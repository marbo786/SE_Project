"""Immutable analysis data; legacy tables remain compatibility projections."""
import uuid
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON, Float, UniqueConstraint, CheckConstraint, Index
from ..core.database import Base
from ..core.time import utcnow


class ProjectRevision(Base):
    __tablename__ = "project_revisions"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    number = Column(Integer, nullable=False)
    parent_id = Column(Integer, ForeignKey("project_revisions.id"), nullable=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    state = Column(String(16), nullable=False, default="draft")
    edit_version = Column(Integer, nullable=False, default=1)
    analysis_profile = Column(String(32), nullable=False, default="srs_only")
    analysis_mode = Column(String(32), nullable=False, default="deterministic")
    canonical_inputs = Column(JSON, nullable=True)
    extraction_confirmed = Column(Boolean, nullable=False, default=False)
    legacy_version = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    sealed_at = Column(DateTime, nullable=True)
    __table_args__ = (
        UniqueConstraint("project_id", "number", name="uq_revision_number"),
        CheckConstraint("state IN ('draft', 'sealed')", name="ck_revision_state"),
        Index("uq_project_open_draft", "project_id", unique=True, sqlite_where=state == "draft", postgresql_where=state == "draft"),
    )


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    revision_id = Column(Integer, ForeignKey("project_revisions.id"), nullable=False, index=True)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), nullable=False, default="queued", index=True)
    stage = Column(String(40), nullable=False, default="queued")
    counts = Column(JSON, nullable=False, default=dict)
    input_snapshot = Column(JSON, nullable=False, default=dict)
    input_hash = Column(String(64), nullable=True)
    versions = Column(JSON, nullable=False, default=dict)
    report = Column(JSON, nullable=True)
    idempotency_key = Column(String(128), nullable=True)
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    attempt_id = Column(String(36), nullable=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    heartbeat_at = Column(DateTime, nullable=True)
    lease_expires_at = Column(DateTime, nullable=True, index=True)
    cancel_requested = Column(Boolean, nullable=False, default=False)
    __table_args__ = (UniqueConstraint("project_id", "idempotency_key", name="uq_run_request"),
        CheckConstraint("status IN ('queued', 'running', 'completed', 'partial', 'failed', 'cancelled')", name="ck_run_status"))


class RunFinding(Base):
    __tablename__ = "run_findings"
    id = Column(Integer, primary_key=True)
    run_id = Column(String(36), ForeignKey("analysis_runs.id"), nullable=False, index=True)
    fingerprint = Column(String(64), nullable=False, index=True)
    rule_id = Column(String(64), nullable=False)
    severity = Column(String(16), nullable=False)
    element_key = Column(String(512), nullable=True)
    data = Column(JSON, nullable=False)


class OutboxEvent(Base):
    __tablename__ = 'outbox_events'
    id = Column(Integer, primary_key=True)
    run_id = Column(String(36), ForeignKey('analysis_runs.id'), nullable=False, unique=True)
    available_at = Column(DateTime, nullable=False, default=utcnow, index=True)
    published_at = Column(DateTime, nullable=True)
    dispatch_attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(String(64), nullable=True)


class RunStage(Base):
    __tablename__ = 'run_stages'
    id = Column(Integer, primary_key=True)
    run_id = Column(String(36), ForeignKey('analysis_runs.id'), nullable=False, index=True)
    stage = Column(String(80), nullable=False)
    attempt_id = Column(String(36), nullable=False)
    output_hash = Column(String(64), nullable=False)
    output = Column(JSON, nullable=False)
    completed_at = Column(DateTime, nullable=False, default=utcnow)
    __table_args__ = (UniqueConstraint('run_id', 'stage', name='uq_run_stage'),)


class RunTraceLink(Base):
    __tablename__ = "run_trace_links"
    id = Column(Integer, primary_key=True)
    run_id = Column(String(36), ForeignKey("analysis_runs.id"), nullable=False, index=True)
    fingerprint = Column(String(64), nullable=False, index=True)
    source_type = Column(String(32), nullable=False)
    source_id = Column(String(512), nullable=False)
    target_type = Column(String(32), nullable=False)
    target_id = Column(String(512), nullable=False)
    data = Column(JSON, nullable=False)
    __table_args__ = (UniqueConstraint("run_id", "source_type", "source_id", "target_type", "target_id", name="uq_run_trace_endpoints"),)


class RunQualityScore(Base):
    __tablename__ = "run_quality_scores"
    run_id = Column(String(36), ForeignKey("analysis_runs.id"), primary_key=True)
    overall_score = Column(Float, nullable=True)
    payload = Column(JSON, nullable=False)
    computed_at = Column(DateTime, nullable=False, default=utcnow)


class Requirement(Base):
    __tablename__ = "requirements"
    id = Column(Integer, primary_key=True)
    revision_id = Column(Integer, ForeignKey("project_revisions.id"), nullable=False, index=True)
    artifact_id = Column(Integer, ForeignKey("artifacts.id"), nullable=False)
    element_key = Column(String(512), nullable=False)
    lineage_key = Column(String(64), nullable=False, default=lambda: uuid.uuid4().hex)
    authored_id = Column(Text, nullable=True)
    text = Column(Text, nullable=False)
    original_text = Column(Text, nullable=False)
    data = Column(JSON, nullable=False)
    __table_args__ = (UniqueConstraint("revision_id", "element_key", name="uq_requirement_occurrence"),)


class UMLElement(Base):
    __tablename__ = "uml_elements"
    id = Column(Integer, primary_key=True)
    revision_id = Column(Integer, ForeignKey("project_revisions.id"), nullable=False, index=True)
    artifact_id = Column(Integer, ForeignKey("artifacts.id"), nullable=False)
    element_key = Column(String(512), nullable=False)
    kind = Column(String(32), nullable=False)
    name = Column(Text, nullable=False)
    data = Column(JSON, nullable=False)
    __table_args__ = (UniqueConstraint("revision_id", "element_key", name="uq_uml_occurrence"),)


class ReviewDecision(Base):
    __tablename__ = "review_decisions"
    id = Column(Integer, primary_key=True)
    run_id = Column(String(36), ForeignKey("analysis_runs.id"), nullable=False, index=True)
    finding_id = Column(Integer, ForeignKey("run_findings.id"), nullable=True)
    trace_id = Column(Integer, ForeignKey("run_trace_links.id"), nullable=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(20), nullable=False)
    origin = Column(String(32), nullable=False, default="manual")
    reason = Column(Text, nullable=True)
    carried_from_id = Column(Integer, ForeignKey("review_decisions.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    __table_args__ = (CheckConstraint("(finding_id IS NOT NULL AND trace_id IS NULL) OR (finding_id IS NULL AND trace_id IS NOT NULL)", name="ck_decision_target"),)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(Integer, primary_key=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(64), nullable=False)
    details = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=utcnow)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    id = Column(Integer, primary_key=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    scope = Column(String(100), nullable=False)
    key = Column(String(128), nullable=False)
    request_hash = Column(String(64), nullable=False)
    response = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    __table_args__ = (UniqueConstraint("actor_id", "scope", "key", name="uq_idempotency_request"),)


class SuggestionDecision(Base):
    __tablename__ = "suggestion_decisions"
    id = Column(Integer, primary_key=True)
    run_id = Column(String(36), ForeignKey("analysis_runs.id"), nullable=False, index=True)
    finding_id = Column(Integer, ForeignKey("run_findings.id"), nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(16), nullable=False)
    draft_id = Column(Integer, ForeignKey("project_revisions.id"))
    replacement_text = Column(Text)
    created_at = Column(DateTime, nullable=False, default=utcnow)
