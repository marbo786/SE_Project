"""CI-only broker/API restart drill against this workflow's disposable Compose stack."""
import os
import subprocess
import time
import uuid
import io
import httpx
from docx import Document


def compose(*arguments):
    subprocess.run(['docker', 'compose', *arguments], check=True, capture_output=True)


def main():
    if os.environ.get('CI') != 'true':
        raise RuntimeError('This drill only controls the disposable CI Compose stack')
    with httpx.Client(base_url='http://localhost:5173/api', timeout=20) as client:
        response = client.post('/auth/register', json={'name': 'Recovery smoke', 'email': f'recovery-{uuid.uuid4().hex}@example.com', 'password': 'recovery-smoke-password-123'})
        response.raise_for_status()
        headers = {'Authorization': 'Bearer ' + response.json()['access_token']}
        project = client.post('/v1/projects', headers=headers, json={'name': 'Broker restart drill'}).json()
        document = Document(); document.add_paragraph('FR-1 The system shall store a record.')
        content = io.BytesIO(); document.save(content)
        uploaded = client.post(f"/v1/projects/{project['id']}/revisions/{project['current_revision_id']}/artifacts",
            headers={**headers, 'If-Match': '1'}, data={'kind': 'srs'}, files={'file': ('source.docx', content.getvalue())})
        uploaded.raise_for_status()
        revision = uploaded.json()['revision']
        compose('stop', 'worker')
        try:
            url = f"/v1/projects/{project['id']}/revisions/{revision['id']}/runs"
            request_headers = {**headers, 'If-Match': str(revision['edit_version']), 'Idempotency-Key': 'restart-drill'}
            accepted = client.post(url, headers=request_headers); accepted.raise_for_status()
            run_id = accepted.json()['id']; uuid.UUID(run_id)
            assert accepted.status_code == 202
            compose('restart', 'backend', 'redis', 'dispatcher')
            for _ in range(60):
                try:
                    if client.get('/ready').status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(1)
            replay = client.post(url, headers=request_headers); replay.raise_for_status()
            assert replay.json()['id'] == run_id
        finally:
            compose('start', 'worker')
        for _ in range(90):
            state = client.get(f'/v1/runs/{run_id}', headers=headers).json()
            if state['status'] in {'completed', 'partial', 'failed'}:
                break
            time.sleep(1)
        assert state['status'] == 'completed', state
        original = client.get(f'/v1/runs/{run_id}/report', headers=headers).json()
        compose('exec', '-T', 'worker', 'python', '-c', f"from app.jobs.celery_app import analyze; analyze.apply_async(args=['{run_id}'])")
        time.sleep(3)
        after = client.get(f'/v1/runs/{run_id}/report', headers=headers).json()
        assert after == original
        assert client.get(f"/v1/projects/{project['id']}/runs", headers=headers).json()['total'] == 1
        print('Compose recovery passed: API/broker restart, idempotent request, outbox delivery and duplicate worker message')


if __name__ == '__main__':
    main()
