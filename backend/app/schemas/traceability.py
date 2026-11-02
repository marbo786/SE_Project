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
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TraceLinkUpdate(BaseModel):
    status: str  # confirmed or rejected

class TraceLinkCreate(BaseModel):
    source_type: str
    source_id: str
    target_type: str
    target_id: str
