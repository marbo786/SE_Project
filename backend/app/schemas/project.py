from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Literal
from datetime import datetime

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=4000)
    analysis_profile: Literal["srs_only", "architecture"] = "srs_only"
    analysis_mode: Literal["deterministic", "ai"] = "deterministic"

    @field_validator("name")
    @classmethod
    def valid_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Enter a project name")
        return value

class ScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    requirements_score: Optional[float]
    uml_score: Optional[float]
    traceability_score: Optional[float]
    overall_score: Optional[float]
    details: Optional[dict] = None
    computed_at: datetime


class ProjectOut(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str]
    version: int
    status: str
    analysis_profile: str
    analysis_mode: str
    analysis_error: Optional[str] = None
    current_revision_id: Optional[int] = None
    latest_run_id: Optional[str] = None
    published_run_id: Optional[str] = None
    archived_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    quality_score: Optional[ScoreOut] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
