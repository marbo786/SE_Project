from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectOut(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str]
    version: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
