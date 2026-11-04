import pytest
from app.models.project import Project
from app.models.user import User
from app.models.artifact import Artifact
from app.pipeline import analyzer
from app.llm import engine
from app.llm.base import BaseLLMProvider, LLMResponse

class SuccessProvider(BaseLLMProvider):
    provider_name = "mock_success"
    default_model = "mock"
    async def complete(self, *args, **kwargs):
        content = '{"results": [{"requirement_id": "R0", "testable": true}]}' if "testab" in args[0] else '{"conflicts": []}'
        return LLMResponse(content, 10, 10, 10, self.provider_name, self.default_model)

class FailProvider(SuccessProvider):
    async def complete(self, *args, **kwargs):
        raise RuntimeError("Simulated provider outage")

@pytest.mark.parametrize("provider,expected", [(SuccessProvider, "done"), (FailProvider, "partial")])
async def test_analysis_terminal_state(db_session, tmp_path, monkeypatch, provider, expected):
    db = db_session
    user = User(name="Test", email="test@example.com", hashed_password="unused")
    db.add(user)
    db.flush()
    project = Project(user_id=user.id, name="Test", version=1, status="pending", analysis_mode="ai")
    db.add(project)
    db.flush()
    path = tmp_path / "sample.docx"
    from docx import Document
    doc = Document()
    doc.add_paragraph("FR-1 The system shall store a record.")
    doc.save(path)
    db.add(Artifact(project_id=project.id, artifact_type="srs", file_format="docx", file_path=str(path), original_filename="sample.docx"))
    db.commit()
    monkeypatch.setattr(engine, "get_provider", provider)
    await analyzer.run_analysis_pipeline(project.id)
    db.refresh(project)
    assert project.status == expected
    from app.models.score import QualityScore
    score = db.query(QualityScore).filter_by(project_id=project.id).one()
    assert (score.overall_score is None) == (expected == "partial")


def make_project(db, tmp_path, *, architecture=False, text="FR-1 The system shall login."):
    from docx import Document
    user = User(name="Test", email="analysis@example.com", hashed_password="unused")
    db.add(user); db.flush()
    project = Project(user_id=user.id, name="Analysis", analysis_profile="architecture" if architecture else "srs_only")
    db.add(project); db.flush()
    doc = Document(); doc.add_paragraph(text)
    path = tmp_path / "input.docx"; doc.save(path)
    db.add(Artifact(project_id=project.id, artifact_type="srs", file_format="docx", file_path=str(path), original_filename="input.docx"))
    if architecture:
        for kind, content in {"usecase": 'actor User\nusecase "Login FR-1" as Login\nUser --> Login',
            "class": "class Auth {\n+login()\n}", "sequence": "participant Auth\nUser -> Auth: login()"}.items():
            path = tmp_path / f"{kind}.puml"; path.write_text(content, encoding="utf-8")
            db.add(Artifact(project_id=project.id, artifact_type=f"uml_{kind}", file_format="puml", file_path=str(path), original_filename=path.name))
    db.commit()
    return project


async def test_review_decisions_do_not_change_raw_score_on_reanalysis(db_session, tmp_path):
    from app.models.score import QualityScore
    from app.models.traceability import TraceLink
    project = make_project(db_session, tmp_path, architecture=True)
    await analyzer.run_analysis_pipeline(project.id)
    db_session.refresh(project)
    assert project.status == "done"
    before = db_session.query(QualityScore).one().overall_score
    links = db_session.query(TraceLink).all()
    assert links and before is not None
    for link in links:
        link.status = "confirmed"
    db_session.commit()
    await analyzer.run_analysis_pipeline(project.id)
    db_session.expire_all()
    assert db_session.query(QualityScore).one().overall_score == before
    assert db_session.query(TraceLink).count() == len(links)
    assert all(link.status == "confirmed" for link in db_session.query(TraceLink))


async def test_failed_reanalysis_preserves_report(db_session, tmp_path, monkeypatch):
    from app.models.finding import Finding
    from app.models.score import QualityScore
    project = make_project(db_session, tmp_path)
    await analyzer.run_analysis_pipeline(project.id)
    identifiers = {finding.id for finding in db_session.query(Finding)}
    before = db_session.query(QualityScore).one().computed_at
    def fail(*args):
        raise ValueError("Simulated corrupt document")
    monkeypatch.setattr(analyzer, "extract_srs", fail)
    await analyzer.run_analysis_pipeline(project.id)
    db_session.expire_all()
    assert db_session.get(Project, project.id).status == "error"
    assert {finding.id for finding in db_session.query(Finding)} == identifiers
    assert db_session.query(QualityScore).one().computed_at == before


async def test_evidence_persisted_and_no_requirements_not_graded(db_session, tmp_path):
    from app.models.finding import Finding
    from app.models.score import QualityScore
    project = make_project(db_session, tmp_path, text="The system shall respond fast.")
    await analyzer.run_analysis_pipeline(project.id)
    missing_id = db_session.query(Finding).filter_by(rule_id="FR-409").one()
    assert missing_id.source_ref == "Paragraph 1"
    assert missing_id.element_id
    assert missing_id.source_spans[0]["artifact_id"]
    from app.services.history import fork_draft
    from app.core.uploads import store_artifact
    from .test_uploads import document_bytes
    db_session.expire_all()
    previous_run = project.published_run_id
    previous_score = db_session.query(QualityScore).one().overall_score
    revision = fork_draft(db_session, project, project.user_id)
    db_session.commit()
    store_artifact(db_session, project, 'srs', document_bytes('A narrative overview without any normative statement.'),
        'docx', 'revised.docx', revision=revision)
    await analyzer.run_analysis_pipeline(project.id)
    db_session.expire_all()
    assert db_session.get(Project, project.id).status == "partial"
    from app.models.history import RunQualityScore
    assert db_session.get(RunQualityScore, project.latest_run_id).overall_score is None
    assert project.published_run_id == previous_run
    assert db_session.query(QualityScore).one().overall_score == previous_score
