"""Kill a real worker process and restart the API while its job is unfinished."""
import os
from pathlib import Path
import subprocess
import sys
import sysconfig
import time
import socket
import httpx
from sqlalchemy import create_engine, text
from .test_history_migration import migrate
from .test_uploads import document_bytes


def test_worker_and_api_restart_preserve_one_report(tmp_path):
    root = Path(__file__).resolve().parents[1]
    database = tmp_path / 'recovery.db'
    engine = create_engine('sqlite:///' + str(database))
    migrate(engine, 'head')
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    marker = tmp_path / 'parser-entered'
    fixture = tmp_path / 'slow_worker.py'
    fixture.write_text('from pathlib import Path\nimport time\nfrom app.pipeline import analyzer\n'
        'original = analyzer.extract_srs\ndef slow(artifact):\n'
        f'    Path({str(marker)!r}).write_text("ready")\n'
        '    time.sleep(30)\n    return original(artifact)\n'
        'analyzer.extract_srs = slow\nfrom app.jobs.worker import main\nmain()\n', encoding='utf-8')
    environment = {**os.environ, 'DATABASE_URL': 'sqlite:///' + str(database), 'UPLOAD_DIR': str(tmp_path / 'uploads'),
        'MAIL_SINK_DIR': str(tmp_path / 'mail'), 'SMTP_HOST': '', 'APP_ENV': 'development', 'COOKIE_SECURE': 'false',
        'PUBLIC_URL': base, 'CORS_ORIGINS': base, 'JOB_LEASE_SECONDS': '2', 'JOB_POLL_SECONDS': '0.1',
        'PYTHONPATH': str(root) + os.pathsep + sysconfig.get_path('purelib')}
    executable = getattr(sys, '_base_executable', sys.executable)
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
    processes = []
    def launch(arguments, log):
        process = subprocess.Popen([executable, *arguments], cwd=root, env=environment, stdout=log, stderr=log, creationflags=flags)
        processes.append(process)
        return process
    def stop(process):
        if process.poll() is not None:
            return
        if sys.platform == 'win32':
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True, creationflags=flags)
        else:
            process.kill()
        process.wait(timeout=10)
    def wait_for(predicate, seconds=20):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            try:
                if result := predicate():
                    return result
            except httpx.TransportError:
                pass
            time.sleep(.1)
        raise AssertionError('Disposable recovery service did not reach the expected state')
    try:
        with (tmp_path / 'services.log').open('w') as log, httpx.Client(base_url=base, timeout=5) as client:
            api = launch(['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(port)], log)
            wait_for(lambda: client.get('/ready').status_code == 200)
            auth = client.post('/auth/register', json={'name': 'Recovery', 'email': 'recovery@example.com', 'password': 'recovery-test-password-123'})
            auth.raise_for_status()
            headers = {'Authorization': 'Bearer ' + auth.json()['access_token']}
            project = client.post('/v1/projects', headers=headers, json={'name': 'Worker recovery'}).json()
            uploaded = client.post(f"/v1/projects/{project['id']}/revisions/{project['current_revision_id']}/artifacts",
                headers={**headers, 'If-Match': '1'}, data={'kind': 'srs'}, files={'file': ('source.docx', document_bytes())})
            uploaded.raise_for_status()
            revision = uploaded.json()['revision']
            response = client.post(f"/v1/projects/{project['id']}/revisions/{revision['id']}/runs",
                headers={**headers, 'If-Match': str(revision['edit_version']), 'Idempotency-Key': 'recover-once'})
            assert response.status_code == 202
            run_id = response.json()['id']
            assert client.get(f'/v1/runs/{run_id}', headers=headers).json()['status'] == 'queued'
            worker = launch([str(fixture)], log)
            wait_for(marker.exists)
            # Request handling remains available while the parser is blocked.
            started = time.monotonic()
            assert client.get(f'/v1/runs/{run_id}', headers=headers).json()['status'] == 'running'
            assert time.monotonic() - started < 3
            stop(worker); stop(api)
            api = launch(['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(port)], log)
            wait_for(lambda: client.get('/ready').status_code == 200)
            launch(['-m', 'app.jobs.worker'], log)
            terminal = wait_for(lambda: (state if (state := client.get(f'/v1/runs/{run_id}', headers=headers).json())['status'] in {'completed', 'failed', 'partial'} else None), 30)
            assert terminal['status'] == 'completed', terminal
            assert terminal['attempt_count'] == 2
            report = client.get(f'/v1/runs/{run_id}/report', headers=headers).json()
            with engine.connect() as db:
                assert db.execute(text('SELECT COUNT(*) FROM analysis_runs')).scalar_one() == 1
                assert db.execute(text('SELECT COUNT(*) FROM run_quality_scores')).scalar_one() == 1
                assert db.execute(text('SELECT COUNT(*) FROM run_findings')).scalar_one() == len(report['findings'])
                assert db.execute(text('SELECT COUNT(*) FROM run_stages')).scalar_one() == 1
    finally:
        for process in reversed(processes):
            stop(process)
        engine.dispose()
