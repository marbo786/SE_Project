"""Revision/run application services. Callers commit once per command."""
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import uuid
from fastapi import HTTPException
from sqlalchemy import update
from ..core.config import get_settings, get_yaml_config
from ..core.time import utcnow, iso_utc
from ..models.project import Project
from ..models.artifact import Artifact
from ..models.user import User
from ..models.history import (ProjectRevision, AnalysisRun, RunFinding, RunTraceLink,
    RunQualityScore, Requirement, UMLElement, ReviewDecision, AuditEvent, IdempotencyRecord)

VERSIONS = {"parser": "2", "rules": "2", "rubric": "2", "report": "1", "ai": "3"}
ACTIVE = {"queued", "running"}
TERMINAL = {"completed", "partial", "failed", "cancelled"}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def audit(db, project, actor_id, action, **details):
    db.add(AuditEvent(project_id=project.id, actor_id=actor_id, action=action, details=details))


def lock_project(db, project):
    # UPDATE acquires the same writer lock on SQLite and a row lock on PostgreSQL.
    db.execute(update(Project).where(Project.id == project.id).values(next_revision_number=Project.next_revision_number))
    db.refresh(project)
    return project


def require_writable(project):
    if project.archived_at or project.deleted_at:
        raise HTTPException(409, "Restore this project before making changes")


def ensure_revision(db, project):
    if project.current_revision_id:
        return db.get(ProjectRevision, project.current_revision_id)
    # Compatibility for imported programmatic callers. Database migrations import
    # actual legacy projects, including their reports, before serving requests.
    lock_project(db, project)
    if project.current_revision_id:
        return db.get(ProjectRevision, project.current_revision_id)
    revision = ProjectRevision(project_id=project.id, number=1, author_id=project.user_id,
        analysis_profile=project.analysis_profile, analysis_mode=project.analysis_mode)
    db.add(revision); db.flush()
    project.current_revision_id, project.next_revision_number = revision.id, 2
    for artifact in db.query(Artifact).filter_by(project_id=project.id, revision_id=None):
        artifact.revision_id = revision.id
        artifact.lineage_key = artifact.lineage_key or f"artifact-{artifact.id}"
    db.flush()
    return revision


def revision_for(db, project, revision_id):
    revision = db.query(ProjectRevision).filter_by(id=revision_id, project_id=project.id).first()
    if not revision:
        raise HTTPException(404, "Revision not found")
    return revision


def edit_draft(db, project, revision, expected_version):
    require_writable(project)
    lock_project(db, project)
    if project.status == "analyzing":
        raise HTTPException(409, "Wait for the active analysis before editing")
    changed = db.query(ProjectRevision).filter_by(id=revision.id, project_id=project.id,
        state="draft", edit_version=expected_version).update({"edit_version": ProjectRevision.edit_version + 1}, synchronize_session=False)
    if not changed:
        db.rollback()
        raise HTTPException(409, "This draft changed or was sealed. Refresh before editing.")
    db.refresh(revision)
    return revision


def replay(db, actor_id, scope, key, body):
    if not key:
        return None
    if len(key) > 128 or not key.strip() or any(ord(c) < 32 for c in key):
        raise HTTPException(422, "Use an Idempotency-Key of 1–128 printable characters")
    # Serializes first insert as well as duplicate retries for this actor.
    db.execute(update(User).where(User.id == actor_id).values(name=User.name))
    saved = db.query(IdempotencyRecord).filter_by(actor_id=actor_id, scope=scope, key=key).first()
    if saved:
        if saved.request_hash != digest(body):
            raise HTTPException(409, "This idempotency key was already used with different input")
        return saved.response
    return None


def remember(db, actor_id, scope, key, body, response):
    if key:
        db.add(IdempotencyRecord(actor_id=actor_id, scope=scope, key=key, request_hash=digest(body), response=response))


def new_project(db, actor_id, data):
    project = Project(user_id=actor_id, **data, version=1, status="pending")
    db.add(project); db.flush()
    ensure_revision(db, project)
    audit(db, project, actor_id, "project_created")
    return project


def fork_draft(db, project, actor_id, parent_id=None):
    require_writable(project)
    lock_project(db, project)
    current = ensure_revision(db, project)
    parent_id = parent_id or current.id
    existing = db.query(ProjectRevision).filter_by(project_id=project.id, state="draft").first()
    if existing:
        if existing.id != parent_id and existing.parent_id != parent_id:
            raise HTTPException(409, "This project already has a draft from another revision")
        return existing
    parent = revision_for(db, project, parent_id)
    if project.status == "analyzing":
        raise HTTPException(409, "Wait for the active run before creating a draft")
    canonical = deepcopy(parent.canonical_inputs)
    if not canonical:
        parent_run = db.query(AnalysisRun).filter(AnalysisRun.revision_id == parent.id, AnalysisRun.status.in_(['completed', 'partial'])).order_by(AnalysisRun.created_at.desc()).first()
        if parent_run and isinstance((parent_run.report or {}).get('extractions'), dict):
            canonical = {'artifacts': deepcopy(parent_run.report['extractions']), 'edits': []}
    revision = ProjectRevision(project_id=project.id, number=project.next_revision_number,
        parent_id=parent.id, author_id=actor_id, analysis_profile=parent.analysis_profile,
        analysis_mode=parent.analysis_mode, canonical_inputs=canonical)
    project.next_revision_number += 1
    db.add(revision); db.flush()
    mapping = {}
    for original in db.query(Artifact).filter_by(revision_id=parent.id).all():
        clone = Artifact(project_id=project.id, revision_id=revision.id, lineage_key=original.lineage_key,
            artifact_type=original.artifact_type, file_format=original.file_format,
            file_path=original.file_path, original_filename=original.original_filename,
            content_hash=original.content_hash, size_bytes=original.size_bytes)
        db.add(clone); db.flush()
        mapping[str(original.id)] = str(clone.id)
    if revision.canonical_inputs:
        revision.canonical_inputs = remap_inputs(revision.canonical_inputs, mapping)
        persist_elements(db, revision)
    project.current_revision_id, project.version, project.status = revision.id, revision.number, "pending"
    project.analysis_error = None
    audit(db, project, actor_id, "draft_created", revision_id=revision.id, parent_id=parent.id)
    db.flush()
    return revision


def remap_inputs(inputs, mapping):
    value = deepcopy(inputs)
    artifacts = {}
    for old_id, extraction in value.get("artifacts", {}).items():
        if old_id not in mapping:
            continue
        new_id = mapping[old_id]
        def walk(item):
            if isinstance(item, dict):
                if "artifact_id" in item:
                    item["artifact_id"] = int(new_id)
                for child in item.values():
                    walk(child)
            elif isinstance(item, list):
                for child in item:
                    walk(child)
        walk(extraction)
        artifacts[new_id] = extraction
    value["artifacts"] = artifacts
    return value


def persist_elements(db, revision, inputs=None):
    db.query(Requirement).filter_by(revision_id=revision.id).delete()
    db.query(UMLElement).filter_by(revision_id=revision.id).delete()
    for artifact_id, extraction in (inputs or revision.canonical_inputs or {}).get("artifacts", {}).items():
        for req in extraction.get("requirements", []):
            db.add(Requirement(revision_id=revision.id, artifact_id=int(artifact_id), element_key=req['internal_id'],
                lineage_key=req['lineage_key'], authored_id=req.get('id'), text=req['text'],
                original_text=req.get('original_text', req['text']), data=req))
        for collection in ("actors", "use_cases", "classes", "participants", "messages"):
            for item in extraction.get(collection, []):
                db.add(UMLElement(revision_id=revision.id, artifact_id=int(artifact_id), element_key=item['id'],
                    kind=collection, name=item.get('name') or item.get('message') or item['id'], data=item))


def artifact_manifest(artifact):
    maximum = get_settings().MAX_UPLOAD_SIZE
    path = Path(artifact.file_path)
    with path.open('rb') as stream:
        content = stream.read(maximum + 1)
    if len(content) > maximum:
        raise HTTPException(409, "A stored input exceeds the supported size")
    checksum = hashlib.sha256(content).hexdigest()
    if artifact.content_hash and checksum != artifact.content_hash:
        raise HTTPException(409, "A stored input changed outside the application. Upload it to a new draft.")
    artifact.content_hash, artifact.size_bytes = checksum, len(content)
    artifact.lineage_key = artifact.lineage_key or f"artifact-{artifact.id}"
    return {"id": artifact.id, "lineage_key": artifact.lineage_key, "type": artifact.artifact_type,
        "format": artifact.file_format, "filename": artifact.original_filename, "sha256": checksum, "size_bytes": len(content)}


def start_run(db, project, revision, actor_id, *, idempotency_key=None, expected_version=None, validate=True):
    require_writable(project)
    lock_project(db, project)
    db.refresh(revision)
    if idempotency_key and db.query(AnalysisRun).filter_by(project_id=project.id, idempotency_key=idempotency_key).first():
        raise HTTPException(409, "This analysis idempotency key is already used by another request")
    if db.query(AnalysisRun).filter(AnalysisRun.project_id == project.id, AnalysisRun.status.in_(ACTIVE)).first():
        raise HTTPException(409, "An analysis is already queued or running")
    if expected_version is not None and revision.edit_version != expected_version:
        raise HTTPException(409, "This revision changed. Refresh before starting analysis.")
    artifacts = db.query(Artifact).filter_by(revision_id=revision.id).order_by(Artifact.id).all()
    required = {"srs", "uml_usecase", "uml_class", "uml_sequence"} if revision.analysis_profile == "architecture" else {"srs"}
    if validate and (missing := required - {a.artifact_type for a in artifacts}):
        raise HTTPException(409, "Upload the required inputs for this profile: " + ", ".join(sorted(missing)))
    if validate and revision.analysis_mode == "ai" and get_settings().LLM_PROVIDER == "mock":
        raise HTTPException(409, "AI analysis needs a configured provider. Use deterministic analysis for offline checks.")
    try:
        manifest = [artifact_manifest(a) for a in artifacts]
    except OSError:
        raise HTTPException(409, "A source file is unavailable. Restore it from backup or upload a replacement in a new draft.")
    snapshot = {"artifacts": manifest, "canonical": deepcopy(revision.canonical_inputs),
        "profile": revision.analysis_profile, "mode": revision.analysis_mode, "rules_config": deepcopy(get_yaml_config())}
    input_hash = digest({"artifacts": sorted([(a['lineage_key'], a['sha256'], a['type']) for a in manifest]),
        "edits": (revision.canonical_inputs or {}).get('edits', []), "profile": revision.analysis_profile,
        "mode": revision.analysis_mode, "rules_config": snapshot['rules_config']})
    revision.state, revision.sealed_at = "sealed", revision.sealed_at or utcnow()
    run = AnalysisRun(project_id=project.id, revision_id=revision.id, requested_by=actor_id,
        input_snapshot=snapshot, input_hash=input_hash, versions=VERSIONS.copy(), idempotency_key=idempotency_key)
    db.add(run); db.flush()
    from .jobs import enqueue
    enqueue(db, run)
    project.latest_run_id, project.status, project.analysis_error = run.id, "analyzing", None
    project.analysis_profile, project.analysis_mode = revision.analysis_profile, revision.analysis_mode
    audit(db, project, actor_id, "analysis_requested", run_id=run.id, revision_id=revision.id)
    return run


def run_summary(run):
    return {"id": run.id, "project_id": run.project_id, "revision_id": run.revision_id,
        "has_report": run.report is not None,
        "attempt_count": run.attempt_count, "cancel_requested": run.cancel_requested,
        "heartbeat_at": iso_utc(run.heartbeat_at),
        "status": run.status, "stage": run.stage, "counts": run.counts, "versions": run.versions,
        "input_hash": run.input_hash, "error_code": run.error_code, "error_message": run.error_message,
        "created_at": iso_utc(run.created_at), "started_at": iso_utc(run.started_at), "finished_at": iso_utc(run.finished_at)}


def revision_summary(db, revision):
    return {"id": revision.id, "project_id": revision.project_id, "number": revision.number,
        "parent_id": revision.parent_id, "state": revision.state, "edit_version": revision.edit_version,
        "analysis_profile": revision.analysis_profile, "analysis_mode": revision.analysis_mode,
        "extraction_confirmed": revision.extraction_confirmed, "legacy_version": revision.legacy_version,
        "created_at": iso_utc(revision.created_at), "sealed_at": iso_utc(revision.sealed_at),
        "artifacts": [{"id": a.id, "type": a.artifact_type, "filename": a.original_filename,
            "sha256": a.content_hash, "size_bytes": a.size_bytes} for a in db.query(Artifact).filter_by(revision_id=revision.id).order_by(Artifact.id)]}


def finding_fingerprint(finding, lineages):
    # Explanation is part of the identity: two missing sections or conflicts must
    # not collapse merely because they share a rule and affected requirement.
    return digest({"rule": finding.get('rule_id'), "element": lineages.get(finding.get('element_id'), finding.get('element_id')),
        "requirement": finding.get('requirement_id'), "artifact_type": finding.get('artifact_type'),
        "explanation": finding.get('explanation'), "related": finding.get('related_ids'), "quoted_text": finding.get('quoted_text')})


def trace_fingerprint(link):
    return digest({key: link.get(key) for key in ('source_type', 'source_id', 'target_type', 'target_id')})


def latest_decisions(db, run_id):
    decisions = {}
    for decision in db.query(ReviewDecision).filter_by(run_id=run_id).order_by(ReviewDecision.id):
        decisions[("finding" if decision.finding_id else "trace", decision.finding_id or decision.trace_id)] = decision
    return decisions


def compare_runs(db, left, right):
    if left.project_id != right.project_id:
        raise HTTPException(404, "Comparison run not found in this project")
    def indexed(run):
        result = defaultdict(list)
        for finding in db.query(RunFinding).filter_by(run_id=run.id).order_by(RunFinding.id):
            result[finding.fingerprint].append({**finding.data, "id": finding.id})
        return result
    before, after = indexed(left), indexed(right)
    resolved, added, persistent = [], [], []
    for key in sorted(before.keys() | after.keys()):
        count = min(len(before[key]), len(after[key]))
        persistent.extend(after[key][:count]); resolved.extend(before[key][count:]); added.extend(after[key][count:])
    def requirements(run):
        extractions = (run.report or {}).get('extractions', {})
        if not isinstance(extractions, dict):
            return {}
        return {req.get('lineage_key', req.get('internal_id')): req for extraction in extractions.values() for req in extraction.get('requirements', [])}
    old, new = requirements(left), requirements(right)
    comparable = left.versions == right.versions and left.versions.get('rubric') != 'unknown' and all(
        left.input_snapshot.get(key) == right.input_snapshot.get(key) for key in ('profile', 'mode', 'rules_config'))
    return {"previous_run_id": left.id, "current_run_id": right.id, "scores_comparable": comparable,
        "comparability_note": None if comparable else "Versions, scope or mode differ, or legacy provenance is unknown.",
        "resolved_findings": resolved, "new_findings": added, "persistent_findings": persistent,
        "requirements": {"added": [new[k] for k in new.keys() - old.keys()],
            "deleted": [old[k] for k in old.keys() - new.keys()],
            "changed": [{"before": old[k], "after": new[k]} for k in old.keys() & new.keys() if old[k]['text'] != new[k]['text']]}}
