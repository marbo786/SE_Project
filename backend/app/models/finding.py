from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, Enum, Boolean
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
    source_ref = Column(String, nullable=True)
    finding_type = Column(String, default="deterministic")
    rewrite_suggestion = Column(Text, nullable=True)
    rewrite_attempts = Column(Integer, default=0)
    rewrite_passed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="findings")
