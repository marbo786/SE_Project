"""Public contract regressions for immutable history and draft concurrency."""
from copy import deepcopy
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.models.project import Project
from app.models.artifact import Artifact
from app.models.history import AnalysisRun, ProjectRevision, RunFinding, RunTraceLink, RunQualityScore, ReviewDecision, Requirement
from app.services import history
from .test_uploads import document_bytes


def create(client, headers, name='History', key='create-history'):
    response = client.post('/v1/projects', headers={**headers, 'Idempotency-Key': key}, json={'name': name})
    assert response.status_code == 201, response.text
    return response.json()


def upload(client, headers, project, revision=None, text='FR-1 The system shall respond fast.'):
    rid = revision['id'] if revision else project['current_revision_id']
    version = revision['edit_version'] if revision else 1
    response = client.post(f"/v1/projects/{project['id']}/revisions/{rid}/artifacts",
        headers={**headers, 'If-Match': str(version)}, data={'kind': 'srs'}, files={'file': ('source.docx', document_bytes(text))})
    assert response.status_code == 201, response.text
    return response.json()['revision']


def analyze(client, headers, project, revision, key='run-history'):
    response = client.post(f"/v1/projects/{project['id']}/revisions/{revision['id']}/runs",
        headers={**headers, 'If-Match': str(revision['edit_version']), 'Idempotency-Key': key})
    assert response.status_code == 202, response.text
    return response.json()


def test_project_identity_and_request_replay(client, headers, db_session):
    first = create(client, headers)
    assert create(client, headers) == first
    second = create(client, headers, key='another-project')
    assert first['id'] != second['id'] and first['version'] == second['version'] == 1
    assert client.post('/v1/projects', headers={**headers, 'Idempotency-Key': 'create-history'}, json={'name': 'Different'}).status_code == 409
    assert db_session.query(Project).count() == 2
    page = client.get('/v1/projects?limit=1&offset=1&search=Hist', headers=headers).json()
    assert page['total'] == 2 and len(page['items']) == 1


def test_upload_retry_and_draft_optimistic_lock(client, headers, db_session):
    project = create(client, headers)
    url = f"/v1/projects/{project['id']}/revisions/{project['current_revision_id']}/artifacts"
    auth = {**headers, 'If-Match': '1', 'Idempotency-Key': 'upload-once'}
    content = document_bytes()
    first = client.post(url, headers=auth, data={'kind': 'srs'}, files={'file': ('source.docx', content)})
    assert first.status_code == 201
    retry = client.post(url, headers=auth, data={'kind': 'srs'}, files={'file': ('source.docx', content)})
    assert retry.json() == first.json()
    assert db_session.query(Artifact).count() == 1
    base = url.removesuffix('/artifacts')
    assert client.patch(base, headers=headers, json={'analysis_profile': 'architecture'}).status_code == 428
    assert client.patch(base, headers={**headers, 'If-Match': '1'}, json={'analysis_profile': 'architecture'}).status_code == 409
    assert client.patch(base, headers={**headers, 'If-Match': '2'}, json={'analysis_profile': 'architecture'}).status_code == 200


def test_sealed_history_corrections_and_partial_preservation(client, headers, db_session):
    project = create(client, headers)
    revision = upload(client, headers, project)
    first = analyze(client, headers, project, revision)
    # A retried start returns its originally accepted response, even after completion.
    assert analyze(client, headers, project, revision) == first
    report_url = f"/v1/runs/{first['id']}/report"
    before = client.get(report_url, headers=headers).json()
    assert before['run']['status'] == 'completed'
    base = f"/v1/projects/{project['id']}/revisions/{revision['id']}"
    assert client.patch(base, headers={**headers, 'If-Match': str(revision['edit_version'])}, json={'analysis_mode': 'ai'}).status_code == 409
    draft = client.post(f"/v1/projects/{project['id']}/drafts", headers={**headers, 'Idempotency-Key': 'fork'}, json={}).json()
    assert draft['number'] == 2 and draft['parent_id'] == revision['id']
    assert client.post(f"/v1/projects/{project['id']}/drafts", headers=headers, json={}).json()['id'] == draft['id']
    canonical = client.get(f"/v1/projects/{project['id']}/revisions/{draft['id']}/extraction", headers=headers).json()['canonical']
    req = next(iter(canonical['artifacts'].values()))['requirements'][0]
    changed = client.patch(f"/v1/projects/{project['id']}/revisions/{draft['id']}/requirements/{req['internal_id']}",
        headers={**headers, 'If-Match': str(draft['edit_version'])}, json={'text': 'FR-1 The system shall respond within 2 seconds.', 'class': 'non_functional', 'subtype': 'performance'})
    assert changed.status_code == 200, changed.text
    assert changed.json()['requirement']['original_text'] == req['text']
    draft['edit_version'] = changed.json()['edit_version']
    second = analyze(client, headers, project, draft, key='run-two')
    after = client.get(f"/v1/runs/{second['id']}/report", headers=headers).json()
    assert next(iter(after['extractions'].values()))['requirements'][0]['text'].endswith('within 2 seconds.')
    comparison = client.get(f"/v1/runs/{second['id']}/compare/{first['id']}", headers=headers).json()
    assert len(comparison['requirements']['changed']) == 1
    assert comparison['resolved_findings']
    assert client.get(report_url, headers=headers).json() == before
    assert db_session.query(AnalysisRun).count() == 2
    assert db_session.query(Requirement).count() == 2


def test_multi_diagram_upload_and_shared_file_retention(client, headers, db_session):
    project = create(client, headers)
    revision = upload(client, headers, project)
    for number in (1, 2):
        response = client.post(f"/v1/projects/{project['id']}/revisions/{revision['id']}/artifacts",
            headers={**headers, 'If-Match': str(revision['edit_version'])}, data={'kind': 'uml_class'},
            files={'file': (f'model-{number}.puml', f'class C{number}'.encode())})
        assert response.status_code == 201, response.text
        revision = response.json()['revision']
    assert len(revision['artifacts']) == 3
    analyze(client, headers, project, revision)
    original = db_session.query(Artifact).filter_by(revision_id=revision['id'], artifact_type='srs').one()
    original_path = Path(original.file_path)
    draft = client.post(f"/v1/projects/{project['id']}/drafts", headers=headers, json={}).json()
    cloned = next(a for a in draft['artifacts'] if a['type'] == 'srs')
    response = client.post(f"/v1/projects/{project['id']}/revisions/{draft['id']}/artifacts",
        headers={**headers, 'If-Match': str(draft['edit_version'])}, data={'kind': 'srs', 'replace_artifact_id': cloned['id']},
        files={'file': ('changed.docx', document_bytes('FR-1 The system shall store a file.'))})
    assert response.status_code == 201, response.text
    assert original_path.is_file()
    assert client.get(f"/v1/projects/{project['id']}/artifacts/{original.id}/source", headers=headers).content == original_path.read_bytes()


def test_review_is_append_only_and_cannot_rewrite_machine_report(client, headers, db_session):
    project = create(client, headers)
    revision = upload(client, headers, project)
    run = analyze(client, headers, project, revision)
    snapshot = deepcopy(db_session.get(AnalysisRun, run['id']).report)
    target = snapshot['findings'][0]['id']
    url = f"/v1/runs/{run['id']}/decisions"
    first = client.post(url, headers=headers, json={'target_type': 'finding', 'target_id': target, 'status': 'dismissed', 'reason': 'Reviewed context'})
    assert first.status_code == 201, first.text
    assert client.post(url, headers=headers, json={'target_type': 'finding', 'target_id': target, 'status': 'accepted'}).status_code == 409
    second = client.post(url, headers=headers, json={'target_type': 'finding', 'target_id': target, 'status': 'accepted', 'expected_decision_id': first.json()['id']})
    assert second.status_code == 201
    db_session.expire_all()
    assert db_session.get(AnalysisRun, run['id']).report == snapshot
    assert db_session.query(ReviewDecision).count() == 2
    retry = analyze(client, headers, project, revision, key='repeat-identical')
    carried = client.get(f"/v1/runs/{retry['id']}/report", headers=headers).json()['reviews']
    assert len(carried) == 1 and carried[0]['origin'] == 'carried' and carried[0]['carried_from_id'] == second.json()['id']


def test_new_resources_are_private_and_lifecycle_is_reversible(client, headers, db_session):
    project = create(client, headers)
    revision = upload(client, headers, project)
    run = analyze(client, headers, project, revision)
    stranger = client.post('/auth/register', json={'name': 'Other', 'email': 'other@example.com', 'password': 'another-password-123'}).json()
    other = {'Authorization': 'Bearer ' + stranger['access_token']}
    for url in [f"/v1/projects/{project['id']}", f"/v1/projects/{project['id']}/revisions", f"/v1/runs/{run['id']}", f"/v1/runs/{run['id']}/report",
        f"/v1/runs/{run['id']}/findings", f"/v1/projects/{project['id']}/artifacts/{revision['artifacts'][0]['id']}/source"]:
        assert client.get(url, headers=other).status_code == 404, url
    url = f"/v1/projects/{project['id']}/lifecycle"
    assert client.post(url, headers=other, json={'action': 'delete', 'confirmation': 'History'}).status_code == 404
    assert client.post(url, headers=headers, json={'action': 'archive'}).status_code == 200
    assert client.get('/v1/projects', headers=headers).json()['total'] == 0
    assert client.get('/v1/projects?archived=true', headers=headers).json()['total'] == 1
    assert client.post(url, headers=headers, json={'action': 'delete', 'confirmation': 'wrong'}).status_code == 422
    assert client.post(url, headers=headers, json={'action': 'delete', 'confirmation': 'History'}).status_code == 200
    assert client.get(f"/v1/runs/{run['id']}/report", headers=headers).status_code == 404
    assert client.post(url, headers=headers, json={'action': 'restore'}).status_code == 200
    assert client.get(f"/v1/runs/{run['id']}/report", headers=headers).status_code == 200


def test_comparison_preserves_duplicate_and_global_findings(db_session):
    from app.models.user import User
    user = User(name='Diff', email='diff@example.com', hashed_password='unused')
    db_session.add(user); db_session.flush()
    project = history.new_project(db_session, user.id, {'name': 'Diff'})
    revision = history.ensure_revision(db_session, project)
    runs = [AnalysisRun(project_id=project.id, revision_id=revision.id, requested_by=user.id,
        status='completed', versions=history.VERSIONS, input_snapshot={'profile': 'srs_only'}) for _ in range(2)]
    db_session.add_all(runs); db_session.flush()
    for index, texts in enumerate([['Missing scope', 'Missing references', 'Conflict A', 'Conflict A'], ['Missing scope', 'Conflict A']]):
        for text in texts:
            data = {'rule_id': 'same', 'severity': 'major', 'explanation': text}
            db_session.add(RunFinding(run_id=runs[index].id, fingerprint=history.finding_fingerprint(data, {}), rule_id='same', severity='major', data=data))
    db_session.commit()
    result = history.compare_runs(db_session, *runs)
    assert len(result['persistent_findings']) == 2
    assert sorted(f['explanation'] for f in result['resolved_findings']) == ['Conflict A', 'Missing references']


def test_retention_dry_run_and_safe_file_cleanup(client, headers, db_session, tmp_path):
    from datetime import timedelta
    from app.core.time import utcnow
    from app.services.retention import purge_expired
    project = create(client, headers)
    revision = upload(client, headers, project)
    analyze(client, headers, project, revision)
    source = Path(db_session.query(Artifact).one().file_path)
    unrelated = tmp_path / 'keep.txt'; unrelated.write_text('unrelated', encoding='utf-8')
    db_session.expire_all()
    db_session.get(Project, project['id']).deleted_at = utcnow() - timedelta(days=31)
    db_session.commit()
    preview = purge_expired(db_session)
    assert preview['eligible_project_ids'] == [project['id']] and source.exists()
    result = purge_expired(db_session, apply=True)
    assert result['purged_project_ids'] == [project['id']]
    assert not source.exists() and unrelated.exists()
    assert not db_session.query(Project).count() and not db_session.query(AnalysisRun).count()


def test_concurrent_draft_creation_has_one_monotonic_number(tmp_path):
    from app.core.database import Base
    from app.models.user import User
    engine = create_engine('sqlite:///' + str(tmp_path / 'concurrent.db'), connect_args={'timeout': 15})
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    try:
        with factory.begin() as db:
            user = User(name='Concurrent', email='concurrent@example.com', hashed_password='unused'); db.add(user); db.flush()
            project = history.new_project(db, user.id, {'name': 'Parallel'})
            revision = history.ensure_revision(db, project)
            revision.state = 'sealed'
            pid, uid, rid = project.id, user.id, revision.id
        def fork(_):
            with factory.begin() as db:
                result = history.fork_draft(db, db.get(Project, pid), uid, rid)
                return result.id, result.number
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(fork, range(4)))
        assert len(set(results)) == 1 and results[0][1] == 2
        with factory() as db:
            assert db.query(ProjectRevision).count() == 2
            assert db.get(Project, pid).next_revision_number == 3
    finally:
        engine.dispose()
