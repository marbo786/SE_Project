from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class FindingOut(BaseModel):
    id: int
    rule_id: str
    severity: str
    quoted_text: Optional[str]
    explanation: str
    artifact_type: Optional[str]
    requirement_id: Optional[str]
    finding_type: str
    rewrite_suggestion: Optional[str]
    created_at: datetime
    instructor_decision: Optional[dict] = None

    class Config:
        from_attributes = True

class DecisionCreate(BaseModel):
    status: str  # accepted or rejected
    comment: Optional[str] = None
