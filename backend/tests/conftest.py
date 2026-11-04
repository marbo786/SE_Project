"""Tests use disposable data, never the user's configured database."""
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_test_directory = TemporaryDirectory(prefix="srs-tests-")
os.environ["TESTING"] = "true"
os.environ["SECRET_KEY"] = "isolated-tests-only-secret-at-least-32-characters"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["LLM_RUN_COST_BUDGET_MICROUSD"] = "0"
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_test_directory.name) / "bootstrap.db")
os.environ["UPLOAD_DIR"] = str(Path(_test_directory.name) / "uploads")


def pytest_sessionfinish(session, exitstatus):
    from app.core.database import engine
    engine.dispose()
    _test_directory.cleanup()


@pytest.fixture
def db_session(tmp_path, monkeypatch):
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.main import app
    from app.core.database import Base, get_db
    from app.core.config import get_settings
    from app.pipeline import analyzer
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(analyzer, "SessionLocal", factory)
    monkeypatch.setattr(get_settings(), "UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setattr(get_settings(), "MAIL_SINK_DIR", str(tmp_path / "mail"))
    monkeypatch.setattr(get_settings(), "SMTP_HOST", "")
    def override_db():
        with factory() as session:
            yield session
    app.dependency_overrides[get_db] = override_db
    try:
        with factory() as session:
            yield session
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


@pytest.fixture
def client(db_session):
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def account(client):
    response = client.post("/auth/register", json={"name": "Reviewer", "email": "reviewer@example.com", "password": "testing-password-123"})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def headers(account):
    return {"Authorization": "Bearer " + account["access_token"]}
