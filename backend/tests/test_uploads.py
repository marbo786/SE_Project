import os
import sys
import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.abspath('..'))

import app.main
from app.core.database import Base, get_db
from app.models.artifact import Artifact

engine_test = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Base.metadata.create_all(bind=engine_test)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.main.app.dependency_overrides[get_db] = override_get_db
client = TestClient(app.main.app)

@pytest.fixture(scope="module")
def setup_user_and_project():
    res = client.post('/auth/register', json={'name': 'U', 'email': 'u@u.com', 'password': 'p'})
    res = client.post('/auth/login', json={'email': 'u@u.com', 'password': 'p'})
    token = res.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    
    res = client.post('/projects/', headers=headers, json={'name': 'Proj1'})
    pid = res.json()['id']
    return headers, pid

def test_oversized_file(setup_user_and_project):
    headers, pid = setup_user_and_project
    content = b"0" * (11 * 1024 * 1024)
    res = client.post(f'/projects/{pid}/upload-srs', headers=headers, files={
        'file': ('demo.docx', io.BytesIO(content), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    })
    assert res.status_code == 413

def test_wrong_extension(setup_user_and_project):
    headers, pid = setup_user_and_project
    content = b"PK\x03\x04Mock"
    res = client.post(f'/projects/{pid}/upload-uml', headers=headers, data={'uml_type': 'usecase'}, files={
        'file': ('diagram.docx', io.BytesIO(content), 'text/plain')
    })
    assert res.status_code == 400
    assert "Invalid UML extension" in res.text

def test_spoofed_extension(setup_user_and_project):
    headers, pid = setup_user_and_project
    content = b"Not a zip or pdf"
    res = client.post(f'/projects/{pid}/upload-srs', headers=headers, files={
        'file': ('demo.docx', io.BytesIO(content), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    })
    assert res.status_code == 400
    assert "Invalid file type" in res.text

def test_duplicate_upload_replaces(setup_user_and_project):
    headers, pid = setup_user_and_project
    
    c1 = b"PK\x03\x04Doc 1"
    res1 = client.post(f'/projects/{pid}/upload-srs', headers=headers, files={
        'file': ('demo1.docx', io.BytesIO(c1), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    })
    assert res1.status_code == 200
    
    db1 = TestingSessionLocal()
    artifacts = db1.query(Artifact).filter(Artifact.project_id == pid, Artifact.artifact_type == "srs").all()
    assert len(artifacts) == 1
    db1.close()
    
    c2 = b"%PDF-1.4 Doc 2"
    res2 = client.post(f'/projects/{pid}/upload-srs', headers=headers, files={
        'file': ('demo2.pdf', io.BytesIO(c2), 'application/pdf')
    })
    assert res2.status_code == 200
    
    db2 = TestingSessionLocal()
    artifacts = db2.query(Artifact).filter(Artifact.project_id == pid, Artifact.artifact_type == "srs").all()
    assert len(artifacts) == 1
    assert artifacts[0].file_format == "pdf"
    assert artifacts[0].original_filename == "demo2.pdf"
    db2.close()

