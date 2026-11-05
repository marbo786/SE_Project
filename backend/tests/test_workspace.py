"""M6: review annotations cannot mutate machine snapshots or escape run ownership."""
from copy import deepcopy
from .test_history import create, upload, analyze
from app.models.history import AnalysisRun


def test_project_rename_conflicts_and_archive(client, headers):
    project = create(client, headers)
    url = f"/v1/projects/{project['id']}"
    assert client.patch(url, headers=headers, json={'name': '  Revised  ', 'expected_name': project['name']}).json()['name'] == 'Revised'
    assert client.patch(url, headers=headers, json={'name': 'Lost update', 'expected_name': project['name']}).status_code == 409
    assert client.patch(url, headers=headers, json={'name': ' ', 'expected_name': 'Revised'}).status_code == 422
    assert client.post(url + '/lifecycle', headers=headers, json={'action': 'archive'}).status_code == 200
    assert client.patch(url, headers=headers, json={'name': 'Blocked', 'expected_name': 'Revised'}).status_code == 409
    assert client.get('/v1/projects?archived=true', headers=headers).json()['total'] == 1
    assert client.post(url + '/lifecycle', headers=headers, json={'action': 'restore'}).status_code == 200


def test_manual_links_validate_snapshot_endpoints_and_preserve_score(client, headers, db_session):
    project = create(client, headers)
    revision = upload(client, headers, project)
    # Explicit extraction preserves every uploaded endpoint in the snapshot.
    response = client.post(f"/v1/projects/{project['id']}/revisions/{revision['id']}/artifacts", headers={**headers, 'If-Match': str(revision['edit_version'])},
        data={'kind': 'uml_class'}, files={'file': ('architecture.puml', b'@startuml\nclass Warehouse\n@enduml')})
    assert response.status_code == 201, response.text
    revision = response.json()['revision']
    extracted = client.post(f"/v1/projects/{project['id']}/revisions/{revision['id']}/extraction", headers={**headers, 'If-Match': str(revision['edit_version'])})
    assert extracted.status_code == 200
    revision['edit_version'] = extracted.json()['edit_version']
    run = analyze(client, headers, project, revision)
    base = f"/v1/runs/{run['id']}"
    before = deepcopy(db_session.get(AnalysisRun, run['id']).report)
    endpoints = client.get(base + '/trace-endpoints', headers=headers).json()
    source = next(node for node in endpoints if node['type'] == 'requirement')
    target = next(node for node in endpoints if node['type'] == 'class')
    data = {'source_type': source['type'], 'source_id': source['id'], 'target_type': target['type'], 'target_id': target['id'], 'reason': 'Source requirement implemented by warehouse operation.'}
    assert client.post(base + '/manual-traces', headers=headers, json={**data, 'target_id': 'not-in-run'}).status_code == 422
    assert client.post(base + '/manual-traces', headers=headers, json={**data, 'reason': ' '}).status_code == 422
    link = client.post(base + '/manual-traces', headers=headers, json=data)
    assert link.status_code == 201, link.text
    assert client.post(base + '/manual-traces', headers=headers, json=data).json()['id'] == link.json()['id']
    report = client.get(base + '/report', headers=headers).json()
    manual = [row for row in report['trace_links'] if row['origin'] == 'manual']
    assert len(manual) == 1
    decision = next(row for row in report['reviews'] if row['trace_id'] == manual[0]['id'])
    rejected = client.post(base + '/decisions', headers=headers, json={'target_type': 'trace', 'target_id': manual[0]['id'], 'status': 'rejected', 'expected_decision_id': decision['id']})
    assert rejected.status_code == 201
    assert client.post(base + '/decisions', headers=headers, json={'target_type': 'trace', 'target_id': manual[0]['id'], 'status': 'confirmed', 'expected_decision_id': decision['id']}).status_code == 409
    db_session.expire_all()
    assert db_session.get(AnalysisRun, run['id']).report == before
    assert report['score'] == before['score']
    assert 'rejected' in client.get(base + '/traceability.csv', headers=headers).text
    outsider = client.post('/auth/register', json={'name': 'Outsider', 'email': 'outsider@example.com', 'password': 'another-password-123'}).json()
    other = {'Authorization': 'Bearer ' + outsider['access_token']}
    assert client.get(base + '/trace-endpoints', headers=other).status_code in (403, 404)
    assert client.post(base + '/manual-traces', headers=other, json=data).status_code in (403, 404)
    assert client.patch(f"/v1/projects/{project['id']}", headers=other, json={'name': 'Stolen', 'expected_name': project['name']}).status_code in (403, 404)
