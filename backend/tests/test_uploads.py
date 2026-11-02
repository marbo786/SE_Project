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


def test_failed_replacement_preserves_original(client, headers, project_id, db_session):
    from pathlib import Path
    client.post(f"/projects/{project_id}/upload-srs", headers=headers, files={"file": ("original.docx", document_bytes())})
    artifact = db_session.query(Artifact).one()
    original = Path(artifact.file_path).read_bytes()
    assert client.post(f"/projects/{project_id}/upload-srs", headers=headers, files={"file": ("broken.docx", b"PKgarbage")}).status_code == 400
    db_session.refresh(artifact)
    assert artifact.original_filename == "original.docx"
    assert Path(artifact.file_path).read_bytes() == original


@pytest.mark.parametrize("content", [b"!include https://example.com/test.puml", b"class X\n!include /etc/passwd", b"", b"\xff\xfe", b"plain prose"])
def test_unsafe_or_invalid_uml_rejected(client, headers, project_id, content):
    assert client.post(f"/projects/{project_id}/upload-uml", headers=headers, data={"uml_type": "class"}, files={"file": ("model.puml", content)}).status_code == 400


def test_expanded_docx_budget(client, headers, project_id, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), "MAX_EXPANDED_SIZE", 100)
    assert client.post(f"/projects/{project_id}/upload-srs", headers=headers, files={"file": ("large.docx", document_bytes())}).status_code == 400


def test_analysis_requires_srs_and_locks_uploads(client, headers, project_id, db_session):
    from app.models.project import Project
    assert client.post(f"/projects/{project_id}/analyze", headers=headers).status_code == 409
    db_session.get(Project, project_id).status = "analyzing"
    db_session.commit()
    assert client.post(f"/projects/{project_id}/upload-srs", headers=headers, files={"file": ("locked.docx", document_bytes())}).status_code == 409


async def test_chunked_body_limit():
    from app.core.request_limits import RequestSizeLimit
    sent = []
    async def downstream(scope, receive, send):
        await receive()
        await receive()
    async def receive():
        return {"type": "http.request", "body": b"123456", "more_body": True}
    async def send(message):
        sent.append(message)
    await RequestSizeLimit(downstream, maximum=10)({"type": "http", "headers": []}, receive, send)
    assert sent[0]["status"] == 413


def test_parser_timeout_becomes_actionable_error(monkeypatch):
    import subprocess
    from app.core import uploads
    from fastapi import HTTPException
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("validator", 20)
    monkeypatch.setattr(uploads.subprocess, "run", timeout)
    with pytest.raises(HTTPException, match="validation took too long") as error:
        uploads.validate_isolated(b"untrusted", "file.pdf")
    assert error.value.status_code == 400
