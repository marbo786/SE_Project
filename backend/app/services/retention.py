"""Explicit maintenance, dry-run by default; only expired soft deletions qualify."""
from datetime import timedelta
from sqlalchemy import or_
from ..core.time import utcnow
from ..core.uploads import remove_unreferenced_file
from ..models.project import Project
from ..models.artifact import Artifact
from ..models.finding import Finding
from ..models.traceability import TraceLink
from ..models.score import QualityScore
from ..models.llm_log import LLMLog
from ..models.history import (ProjectRevision, AnalysisRun, RunFinding, RunTraceLink,
    RunQualityScore, ReviewDecision, Requirement, UMLElement, IdempotencyRecord)
from .history import ACTIVE, lock_project, audit


def purge_expired(db, *, apply=False, now=None):
    cutoff = (now or utcnow()) - timedelta(days=30)
    candidates = db.query(Project).filter(Project.deleted_at <= cutoff).order_by(Project.id).all()
    result = {'apply': apply, 'eligible_project_ids': [], 'purged_project_ids': []}
    for project in candidates:
        lock_project(db, project)
        if not project.deleted_at or project.deleted_at > cutoff:
            continue
        if db.query(AnalysisRun).filter(AnalysisRun.project_id == project.id, AnalysisRun.status.in_(ACTIVE)).first():
            continue
        result['eligible_project_ids'].append(project.id)
        if not apply:
            continue
        pid = project.id
        runs = [r.id for r in db.query(AnalysisRun).filter_by(project_id=pid)]
        revisions = [r.id for r in db.query(ProjectRevision).filter_by(project_id=pid)]
        paths = [a.file_path for a in db.query(Artifact).filter_by(project_id=pid)]
        audit(db, project, None, 'project_purged', original_project_id=pid, retention_days=30)
        project.current_revision_id = project.latest_run_id = project.published_run_id = None
        db.flush()
        db.query(ReviewDecision).filter(ReviewDecision.run_id.in_(runs)).delete(synchronize_session=False)
        for model in (RunFinding, RunTraceLink, RunQualityScore):
            db.query(model).filter(model.run_id.in_(runs)).delete(synchronize_session=False)
        for model in (Requirement, UMLElement):
            db.query(model).filter(model.revision_id.in_(revisions)).delete(synchronize_session=False)
        for model in (Finding, TraceLink, QualityScore, LLMLog, Artifact, AnalysisRun):
            db.query(model).filter_by(project_id=pid).delete(synchronize_session=False)
        db.query(ProjectRevision).filter_by(project_id=pid).delete(synchronize_session=False)
        scopes = [f'draft:{pid}', f'run:{pid}', f'legacy_run:{pid}', *[f'upload:{rid}' for rid in revisions]]
        db.query(IdempotencyRecord).filter(IdempotencyRecord.actor_id == project.user_id, or_(
            IdempotencyRecord.scope.in_(scopes),
            (IdempotencyRecord.scope == 'project_create') & (IdempotencyRecord.response['id'].as_integer() == pid))).delete(synchronize_session=False)
        db.query(Project).filter_by(id=pid).delete(synchronize_session=False)
        db.commit()
        for path in set(paths):
            remove_unreferenced_file(db, path)
        result['purged_project_ids'].append(pid)
    if not apply:
        db.rollback()
    return result
