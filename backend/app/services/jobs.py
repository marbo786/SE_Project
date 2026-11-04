"""Database-owned job state; broker delivery is intentionally at least once."""
from datetime import timedelta
import uuid
from sqlalchemy import or_
from ..core.config import get_settings
from ..core.time import utcnow
from ..models.history import AnalysisRun, OutboxEvent, RunStage
from ..models.project import Project
from .history import audit, digest, lock_project


class LostLease(Exception):
    pass


class JobCancelled(Exception):
    pass


def enqueue(db, run):
    db.add(OutboxEvent(run_id=run.id))


def claim(db, run_id):
    now, settings = utcnow(), get_settings()
    token = str(uuid.uuid4())
    changed = db.query(AnalysisRun).filter(AnalysisRun.id == run_id, AnalysisRun.status == 'queued',
        AnalysisRun.cancel_requested.is_(False), AnalysisRun.attempt_count < settings.JOB_MAX_ATTEMPTS).update({
            'status': 'running', 'stage': 'extracting', 'attempt_id': token,
            'attempt_count': AnalysisRun.attempt_count + 1, 'started_at': now, 'heartbeat_at': now,
            'lease_expires_at': now + timedelta(seconds=settings.JOB_LEASE_SECONDS)}, synchronize_session=False)
    db.commit()
    return token if changed else None


def fence(db, run_id, token, *, stage=None, counts=None):
    """Take the run row lock before checkpoint/publication; callers commit."""
    now = utcnow()
    values = {'heartbeat_at': now, 'lease_expires_at': now + timedelta(seconds=get_settings().JOB_LEASE_SECONDS)}
    if stage is not None:
        values['stage'] = stage
    if counts is not None:
        values['counts'] = counts
    changed = db.query(AnalysisRun).filter(AnalysisRun.id == run_id, AnalysisRun.status == 'running',
        AnalysisRun.attempt_id == token, AnalysisRun.lease_expires_at > now,
        AnalysisRun.cancel_requested.is_(False)).update(values, synchronize_session=False)
    if not changed:
        db.rollback()
        run = db.get(AnalysisRun, run_id, populate_existing=True)
        if run and run.attempt_id == token and run.cancel_requested:
            raise JobCancelled()
        raise LostLease()


def checkpoint(db, run_id, token, stage, output):
    fence(db, run_id, token, stage=stage)
    row = db.query(RunStage).filter_by(run_id=run_id, stage=stage).first()
    if row is None:
        row = RunStage(run_id=run_id, stage=stage); db.add(row)
    row.attempt_id, row.output_hash, row.output, row.completed_at = token, digest(output), output, utcnow()
    db.commit()


def cached_stage(db, run_id, stage):
    row = db.query(RunStage).filter_by(run_id=run_id, stage=stage).first()
    if row and digest(row.output) == row.output_hash:
        return row.output
    return None


def request_cancel(db, project, run, actor_id):
    lock_project(db, project)
    db.refresh(run)
    if run.status not in {'queued', 'running'}:
        return run
    run.cancel_requested = True
    if run.status == 'queued':
        run.status, run.stage, run.finished_at = 'cancelled', 'cancelled', utcnow()
        project.status = 'cancelled'
    audit(db, project, actor_id, 'analysis_cancel_requested', run_id=run.id)
    return run


def finish_failure(db, run_id, token, *, cancelled=False):
    db.rollback()
    run = db.get(AnalysisRun, run_id)
    if not run:
        return
    project = db.get(Project, run.project_id)
    lock_project(db, project)
    now = utcnow()
    state = 'cancelled' if cancelled else 'failed'
    changed = db.query(AnalysisRun).filter(AnalysisRun.id == run_id, AnalysisRun.attempt_id == token,
        AnalysisRun.status == 'running', AnalysisRun.lease_expires_at > now).update({
            'status': state, 'stage': state, 'finished_at': now, 'lease_expires_at': None,
            'error_code': None if cancelled else 'analysis_failed',
            'error_message': None if cancelled else 'Analysis could not finish. Check the inputs and retry. Earlier reports are preserved.'}, synchronize_session=False)
    if changed:
        project.status = 'cancelled' if cancelled else 'error'
        project.analysis_error = None if cancelled else 'Analysis could not finish. Earlier reports are preserved.'
        audit(db, project, run.requested_by, 'analysis_' + state, run_id=run_id)
    db.commit()


def reconcile(db, *, now=None):
    """Only expired leases are recoverable. Every retry has a bounded attempt count."""
    now = now or utcnow()
    settings = get_settings()
    ids = db.query(AnalysisRun.id).filter(AnalysisRun.status == 'running',
        or_(AnalysisRun.lease_expires_at.is_(None), AnalysisRun.lease_expires_at <= now)).all()
    recovered = []
    for (run_id,) in ids:
        run = db.get(AnalysisRun, run_id)
        project = db.get(Project, run.project_id)
        lock_project(db, project)
        db.refresh(run)
        if run.status != 'running' or run.lease_expires_at and run.lease_expires_at > now:
            continue
        if run.cancel_requested:
            run.status, run.stage, run.finished_at = 'cancelled', 'cancelled', now
            project.status = 'cancelled'
        elif run.attempt_count >= settings.JOB_MAX_ATTEMPTS:
            run.status, run.stage, run.finished_at = 'failed', 'failed', now
            run.error_code = 'worker_attempts_exhausted'
            run.error_message = 'The worker stopped repeatedly. Retry after checking worker health. Earlier reports are preserved.'
            project.status, project.analysis_error = 'error', run.error_message
        else:
            run.status, run.stage = 'queued', 'recovering'
            event = db.query(OutboxEvent).filter_by(run_id=run.id).first()
            if not event:
                event = OutboxEvent(run_id=run.id); db.add(event)
            event.available_at, event.published_at = now, None
            recovered.append(run.id)
        run.lease_expires_at, run.attempt_id = None, None
        audit(db, project, None, 'analysis_lease_expired', run_id=run.id, status=run.status, attempts=run.attempt_count)
        db.commit()
    return recovered


def dispatch(db, publish, *, now=None):
    """Publish only IDs. A crash before recording delivery causes safe redelivery."""
    now = now or utcnow()
    events = db.query(OutboxEvent).join(AnalysisRun, AnalysisRun.id == OutboxEvent.run_id).filter(
        AnalysisRun.status == 'queued', AnalysisRun.cancel_requested.is_(False), OutboxEvent.available_at <= now).order_by(OutboxEvent.id).limit(100).all()
    sent = []
    for event in events:
        event.dispatch_attempts += 1
        try:
            publish(event.run_id)
            event.published_at, event.last_error = now, None
            event.available_at = now + timedelta(seconds=get_settings().JOB_REDISPATCH_SECONDS)
            sent.append(event.run_id)
        except Exception:
            event.last_error = 'broker_unavailable'
            event.available_at = now + timedelta(seconds=min(60, 2 ** min(event.dispatch_attempts, 6)))
        db.commit()
    return sent
