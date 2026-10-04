from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base

class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
    rule_id = Column(String, nullable=False)
    severity = Column(Enum("critical", "major", "minor", name="severity_enum"), nullable=False)
    quoted_text = Column(Text, nullable=True)
    explanation = Column(Text, nullable=False)
    artifact_type = Column(String, nullable=True)  # srs, uml, traceability
    requirement_id = Column(String, nullable=True)
    finding_type = Column(String, default="deterministic")  # deterministic or llm
    rewrite_suggestion = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    submission = relationship("Submission", back_populates="findings")
    instructor_decision = relationship("InstructorDecision", back_populates="finding", uselist=False, cascade="all, delete-orphan")


class InstructorDecision(Base):
    __tablename__ = "instructor_decisions"

    id = Column(Integer, primary_key=True, index=True)
    finding_id = Column(Integer, ForeignKey("findings.id"), nullable=False)
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum("accepted", "rejected", name="decision_status"), nullable=False)
    comment = Column(Text, nullable=True)
    decided_at = Column(DateTime, default=datetime.utcnow)

    finding = relationship("Finding", back_populates="instructor_decision")
    instructor = relationship("User")
