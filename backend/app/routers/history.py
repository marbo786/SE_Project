"""Versioned contracts, served as /api/v1 by the same-origin reverse proxy."""
from copy import deepcopy
from datetime import timedelta
import hashlib
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..core.config import get_settings
from ..core.database import get_db
from ..core.deps import get_current_user, require_project_access
from ..core.limits import enforce_limit
from ..core.time import utcnow, iso_utc
from ..core.uploads import accept_upload, store_artifact, remove_unreferenced_file
from ..models.user import User
from ..models.project import Project
from ..models.artifact import Artifact
from ..models.history import ProjectRevision, AnalysisRun, RunFinding, RunTraceLink, ReviewDecision, Requirement, UMLElement
from ..schemas.project import ProjectCreate, ProjectOut
from ..schemas.history import DraftCreate, RevisionUpdate, RequirementUpdate, DecisionCreate, ProjectLifecycle
from ..services import history as service
from ..services.extraction import extract_draft, correct_requirement
from ..pipeline.analyzer import run_analysis_pipeline

router = APIRouter(prefix='/v1', tags=['revisions and runs'])


def expected_version(if_match):
    if if_match is None:
        raise HTTPException(428, 'Send the current edit_version in the If-Match header')
    try:
        value = int(if_match.strip('"'))
        if value < 1:
            raise ValueError()
        return value
    except ValueError:
        raise HTTPException(422, 'If-Match must be a positive edit_version')


def run_access(db, user, run_id):
    run = db.get(AnalysisRun, run_id)
    if not run:
        raise HTTPException(404, 'Run not found')
    require_project_access(db, user, run.project_id)
    return run


def project_view(project):
    return ProjectOut.model_validate(project).model_dump(mode='json')


@router.get('/projects')
def projects(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
             archived: bool = False, search: str = Query('', max_length=120),
             status: str | None = Query(None, max_length=20), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(Project).filter(Project.user_id == user.id, Project.deleted_at.is_(None))
    query = query.filter(Project.archived_at.is_not(None) if archived else Project.archived_at.is_(None))
    if search:
        query = query.filter(Project.name.icontains(search, autoescape=True))
    if status:
        query = query.filter(Project.status == status)
    return {'items': [project_view(p) for p in query.order_by(Project.created_at.desc(), Project.id.desc()).offset(offset).limit(limit)],
        'total': query.count(), 'limit': limit, 'offset': offset}


@router.post('/projects', status_code=201)
def create_project(data: ProjectCreate, idempotency_key: str | None = Header(None),
                   db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    body = data.model_dump()
    if saved := service.replay(db, user.id, 'project_create', idempotency_key, body):
        return saved
    # Limits commit their bucket, so take them before the command transaction.
    db.rollback()
    enforce_limit(db, f'create:{user.id}', 20, 3600)
    if saved := service.replay(db, user.id, 'project_create', idempotency_key, body):
        return saved
    if db.query(Project).filter_by(user_id=user.id).count() >= get_settings().MAX_PROJECTS_PER_USER:
        raise HTTPException(409, 'Project quota reached')
    project = service.new_project(db, user.id, body)
    result = project_view(project)
    service.remember(db, user.id, 'project_create', idempotency_key, body, result)
    db.commit()
    return result


@router.get('/projects/{project_id}')
def get_project(project_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return project_view(require_project_access(db, user, project_id))


@router.get('/projects/{project_id}/revisions')
def revisions(project_id: int, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
              db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_project_access(db, user, project_id)
    query = db.query(ProjectRevision).filter_by(project_id=project_id)
    return {'items': [service.revision_summary(db, r) for r in query.order_by(ProjectRevision.number.desc()).offset(offset).limit(limit)], 'total': query.count()}


@router.post('/projects/{project_id}/drafts', status_code=201)
def create_draft(project_id: int, data: DraftCreate, idempotency_key: str | None = Header(None),
                 db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = require_project_access(db, user, project_id)
    scope, body = f'draft:{project_id}', data.model_dump()
    if saved := service.replay(db, user.id, scope, idempotency_key, body):
        return saved
    revision = service.fork_draft(db, project, user.id, data.parent_revision_id)
    result = service.revision_summary(db, revision)
    service.remember(db, user.id, scope, idempotency_key, body, result)
    db.commit()
    return result


@router.get('/projects/{project_id}/revisions/{revision_id}')
def get_revision(project_id: int, revision_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = require_project_access(db, user, project_id)
    return service.revision_summary(db, service.revision_for(db, project, revision_id))


@router.patch('/projects/{project_id}/revisions/{revision_id}')
def edit_revision(project_id: int, revision_id: int, data: RevisionUpdate, if_match: str | None = Header(None),
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = require_project_access(db, user, project_id)
    revision = service.revision_for(db, project, revision_id)
    service.edit_draft(db, project, revision, expected_version(if_match))
    if data.extraction_confirmed and not revision.canonical_inputs:
        raise HTTPException(409, 'Extract and review the draft before confirming it')
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(revision, key, value)
    service.audit(db, project, user.id, 'draft_updated', revision_id=revision.id, fields=list(data.model_fields_set))
    db.commit()
    return service.revision_summary(db, revision)


@router.post('/projects/{project_id}/revisions/{revision_id}/artifacts', status_code=201)
async def upload(project_id: int, revision_id: int, kind: str = Form(...), file: UploadFile = File(...),
                 replace_artifact_id: int | None = Form(None), if_match: str | None = Header(None),
                 idempotency_key: str | None = Header(None), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = require_project_access(db, user, project_id)
    revision = service.revision_for(db, project, revision_id)
    version = expected_version(if_match)
    if kind not in {'srs', 'uml_usecase', 'uml_class', 'uml_sequence'}:
        raise HTTPException(422, 'Unsupported artifact type')
    enforce_limit(db, f'upload:{user.id}', 30, 3600)
    content, format, filename = await accept_upload(file, uml=kind != 'srs')
    scope = f'upload:{revision.id}'
    body = {'kind': kind, 'filename': filename, 'sha256': hashlib.sha256(content).hexdigest(), 'replace': replace_artifact_id, 'edit_version': version}
    if saved := service.replay(db, user.id, scope, idempotency_key, body):
        return saved
    old = db.get(Artifact, replace_artifact_id).file_path if replace_artifact_id and db.query(Artifact).filter_by(id=replace_artifact_id, revision_id=revision.id).first() else None
    artifact = store_artifact(db, project, kind, content, format, filename, revision=revision,
        expected_version=version, replace_id=replace_artifact_id, append=True, commit=False)
    result = {'artifact_id': artifact.id, 'revision': service.revision_summary(db, revision)}
    service.remember(db, user.id, scope, idempotency_key, body, result)
    db.commit()
    if old:
        remove_unreferenced_file(db, old)
    return result


@router.delete('/projects/{project_id}/revisions/{revision_id}/artifacts/{artifact_id}')
def remove_artifact(project_id: int, revision_id: int, artifact_id: int, if_match: str | None = Header(None),
                    db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = require_project_access(db, user, project_id)
    revision = service.revision_for(db, project, revision_id)
    service.edit_draft(db, project, revision, expected_version(if_match))
    artifact = db.query(Artifact).filter_by(id=artifact_id, revision_id=revision.id).first()
    if not artifact:
        raise HTTPException(404, 'Artifact not found')
    path = artifact.file_path
    db.query(Requirement).filter_by(revision_id=revision.id).delete()
    db.query(UMLElement).filter_by(revision_id=revision.id).delete()
    revision.canonical_inputs, revision.extraction_confirmed = None, False
    db.delete(artifact)
    service.audit(db, project, user.id, 'artifact_removed', revision_id=revision.id, artifact_id=artifact.id)
    db.commit(); remove_unreferenced_file(db, path)
    return service.revision_summary(db, revision)


@router.get('/projects/{project_id}/artifacts/{artifact_id}/source')
def source(project_id: int, artifact_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_project_access(db, user, project_id)
    artifact = db.query(Artifact).filter_by(id=artifact_id, project_id=project_id).first()
    root = Path(get_settings().UPLOAD_DIR).resolve()
    path = Path(artifact.file_path).resolve() if artifact else None
    if not path or path.parent != root or not path.is_file():
        raise HTTPException(404, 'Source file is unavailable')
    return FileResponse(path, filename=artifact.original_filename, media_type='application/octet-stream',
        headers={'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'})


@router.post('/projects/{project_id}/revisions/{revision_id}/extraction')
def extract(project_id: int, revision_id: int, if_match: str | None = Header(None),
            db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = require_project_access(db, user, project_id)
    revision = service.revision_for(db, project, revision_id)
    service.edit_draft(db, project, revision, expected_version(if_match))
    if not revision.canonical_inputs:
        extract_draft(db, revision)
    service.audit(db, project, user.id, 'draft_extracted', revision_id=revision.id)
    db.commit()
    return {'edit_version': revision.edit_version, **revision.canonical_inputs}


@router.get('/projects/{project_id}/revisions/{revision_id}/extraction')
def extraction(project_id: int, revision_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = require_project_access(db, user, project_id)
    revision = service.revision_for(db, project, revision_id)
    return {'edit_version': revision.edit_version, 'canonical': revision.canonical_inputs}


@router.patch('/projects/{project_id}/revisions/{revision_id}/requirements/{element_key}')
def correction(project_id: int, revision_id: int, element_key: str, data: RequirementUpdate,
               if_match: str | None = Header(None), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = require_project_access(db, user, project_id)
    revision = service.revision_for(db, project, revision_id)
    service.edit_draft(db, project, revision, expected_version(if_match))
    changes = data.model_dump(exclude_unset=True, by_alias=True)
    if any(value is None and key != 'id' for key, value in changes.items()):
        raise HTTPException(422, 'Only an authored ID may be cleared')
    requirement = correct_requirement(db, revision, element_key, changes)
    service.audit(db, project, user.id, 'extraction_corrected', revision_id=revision.id, element_key=element_key, fields=list(changes))
    db.commit()
    return {'edit_version': revision.edit_version, 'requirement': requirement}


@router.post('/projects/{project_id}/revisions/{revision_id}/runs', status_code=202)
def analyze(project_id: int, revision_id: int, background_tasks: BackgroundTasks,
            if_match: str | None = Header(None), idempotency_key: str | None = Header(None),
            db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = require_project_access(db, user, project_id)
    revision = service.revision_for(db, project, revision_id)
    version = expected_version(if_match)
    scope, body = f'run:{project_id}', {'revision_id': revision_id, 'edit_version': version}
    if saved := service.replay(db, user.id, scope, idempotency_key, body):
        return saved
    db.rollback(); enforce_limit(db, f'analysis:{user.id}', 10, 3600)
    if saved := service.replay(db, user.id, scope, idempotency_key, body):
        return saved
    run = service.start_run(db, project, revision, user.id, idempotency_key=idempotency_key, expected_version=version)
    result = service.run_summary(run)
    service.remember(db, user.id, scope, idempotency_key, body, result)
    db.commit()
    background_tasks.add_task(run_analysis_pipeline, project.id, run_id=run.id)
    return result


@router.get('/projects/{project_id}/runs')
def runs(project_id: int, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
         db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_project_access(db, user, project_id)
    query = db.query(AnalysisRun).filter_by(project_id=project_id)
    return {'items': [service.run_summary(run) for run in query.order_by(AnalysisRun.created_at.desc(), AnalysisRun.id.desc()).offset(offset).limit(limit)], 'total': query.count()}


@router.get('/runs/{run_id}')
def run_status(run_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return service.run_summary(run_access(db, user, run_id))


@router.get('/runs/{run_id}/report')
def report(run_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    run = run_access(db, user, run_id)
    if not run.report:
        raise HTTPException(409, 'This run has no published report; check its status')
    decisions = service.latest_decisions(db, run_id)
    payload = deepcopy(run.report)
    if payload.get('legacy'):
        # The original import stays immutable. Expose mapped target IDs so new
        # decisions do not accidentally address unrelated old projection rows.
        payload['findings'] = [{**row.data, 'legacy_id': row.data.get('id'), 'id': row.id} for row in db.query(RunFinding).filter_by(run_id=run.id)]
        payload['trace_links'] = [{**row.data, 'legacy_id': row.data.get('id'), 'id': row.id} for row in db.query(RunTraceLink).filter_by(run_id=run.id)]
    return {**payload, 'run': service.run_summary(run),
        'reviews': [decision_view(decision) for decision in decisions.values()]}


@router.get('/runs/{run_id}/traceability.csv')
def export_trace(run_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    import csv
    import io
    from fastapi.responses import Response
    from .traceability import safe_csv_cell
    run = run_access(db, user, run_id)
    if not run.report:
        raise HTTPException(409, 'This run has no report to export')
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(['Run ID', 'Source Type', 'Source ID', 'Target Type', 'Target ID', 'Review Status', 'Origin', 'Similarity (not probability)'])
    decisions = service.latest_decisions(db, run.id)
    for link in db.query(RunTraceLink).filter_by(run_id=run.id).order_by(RunTraceLink.id):
        decision = decisions.get(('trace', link.id))
        writer.writerow([safe_csv_cell(value) for value in [run.id, link.source_type, link.source_id, link.target_type, link.target_id,
            decision.status if decision else 'suggested', link.data.get('origin'), link.data.get('confidence')]])
    return Response(output.getvalue(), media_type='text/csv', headers={'Content-Disposition': f'attachment; filename="traceability-{run.id}.csv"', 'Cache-Control': 'private, no-store'})


@router.get('/runs/{run_id}/findings')
def findings(run_id: str, severity: str | None = None, rule_id: str | None = None,
             limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
             db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    run_access(db, user, run_id)
    query = db.query(RunFinding).filter_by(run_id=run_id)
    if severity:
        query = query.filter_by(severity=severity)
    if rule_id:
        query = query.filter_by(rule_id=rule_id)
    return {'items': [{**f.data, 'id': f.id, 'fingerprint': f.fingerprint} for f in query.order_by(RunFinding.id).offset(offset).limit(limit)], 'total': query.count()}


@router.get('/runs/{run_id}/compare/{previous_run_id}')
def compare(run_id: str, previous_run_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    right, left = run_access(db, user, run_id), run_access(db, user, previous_run_id)
    return service.compare_runs(db, left, right)


def decision_view(decision):
    return {'id': decision.id, 'run_id': decision.run_id, 'finding_id': decision.finding_id, 'trace_id': decision.trace_id,
        'actor_id': decision.actor_id, 'status': decision.status, 'origin': decision.origin,
        'reason': decision.reason, 'carried_from_id': decision.carried_from_id, 'created_at': iso_utc(decision.created_at)}


@router.post('/runs/{run_id}/decisions', status_code=201)
def decide(run_id: str, data: DecisionCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    run = run_access(db, user, run_id)
    project = require_project_access(db, user, run.project_id)
    service.require_writable(project); service.lock_project(db, project)
    model = RunFinding if data.target_type == 'finding' else RunTraceLink
    target = db.query(model).filter_by(id=data.target_id, run_id=run.id).first()
    if not target:
        raise HTTPException(404, 'Review target not found in this run')
    allowed = {'suggested', 'confirmed', 'rejected'} if data.target_type == 'trace' else {'needs_review', 'accepted', 'dismissed'}
    if data.status not in allowed:
        raise HTTPException(422, 'This decision is not supported for the selected target')
    field = 'finding_id' if data.target_type == 'finding' else 'trace_id'
    previous = db.query(ReviewDecision).filter_by(run_id=run.id, **{field: target.id}).order_by(ReviewDecision.id.desc()).first()
    if (previous.id if previous else 0) != data.expected_decision_id:
        raise HTTPException(409, 'This review changed. Refresh before saving your decision.')
    decision = ReviewDecision(run_id=run.id, **{field: target.id}, actor_id=user.id, status=data.status, reason=data.reason)
    db.add(decision); db.flush()
    if data.target_type == 'trace' and project.published_run_id == run.id:
        from ..models.traceability import TraceLink
        db.query(TraceLink).filter_by(project_id=project.id, is_stale=False,
            **{key: getattr(target, key) for key in ('source_type', 'source_id', 'target_type', 'target_id')}).update({'status': data.status})
    service.audit(db, project, user.id, 'review_decision', run_id=run.id, decision_id=decision.id)
    db.commit()
    return decision_view(decision)


@router.post('/projects/{project_id}/lifecycle')
def lifecycle(project_id: int, data: ProjectLifecycle, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = require_project_access(db, user, project_id, include_deleted=True)
    service.lock_project(db, project)
    if db.query(AnalysisRun).filter(AnalysisRun.project_id == project.id, AnalysisRun.status.in_(service.ACTIVE)).first():
        raise HTTPException(409, 'Wait for the active run before changing project state')
    if data.action == 'delete':
        if data.confirmation != project.name:
            raise HTTPException(422, 'Confirm deletion by entering the exact project name')
        project.deleted_at = project.deleted_at or utcnow()
    elif data.action == 'archive':
        if project.deleted_at:
            raise HTTPException(409, 'Restore this deleted project first')
        project.archived_at = project.archived_at or utcnow()
    else:
        if project.deleted_at and project.deleted_at < utcnow() - timedelta(days=30):
            raise HTTPException(409, 'The 30-day restoration period has expired')
        project.deleted_at, project.archived_at = None, None
    service.audit(db, project, user.id, f'project_{data.action}')
    db.commit()
    return project_view(project)
