from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AssignmentCreate(BaseModel):
    title: str
    course_code: str
    due_date: Optional[datetime] = None

class AssignmentOut(BaseModel):
    id: int
    title: str
    course_code: str
    due_date: Optional[datetime]
    instructor_id: int
    created_at: datetime

    class Config:
        from_attributes = True
