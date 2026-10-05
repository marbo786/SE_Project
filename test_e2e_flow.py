import os
import sys
import io

sys.path.insert(0, os.path.abspath('backend'))
os.chdir(os.path.abspath('backend'))

from fastapi.testclient import TestClient
os.environ["SECRET_KEY"] = "supersecret_real_key_123"
from app.main import app

client = TestClient(app)

print("--- Starting End-to-End System Test ---")

# 1. Health check
res = client.get('/health')
assert res.status_code == 200, f'Health failed: {res.text}'
print('[OK] 1. Health check passed')

# 2. Register
user_email = 'user_demo@test.com'
res = client.post('/auth/register', json={
    'name': 'Test User',
    'email': user_email,
    'password': 'password123'
})
if res.status_code == 400 and 'Email already registered' in res.text:
    print('  User already registered')
else:
    assert res.status_code == 200, f'Register failed: {res.text}'
print('[OK] 2. Registration passed')

# 3. Login
res = client.post('/auth/login', json={
    'email': user_email,
    'password': 'password123'
})
assert res.status_code == 200, f'Login failed: {res.text}'
token = res.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}
print('[OK] 3. Login passed')

res = client.get('/auth/me', headers=headers)
assert res.status_code == 200, f'/auth/me failed: {res.text}'
user_id = res.json()['id']
print('[OK] 4. User profile fetched')

# 4. Create Project
res = client.post('/projects/', headers=headers, json={
    'name': 'Demo Project V1',
    'description': 'A test project'
})
assert res.status_code == 200, f'Create project failed: {res.text}'
project_id = res.json()['id']
print(f'[OK] 5. Created Project {project_id}')

# 5. Upload files
import docx
doc = docx.Document()
bio = io.BytesIO()
doc.save(bio)
docx_content = bio.getvalue()
res = client.post(f'/projects/{project_id}/upload-srs', headers=headers, files={
    'file': ('demo.docx', io.BytesIO(docx_content), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
})
assert res.status_code == 200, f'Upload SRS failed: {res.text}'

puml_content = b"@startuml\nactor User\nusecase \"Login\" as UC1\nUser --> UC1\n@enduml"
res = client.post(f'/projects/{project_id}/upload-uml', headers=headers, data={'uml_type': 'usecase'}, files={
    'file': ('diagram.puml', io.BytesIO(puml_content), 'text/plain')
})
assert res.status_code == 200, f'Upload UML failed: {res.text}'
print('[OK] 6. Uploaded files')

# 6. Analyze
res = client.post(f'/projects/{project_id}/analyze', headers=headers)
assert res.status_code == 200, f'Analyze trigger failed: {res.text}'
print('[OK] 7. Analysis triggered')

# 7. Wait and Check Status
import time
for i in range(10):
    res = client.get(f'/projects/{project_id}', headers=headers)
    status = res.json()['status']
    if status in ['done', 'error', 'partial']:
        break
    time.sleep(1)

print(f'[OK] 8. Final status: {status}')
if status in ['done', 'partial']:
    print("--- End-to-End System Test PASSED ---")
else:
    print("--- End-to-End System Test FAILED ---")
    sys.exit(1)




