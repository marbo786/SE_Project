from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base

class QualityScore(Base):
    __tablename__ = "quality_scores"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False, unique=True)
    requirements_score = Column(Float, default=0.0)
    uml_score = Column(Float, default=0.0)
    traceability_score = Column(Float, default=0.0)
    overall_score = Column(Float, default=0.0)
    computed_at = Column(DateTime, default=datetime.utcnow)

    submission = relationship("Submission", back_populates="quality_score")
