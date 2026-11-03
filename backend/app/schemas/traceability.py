from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class TraceLinkOut(BaseModel):
    id: int
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    status: str
    source_label: Optional[str] = None
    target_label: Optional[str] = None
    confidence: Optional[float] = None
    origin: str = "legacy"
    evidence: Optional[dict] = None
    is_stale: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TraceLinkUpdate(BaseModel):
    status: str  # confirmed or rejected

class TraceLinkCreate(BaseModel):
    source_type: str
    source_id: str
    target_type: str
    target_id: str
