from ..core.time import utcnow
from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from ..core.database import Base

class QualityScore(Base):
    __tablename__ = "quality_scores"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, unique=True)
    requirements_score = Column(Float, nullable=True)
    uml_score = Column(Float, nullable=True)
    traceability_score = Column(Float, nullable=True)
    overall_score = Column(Float, nullable=True)
    details = Column(JSON, nullable=True)
    computed_at = Column(DateTime, default=utcnow)

    project = relationship("Project", back_populates="quality_score")
