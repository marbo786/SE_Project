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
    source_ref: Optional[str] = None
    finding_type: str
    rewrite_suggestion: Optional[str]
    rewrite_attempts: Optional[int] = 0
    rewrite_passed: Optional[bool] = False
    created_at: datetime

    class Config:
        from_attributes = True
