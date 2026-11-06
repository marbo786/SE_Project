"""Prepare recording projects through the public HTTP API only."""
import argparse
import json
from pathlib import Path
import time
from urllib.parse import urlsplit
from uuid import uuid4
import httpx

ROOT = Path(__file__).resolve().parents[1]
EMAIL = 'demo-reviewer@example.com'
PASSWORD = 'Library-demo-only-2026!'
NAME = 'Library Lending (ready)'


class Demo:
    def __init__(self, base_url):
        if urlsplit(base_url).hostname not in {'localhost', '127.0.0.1', '::1'}:
            raise ValueError('The recording seeder only operates on localhost.')
        self.client = httpx.Client(base_url=base_url.rstrip('/'), timeout=120, trust_env=False)

    def request(self, method, path, **kwargs):
        headers = kwargs.pop('headers', {})
        csrf = self.client.cookies.get('srs_csrf')
        if csrf:
            headers['X-CSRF-Token'] = csrf
        response = self.client.request(method, path, headers=headers, **kwargs)
        response.raise_for_status()
        return response.json() if response.content else None

    def login(self):
        result = self.client.post('/auth/login', json={'email': EMAIL, 'password': PASSWORD})
        if result.status_code == 401:
            result = self.client.post('/auth/register', json={'name': 'Demo reviewer', 'email': EMAIL, 'password': PASSWORD})
        result.raise_for_status()
        user = self.request('GET', '/auth/me')
        if user['email'] != EMAIL:
            raise RuntimeError('Refusing to operate outside the demo account.')

    def projects(self):
        found = {}
        for archived in ('false', 'true'):
            offset = 0
            while True:
                page = self.request('GET', f'/v1/projects?archived={archived}&limit=100&offset={offset}')
                found.update({p['id']: p for p in page['items']})
                offset += len(page['items'])
                if offset >= page['total'] or not page['items']:
                    break
        return list(found.values())

    def reset(self):
        projects = self.projects()
        for project in projects:
            runs = self.request('GET', f"/v1/projects/{project['id']}/runs?limit=100")['items']
            for run in runs:
                if run['status'] in {'queued', 'running'}:
                    self.request('POST', f"/v1/runs/{run['id']}/cancel")
                    for _ in range(60):
                        if self.request('GET', f"/v1/runs/{run['id']}")['status'] not in {'queued', 'running'}:
                            break
                        time.sleep(1)
            self.request('POST', f"/v1/projects/{project['id']}/lifecycle", json={'action': 'delete', 'confirmation': project['name']})
        print(f'Removed {len(projects)} demo-account projects through the API; no other account was touched.')

    def revision(self, pid, rid):
        return self.request('GET', f'/v1/projects/{pid}/revisions/{rid}')

    def upload(self, pid, revision, kind, path):
        existing = next((a for a in revision['artifacts'] if a['type'] == kind), None)
        data = {'kind': kind}
        if existing:
            data['replace_artifact_id'] = str(existing['id'])
        with path.open('rb') as source:
            result = self.request('POST', f"/v1/projects/{pid}/revisions/{revision['id']}/artifacts",
                headers={'If-Match': str(revision['edit_version']), 'Idempotency-Key': str(uuid4())},
                data=data, files={'file': (path.name, source)})
        return result['revision']

    def analyze(self, pid, revision, corrected=False):
        base = f"/v1/projects/{pid}/revisions/{revision['id']}"
        self.request('POST', base + '/extraction', headers={'If-Match': str(revision['edit_version'])})
        revision = self.revision(pid, revision['id'])
        if corrected:
            from docx import Document
            desired = {p.text.split()[0]: p.text for p in Document(ROOT / 'demo/library-srs-v2.docx').paragraphs if p.text.startswith(('FR-', 'NFR-'))}
            extraction = self.request('GET', base + '/extraction')['canonical']
            for artifact in extraction['artifacts'].values():
                for requirement in artifact.get('requirements', []):
                    text = desired.get(requirement['id'])
                    if text and text != requirement['text']:
                        self.request('PATCH', base + '/requirements/' + requirement['internal_id'],
                            headers={'If-Match': str(revision['edit_version'])}, json={'text': text})
                        revision = self.revision(pid, revision['id'])
        revision = self.request('PATCH', base, headers={'If-Match': str(revision['edit_version'])}, json={'extraction_confirmed': True})
        run = self.request('POST', base + '/runs', headers={'If-Match': str(revision['edit_version']), 'Idempotency-Key': str(uuid4())})
        return self.wait(run['id'])

    def wait(self, run_id):
        for _ in range(180):
            run = self.request('GET', f'/v1/runs/{run_id}')
            if run['status'] not in {'queued', 'running'}:
                if run['status'] != 'completed':
                    report = self.request('GET', f'/v1/runs/{run_id}/report') if run.get('has_report') else run
                    raise RuntimeError(f'Demo analysis did not complete: {json.dumps(report, default=str)[:3000]}')
                return run
            time.sleep(1)
        raise TimeoutError('Analysis exceeded three minutes; inspect .demo-runtime/worker logs.')

    def seed(self, compare):
        project = next((p for p in self.projects() if p['name'] == NAME and not p.get('archived_at')), None)
        if project is None:
            project = self.request('POST', '/v1/projects', headers={'Idempotency-Key': str(uuid4())},
                json={'name': NAME, 'analysis_profile': 'architecture', 'analysis_mode': 'ai'})
        pid = project['id']
        revisions = self.request('GET', f'/v1/projects/{pid}/revisions?limit=100')['items']
        first = next(r for r in revisions if r['number'] == 1)
        results = []
        for version in range(1, 3 if compare else 2):
            runs = self.request('GET', f'/v1/projects/{pid}/runs?limit=100')['items']
            revision = next((r for r in revisions if r['number'] == version), None)
            if revision:
                prior = next((r for r in runs if r['revision_id'] == revision['id']), None)
                if prior:
                    results.append(self.wait(prior['id']))
                    continue
            else:
                revision = self.request('POST', f'/v1/projects/{pid}/drafts', json={'parent_revision_id': first['id']})
            if version == 1:
                revision = self.upload(pid, revision, 'srs', ROOT / 'demo/library-srs-v1.docx')
            files = [('uml_usecase', 'library_usecase.puml'), ('uml_class', 'library_class.puml'), ('uml_sequence', 'library_sequence.puml')] if version == 1 else [('uml_sequence', 'library_sequence_fixed.puml')]
            for kind, filename in files:
                revision = self.upload(pid, revision, kind, ROOT / 'demo/diagrams' / filename)
            results.append(self.analyze(pid, revision, corrected=version == 2))
        manifest = {'project_id': pid, 'runs': [r['id'] for r in results], 'email': EMAIL}
        runtime = ROOT / '.demo-runtime'
        runtime.mkdir(exist_ok=True)
        (runtime / 'seed.json').write_text(json.dumps(manifest, indent=2) + '\n')
        origin = str(self.client.base_url).removesuffix('/api/').removesuffix('/api').rstrip('/')
        print(f'Demo ready: {origin}/projects/{pid}?run={results[0]["id"]}')
        if len(results) == 2:
            print(f'Compare: {origin}/projects/{pid}?run={results[1]["id"]}&tab=compare&compare={results[0]["id"]}')
        print('Use the demo credentials in docs/DEMO.md; do not record the sign-in screen.')
        return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://localhost:5174/api')
    parser.add_argument('--reset', action='store_true', help='Remove only demo-account projects, then seed v1 again.')
    parser.add_argument('--with-compare', action='store_true', help='Also prepare the corrected second revision.')
    args = parser.parse_args()
    demo = Demo(args.base_url)
    try:
        demo.login()
        if args.reset:
            demo.reset()
        demo.seed(args.with_compare)
    finally:
        demo.client.close()


if __name__ == '__main__':
    main()
