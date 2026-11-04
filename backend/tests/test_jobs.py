from datetime import timedelta
import pytest
from app.core.time import utcnow
from app.models.user import User
from app.models.project import Project
from app.models.history import AnalysisRun, OutboxEvent, RunStage
from app.services import history, jobs


def queued(db):
    user = User(name='Jobs', email='jobs@example.com', hashed_password='unused')
    db.add(user); db.flush()
    project = history.new_project(db, user.id, {'name': 'Durable'})
    run = history.start_run(db, project, history.ensure_revision(db, project), user.id, validate=False)
    db.commit()
    return project, run


def test_run_and_outbox_are_atomic(db_session):
    _, run = queued(db_session)
    assert db_session.query(OutboxEvent).filter_by(run_id=run.id).count() == 1
    assert run.status == 'queued'


def test_duplicate_delivery_has_one_owner_and_stage(db_session):
    _, run = queued(db_session)
    first = jobs.claim(db_session, run.id)
    assert first and jobs.claim(db_session, run.id) is None
    jobs.checkpoint(db_session, run.id, first, 'extract:1', {'requirements': []})
    jobs.checkpoint(db_session, run.id, first, 'extract:1', {'requirements': []})
    assert db_session.query(RunStage).count() == 1
    assert jobs.cached_stage(db_session, run.id, 'extract:1') == {'requirements': []}


def test_expired_worker_is_fenced_after_recovery(db_session):
    _, run = queued(db_session)
    old = jobs.claim(db_session, run.id)
    db_session.refresh(run)
    run.lease_expires_at = utcnow() - timedelta(seconds=1); db_session.commit()
    assert jobs.reconcile(db_session) == [run.id]
    new = jobs.claim(db_session, run.id)
    assert new and new != old
    with pytest.raises(jobs.LostLease):
        jobs.checkpoint(db_session, run.id, old, 'obsolete', {'bad': True})
    jobs.finish_failure(db_session, run.id, old)
    db_session.refresh(run)
    assert run.status == 'running' and run.attempt_id == new
    assert not db_session.query(RunStage).filter_by(stage='obsolete').first()


def test_recovery_is_bounded_and_does_not_touch_live_lease(db_session, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), 'JOB_MAX_ATTEMPTS', 1)
    project, run = queued(db_session)
    jobs.claim(db_session, run.id)
    assert jobs.reconcile(db_session) == []
    db_session.refresh(run)
    run.lease_expires_at = utcnow() - timedelta(seconds=1); db_session.commit()
    jobs.reconcile(db_session)
    db_session.refresh(run); db_session.refresh(project)
    assert run.status == 'failed' and run.error_code == 'worker_attempts_exhausted'
    assert project.status == 'error' and jobs.claim(db_session, run.id) is None


@pytest.mark.parametrize('running', [False, True])
def test_cancel_prevents_claim_and_publication(db_session, running):
    project, run = queued(db_session)
    token = jobs.claim(db_session, run.id) if running else None
    jobs.request_cancel(db_session, project, run, project.user_id); db_session.commit()
    if running:
        with pytest.raises(jobs.JobCancelled):
            jobs.fence(db_session, run.id, token)
        jobs.finish_failure(db_session, run.id, token, cancelled=True)
    assert jobs.claim(db_session, run.id) is None
    db_session.refresh(run)
    assert run.status == 'cancelled' and run.report is None


def test_broker_failure_retains_outbox_for_retry(db_session):
    _, run = queued(db_session)
    def unavailable(_):
        raise ConnectionError('private broker details must not be stored')
    now = utcnow()
    assert jobs.dispatch(db_session, unavailable, now=now) == []
    event = db_session.query(OutboxEvent).one()
    assert event.last_error == 'broker_unavailable' and event.available_at > now
    delivered = []
    assert jobs.dispatch(db_session, delivered.append, now=now + timedelta(seconds=61)) == [run.id]
    assert delivered == [run.id]
    # Broker acknowledgement is not proof of execution: queued work is redelivered.
    assert jobs.dispatch(db_session, delivered.append, now=now + timedelta(seconds=120)) == [run.id]
