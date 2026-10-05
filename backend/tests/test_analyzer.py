import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import asyncio

sys.path.insert(0, os.path.abspath('..'))

import app.main  # Import EVERYTHING so Base has all models

from app.core.database import Base
from app.models.project import Project
from app.models.artifact import Artifact
from app.pipeline.analyzer import run_analysis_pipeline
from app.llm.base import BaseLLMProvider, LLMResponse
from app.llm import engine

# Setup test DB
from sqlalchemy.pool import StaticPool
engine_test = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Base.metadata.create_all(bind=engine_test)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

import app.core.database
app.core.database.SessionLocal = TestingSessionLocal
import app.pipeline.analyzer
app.pipeline.analyzer.SessionLocal = TestingSessionLocal

class MockSuccessProvider(BaseLLMProvider):
    @property
    def provider_name(self) -> str: return "mock_success"
    @property
    def default_model(self) -> str: return "mock"
    async def complete(self, sys_prompt, usr_prompt, model=None):
        content = '{"results": [{"requirement_id": "FR-1", "testable": true}], "conflicts": [], "rewrites": []}'
        return LLMResponse(content=content, prompt_tokens=10, completion_tokens=10, latency_ms=10, provider="mock", model="mock")

class MockFailProvider(BaseLLMProvider):
    @property
    def provider_name(self) -> str: return "mock_fail"
    @property
    def default_model(self) -> str: return "mock"
    async def complete(self, sys_prompt, usr_prompt, model=None):
        raise RuntimeError("Network Error")

@pytest.fixture(autouse=True)
def clear_cache():
    pass

def create_mock_project(db):
    project = Project(user_id=1, name="Test", version=1, status="pending")
    db.add(project)
    db.commit()
    db.refresh(project)
    
    import uuid
    path = f"test_{uuid.uuid4()}.docx"
    with open(path, "wb") as f:
        f.write(b"PK\x03\x04") # dummy docx magic
    
    art = Artifact(project_id=project.id, artifact_type="srs", file_format="docx", file_path=path, original_filename="test.docx")
    db.add(art)
    db.commit()
    
    import app.pipeline.analyzer
    app.pipeline.analyzer.parse_srs = lambda *args: {"sections": ["1. Intro"], "requirements": [{"id": "FR-1", "text": "System shall do X."}]}
    
    return project, path

def test_analysis_reaches_done(monkeypatch):
    monkeypatch.setattr(engine, "get_provider", lambda: MockSuccessProvider())
    db = TestingSessionLocal()
    project, path = create_mock_project(db)
    
    run_analysis_pipeline(project.id)
    
    db.refresh(project)
    assert project.status == "done"
    
    if os.path.exists(path):
        os.remove(path)
    db.close()

def test_analysis_reaches_partial(monkeypatch):
    monkeypatch.setattr(engine, "get_provider", lambda: MockFailProvider())
    db = TestingSessionLocal()
    project, path = create_mock_project(db)
    
    run_analysis_pipeline(project.id)
    
    db.refresh(project)
    assert project.status == "partial"
    
    if os.path.exists(path):
        os.remove(path)
    db.close()


