import os

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + '\n')

def delete_file(path):
    if os.path.exists(path):
        os.remove(path)

# --- 1. CORE DEPS ---
write_file('backend/app/core/deps.py', """
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db
from .security import decode_token
from ..models.user import User

bearer_scheme = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user_id: int = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
""")

# --- 2. MODELS ---
write_file('backend/app/models/user.py', """
from sqlalchemy import Column, Integer, String
from ..core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
""")

write_file('backend/app/models/project.py', """
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    version = Column(Integer, default=1)
    status = Column(String, default="pending")  # pending, analyzing, done, error
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    artifacts = relationship("Artifact", back_populates="project", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="project", cascade="all, delete-orphan")
    trace_links = relationship("TraceLink", back_populates="project", cascade="all, delete-orphan")
    llm_logs = relationship("LLMLog", back_populates="project", cascade="all, delete-orphan")
""")

write_file('backend/app/models/artifact.py', """
from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base

class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    artifact_type = Column(String, nullable=False)
    file_format = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    extracted_content = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="artifacts")
""")

write_file('backend/app/models/finding.py', """
from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base

class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    rule_id = Column(String, nullable=False)
    severity = Column(Enum("critical", "major", "minor", name="severity_enum"), nullable=False)
    quoted_text = Column(Text, nullable=True)
    explanation = Column(Text, nullable=False)
    artifact_type = Column(String, nullable=True)
    requirement_id = Column(String, nullable=True)
    finding_type = Column(String, default="deterministic")
    rewrite_suggestion = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="findings")
""")

write_file('backend/app/models/traceability.py', """
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base

class TraceLink(Base):
    __tablename__ = "trace_links"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    source_type = Column(String, nullable=False)
    source_id = Column(String, nullable=False)
    target_type = Column(String, nullable=False)
    target_id = Column(String, nullable=False)
    status = Column(Enum("suggested", "confirmed", "rejected", name="link_status"), default="suggested")
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="trace_links")
""")

write_file('backend/app/models/score.py', """
from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base

class QualityScore(Base):
    __tablename__ = "quality_scores"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, unique=True)
    requirements_score = Column(Float, default=0.0)
    uml_score = Column(Float, default=0.0)
    traceability_score = Column(Float, default=0.0)
    overall_score = Column(Float, default=0.0)
    computed_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project")
""")

write_file('backend/app/models/llm_log.py', """
from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base

class LLMLog(Base):
    __tablename__ = "llm_logs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    latency_ms = Column(Float, default=0.0)
    cache_hit = Column(String, default="false")
    prompt_hash = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="llm_logs")
""")

# Delete old assignment/submission models
delete_file('backend/app/models/assignment.py')
delete_file('backend/app/models/submission.py')
