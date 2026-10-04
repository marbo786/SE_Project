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
