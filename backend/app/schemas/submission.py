from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class SubmissionCreate(BaseModel):
    assignment_id: int
    team_name: str
    member_names: List[str]

class SubmissionOut(BaseModel):
    id: int
    assignment_id: int
    team_name: str
    member_names: str
    version: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
