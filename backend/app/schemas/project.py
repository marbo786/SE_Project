from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=4000)

    @field_validator("name")
    @classmethod
    def valid_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Enter a project name")
        return value

class ProjectOut(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str]
    version: int
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
