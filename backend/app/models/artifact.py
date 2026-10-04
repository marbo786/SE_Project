from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base

class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
    artifact_type = Column(String, nullable=False)  # srs, uml_usecase, uml_class, uml_sequence
    file_format = Column(String, nullable=False)  # docx, pdf, plantuml
    file_path = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    extracted_content = Column(Text, nullable=True)  # JSON: requirements or UML model
    created_at = Column(DateTime, default=datetime.utcnow)

    submission = relationship("Submission", back_populates="artifacts")
