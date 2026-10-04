from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from ..core.database import Base

class TraceLink(Base):
    __tablename__ = "trace_links"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False)
    source_type = Column(String, nullable=False)  # requirement, usecase, sequence
    source_id = Column(String, nullable=False)
    target_type = Column(String, nullable=False)  # usecase, sequence, class
    target_id = Column(String, nullable=False)
    status = Column(Enum("suggested", "confirmed", "rejected", name="link_status"), default="suggested")
    created_at = Column(DateTime, default=datetime.utcnow)

    submission = relationship("Submission", back_populates="trace_links")
