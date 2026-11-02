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
        return LLMResponse('{"results": [{"requirement_id": "FR-1", "testable": true}], "conflicts": []}', 10, 10, 10, self.provider_name, self.default_model)

class FailProvider(SuccessProvider):
    async def complete(self, *args, **kwargs):
        raise RuntimeError("Simulated provider outage")

@pytest.mark.parametrize("provider,expected", [(SuccessProvider, "done"), (FailProvider, "partial")])
async def test_analysis_terminal_state(db_session, tmp_path, monkeypatch, provider, expected):
    db = db_session
    user = User(name="Test", email="test@example.com", hashed_password="unused")
    db.add(user)
    db.flush()
    project = Project(user_id=user.id, name="Test", version=1, status="pending")
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
