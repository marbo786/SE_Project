from ..core.time import utcnow
from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from ..core.database import Base

class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    revision_id = Column(Integer, ForeignKey("project_revisions.id", name="fk_artifact_revision"), nullable=True, index=True)
    lineage_key = Column(String(64), nullable=True)
    content_hash = Column(String(64), nullable=True)
    size_bytes = Column(Integer, nullable=True)
    artifact_type = Column(String, nullable=False)
    file_format = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    extracted_content = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    project = relationship("Project", back_populates="artifacts")
