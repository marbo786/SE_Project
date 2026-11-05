from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class StrictInput(BaseModel):
    model_config = ConfigDict(extra='forbid')


class ArtifactSummary(BaseModel):
    id: int
    type: str
    filename: str
    sha256: str | None
    size_bytes: int | None


class RevisionOut(BaseModel):
    id: int
    project_id: int
    number: int
    parent_id: int | None
    state: Literal['draft', 'sealed']
    edit_version: int
    analysis_profile: Literal['srs_only', 'architecture']
    analysis_mode: Literal['deterministic', 'ai']
    extraction_confirmed: bool
    legacy_version: int | None
    created_at: str
    sealed_at: str | None
    artifacts: list[ArtifactSummary]


class RunOut(BaseModel):
    id: str
    project_id: int
    revision_id: int
    has_report: bool
    attempt_count: int
    cancel_requested: bool
    heartbeat_at: str | None
    status: Literal['queued', 'running', 'completed', 'partial', 'failed', 'cancelled']
    stage: str
    counts: dict[str, int]
    versions: dict[str, str]
    input_hash: str | None
    error_code: str | None
    error_message: str | None
    created_at: str
    started_at: str | None
    finished_at: str | None


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


class ProjectRename(StrictInput):
    name: str = Field(min_length=1, max_length=120)
    expected_name: str = Field(max_length=120)


class ManualTrace(StrictInput):
    source_type: Literal['requirement', 'usecase', 'sequence']
    source_id: str = Field(min_length=1, max_length=512)
    target_type: Literal['usecase', 'sequence', 'class']
    target_id: str = Field(min_length=1, max_length=512)
    reason: str = Field(min_length=1, max_length=4000)


class SuggestionInput(StrictInput):
    action: Literal['accepted', 'edited', 'rejected']
    expected_decision_id: int = Field(default=0, ge=0)
    draft_id: int | None = None
    text: str | None = Field(default=None, min_length=1, max_length=12000)
    confirm_intent: bool = False
