from ..core.time import utcnow
from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime, Text, BigInteger
from sqlalchemy.orm import relationship
from ..core.database import Base

class LLMLog(Base):
    __tablename__ = "llm_logs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    latency_ms = Column(Float, default=0.0)
    cache_hit = Column(String, default="false")
    prompt_hash = Column(String, nullable=True)
    response_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    project = relationship("Project", back_populates="llm_logs")



class LLMCall(Base):
    """Minimal accounting only: never store prompts or completions here."""
    __tablename__ = "llm_calls"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    run_id = Column(String(36), ForeignKey("analysis_runs.id"), index=True)
    provider = Column(String(80), nullable=False)
    model = Column(String(200), nullable=False)
    prompt_hash = Column(String(64), nullable=False)
    status = Column(String(40), nullable=False)
    usage_source = Column(String(30), nullable=False)
    reserved_tokens = Column(Integer, nullable=False)
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    latency_ms = Column(Float)
    reserved_cost_microusd = Column(BigInteger)
    reported_cost_microusd = Column(BigInteger)
    input_price = Column(BigInteger)
    output_price = Column(BigInteger)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class LLMCache(Base):
    __tablename__ = "llm_cache"
    key = Column(String(64), primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    response_text = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
