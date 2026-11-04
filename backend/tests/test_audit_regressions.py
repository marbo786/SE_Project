"""Strict expected failures are removed as their corresponding fixes land."""
import pytest
from docx import Document
from app.models.project import Project
from app.models.user import User
from app.models.finding import Finding
from app.models.traceability import TraceLink
from app.pipeline.srs.parser import parse_srs
from app.pipeline.uml.parser import parse_plantuml
from app.pipeline.checks.uml_checks import run_all_uml_checks
from app.pipeline.checks.traceability_checks import build_trace_links
from app.pipeline.checks.srs_checks import run_all_srs_checks
from app.pipeline.scoring import compute_scores

def test_foreign_resources_are_private(client, headers, db_session):
    owner = User(name="Owner", email="owner@example.com", hashed_password="unused")
    db_session.add(owner)
    db_session.flush()
    project = Project(user_id=owner.id, name="Private")
    db_session.add(project)
    db_session.flush()
    db_session.add(Finding(project_id=project.id, rule_id="TEST", severity="major", explanation="Private text"))
    link = TraceLink(project_id=project.id, source_type="requirement", source_id="FR-1", target_type="usecase", target_id="Login")
    db_session.add(link)
    db_session.commit()
    for path in [f"/projects/{project.id}", f"/projects/{project.id}/extraction", f"/findings/project/{project.id}", f"/traceability/project/{project.id}", f"/traceability/project/{project.id}/export"]:
        assert client.get(path, headers=headers).status_code == 404, path
    assert client.patch(f"/traceability/{link.id}", headers=headers, json={"status": "rejected"}).status_code == 404
    assert client.get(f"/projects/{project.id}/compare?with_version=1", headers=headers).status_code == 404
    for operation in ["analyze", "reanalyze"]:
        assert client.post(f"/projects/{project.id}/{operation}", headers=headers).status_code == 404
    assert client.post(f"/projects/{project.id}/upload-srs", headers=headers, files={"file": ("fake.docx", b"PKgarbage")}).status_code == 404

def test_empty_credentials_rejected(client):
    assert client.post("/auth/register", json={"name": "", "email": "empty@example.com", "password": ""}).status_code == 422

def test_invalid_docx_rejected(client, headers):
    pid = client.post("/projects/", headers=headers, json={"name": "Test"}).json()["id"]
    assert client.post(f"/projects/{pid}/upload-srs", headers=headers, files={"file": ("fake.docx", b"PKgarbage")}).status_code == 400

def test_table_requirement_is_one_record(tmp_path):
    doc = Document()
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "FR-1"
    table.cell(0, 1).text = "The system shall save a record."
    path = tmp_path / "table.docx"
    doc.save(path)
    requirements = parse_srs(str(path), "docx")["requirements"]
    assert len(requirements) == 1
    assert requirements[0]["id"] == "FR-1"
    assert "save a record" in requirements[0]["text"]

def test_missing_id_trace_does_not_crash():
    build_trace_links([{"id": None, "text": "The system shall login."}], {"use_cases": [{"name": "Login"}]})

def test_usecase_alias_is_connected():
    model = parse_plantuml('@startuml\nactor User\nusecase "Login" as UC1\nUser --> UC1\n@enduml', "usecase")
    assert not run_all_uml_checks(model)

def test_public_operation_is_defined():
    classes = parse_plantuml("class Auth {\n+login()\n}", "class")
    sequence = parse_plantuml("participant Auth\nUser -> Auth: login()", "sequence")
    assert not run_all_uml_checks(sequence, classes)

def test_empty_input_has_no_score():
    findings = run_all_srs_checks({"requirements": [], "sections": []})
    assert compute_scores(findings, [], 0, 0, 0)["overall_score"] is None

async def test_meaningless_rewrite_cannot_pass(monkeypatch):
    from app.pipeline import repair
    async def fake_call(*args, **kwargs):
        return '{"rewrite_suggestion":"Hello."}'
    monkeypatch.setattr(repair, "call_llm", fake_call)
    findings = [{"artifact_type": "srs", "requirement_id": "NFR-1", "quoted_text": "The system shall respond fast.", "explanation": "Missing response-time metric"}]
    await repair.agentic_repair_loop(findings)
    assert findings[0]["rewrite_passed"] is False
