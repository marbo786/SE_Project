from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    team_name = Column(String, nullable=False)
    member_names = Column(Text, nullable=False)  # JSON string list
    version = Column(Integer, default=1)
    status = Column(String, default="pending")  # pending, analyzing, done, error
    created_at = Column(DateTime, default=datetime.utcnow)

    assignment = relationship("Assignment", back_populates="submissions")
    student = relationship("User")
    artifacts = relationship("Artifact", back_populates="submission", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="submission", cascade="all, delete-orphan")
    trace_links = relationship("TraceLink", back_populates="submission", cascade="all, delete-orphan")
    llm_logs = relationship("LLMLog", back_populates="submission", cascade="all, delete-orphan")
    quality_score = relationship("QualityScore", back_populates="submission", uselist=False, cascade="all, delete-orphan")
