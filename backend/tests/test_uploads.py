import io
import pytest
from docx import Document
from app.models.artifact import Artifact

def document_bytes(text="FR-1 The system shall save a record."):
    doc = Document()
    doc.add_paragraph(text)
    output = io.BytesIO()
    doc.save(output)
    return output.getvalue()

@pytest.fixture
def project_id(client, headers):
    return client.post("/projects/", headers=headers, json={"name": "Upload test"}).json()["id"]

def test_oversized_file(client, headers, project_id):
    res = client.post(f"/projects/{project_id}/upload-srs", headers=headers, files={"file": ("large.docx", b"0" * (11 * 1024 * 1024))})
    assert res.status_code == 413

def test_wrong_extension(client, headers, project_id):
    res = client.post(f"/projects/{project_id}/upload-uml", headers=headers, data={"uml_type": "usecase"}, files={"file": ("diagram.docx", b"PKinvalid")})
    assert res.status_code == 400

def test_spoofed_extension(client, headers, project_id):
    res = client.post(f"/projects/{project_id}/upload-srs", headers=headers, files={"file": ("fake.docx", b"Not a document")})
    assert res.status_code == 400

def test_duplicate_upload_replaces(client, headers, project_id, db_session):
    for filename in ["first.docx", "second.docx"]:
        res = client.post(f"/projects/{project_id}/upload-srs", headers=headers, files={"file": (filename, document_bytes())})
        assert res.status_code == 200, res.text
    artifacts = db_session.query(Artifact).filter_by(project_id=project_id, artifact_type="srs").all()
    assert len(artifacts) == 1
    assert artifacts[0].original_filename == "second.docx"
