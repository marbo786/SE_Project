import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import json

engine_test = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_compare_versions():
    Base.metadata.create_all(bind=engine_test)
    db = TestingSessionLocal()
    # Create user
    from app.core.security import get_password_hash
    from app.models.user import User
    from app.models.project import Project
    from app.models.finding import Finding
    
    user = User(name="Test", email="test@ex.com", hashed_password=get_password_hash("pass"))
    db.add(user)
    db.commit()
    
    res = client.post("/auth/login", json={"email": "test@ex.com", "password": "pass"})
    token = res.json().get("access_token")
    if not token:
        print("Login failed:", res.json())
        assert False
    headers = {"Authorization": f"Bearer {token}"}
    
    # Project v1
    p1 = Project(name="Project A", version=1, status="done", user_id=user.id)
    db.add(p1)
    db.commit()
    
    # Project v2
    p2 = Project(name="Project A", version=2, status="done", user_id=user.id)
    db.add(p2)
    db.commit()
    
    # Finding in v1
    f1 = Finding(project_id=p1.id, rule_id="FR-101", artifact_type="srs", requirement_id="REQ-1", severity="major", explanation="Bad", quoted_text="Old Text")
    db.add(f1)
    
    # Finding in v2 (Same requirement, rewritten text)
    f2 = Finding(project_id=p2.id, rule_id="FR-101", artifact_type="srs", requirement_id="REQ-1", severity="major", explanation="Bad", quoted_text="New Text")
    db.add(f2)
    db.commit()
    
    # Compare v2 with v1
    res = client.get(f"/projects/{p2.id}/compare?with_version=1", headers=headers)
    assert res.status_code == 200
    data = res.json()
    
    # Because requirement_id is the same, it should match, meaning it's persistent!
    assert len(data['persistent_findings']) == 1
    assert len(data['new_findings']) == 0
    assert len(data['resolved_findings']) == 0
    
    # Now try without requirement_id (e.g. diagram error)
    f3_v1 = Finding(project_id=p1.id, rule_id="UML-01", artifact_type="uml", requirement_id=None, severity="major", explanation="Err", quoted_text="Missing relation")
    db.add(f3_v1)
    
    # Changed quoted text in v2
    f3_v2 = Finding(project_id=p2.id, rule_id="UML-01", artifact_type="uml", requirement_id=None, severity="major", explanation="Err", quoted_text="Missing relation fixed")
    db.add(f3_v2)
    db.commit()
    
    res = client.get(f"/projects/{p2.id}/compare?with_version=1", headers=headers)
    data = res.json()
    
    # Since quoted_text changed and no req ID, it should be 1 resolved, 1 new
    assert len(data['resolved_findings']) == 1
    assert len(data['new_findings']) == 1
    
    db.close()


