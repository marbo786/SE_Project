from ..core.time import utcnow
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from ..core.database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    version = Column(Integer, default=1)
    status = Column(String, default="pending")  # pending, analyzing, done, error
    analysis_profile = Column(String, default="srs_only", nullable=False)
    analysis_mode = Column(String, default="deterministic", nullable=False)
    analysis_error = Column(Text, nullable=True)
    next_revision_number = Column(Integer, default=2, nullable=False)
    current_revision_id = Column(Integer, ForeignKey("project_revisions.id", name="fk_project_current_revision", use_alter=True), nullable=True)
    latest_run_id = Column(String(36), ForeignKey("analysis_runs.id", name="fk_project_latest_run", use_alter=True), nullable=True)
    published_run_id = Column(String(36), ForeignKey("analysis_runs.id", name="fk_project_published_run", use_alter=True), nullable=True)
    archived_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User")
    artifacts = relationship("Artifact", back_populates="project", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="project", cascade="all, delete-orphan")
    trace_links = relationship("TraceLink", back_populates="project", cascade="all, delete-orphan")
    llm_logs = relationship("LLMLog", back_populates="project", cascade="all, delete-orphan")
    quality_score = relationship("QualityScore", back_populates="project", uselist=False, cascade="all, delete-orphan")
