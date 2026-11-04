from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class StrictInput(BaseModel):
    model_config = ConfigDict(extra='forbid')


class DraftCreate(StrictInput):
    parent_revision_id: int | None = None


class RevisionUpdate(StrictInput):
    analysis_profile: Literal['srs_only', 'architecture'] | None = None
    analysis_mode: Literal['deterministic', 'ai'] | None = None
    extraction_confirmed: bool | None = None


class RequirementUpdate(StrictInput):
    text: str | None = Field(default=None, min_length=1, max_length=20000)
    id: str | None = Field(default=None, max_length=128)
    classification: Literal['functional', 'non_functional'] | None = Field(default=None, alias='class')
    subtype: Literal['performance', 'availability', 'security', 'usability', 'reliability', 'maintainability', 'portability', 'other'] | None = None


class DecisionCreate(StrictInput):
    target_type: Literal['finding', 'trace']
    target_id: int
    status: Literal['suggested', 'confirmed', 'rejected', 'accepted', 'dismissed', 'needs_review']
    reason: str | None = Field(default=None, max_length=4000)
    expected_decision_id: int = Field(default=0, ge=0)


class ProjectLifecycle(StrictInput):
    action: Literal['archive', 'restore', 'delete']
    confirmation: str | None = None


class SuggestionInput(StrictInput):
    action: Literal['accepted', 'edited', 'rejected']
    expected_decision_id: int = Field(default=0, ge=0)
    draft_id: int | None = None
    text: str | None = Field(default=None, min_length=1, max_length=12000)
    confirm_intent: bool = False
