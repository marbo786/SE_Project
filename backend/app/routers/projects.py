"""Temporary adapters for the original browser routes; new work uses /v1."""
import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Header
from sqlalchemy.orm import Session
from typing import List
from ..core.database import get_db
from ..core.deps import get_current_user, require_project_access
from ..core.uploads import accept_upload, store_artifact
from ..core.limits import enforce_limit
from ..models.user import User
from ..models.project import Project
from ..models.artifact import Artifact
from ..models.history import ProjectRevision, AnalysisRun
from ..schemas.project import ProjectOut, ProjectCreate
from ..pipeline.analyzer import run_analysis_pipeline
from ..services import history as service

router = APIRouter(prefix='/projects', tags=['projects (compatibility)'])


@router.get('/', response_model=List[ProjectOut])
def list_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Project).filter(Project.user_id == current_user.id, Project.deleted_at.is_(None), Project.archived_at.is_(None)).order_by(Project.created_at.desc()).all()


@router.post('/', response_model=ProjectOut)
def create_project(project_in: ProjectCreate, idempotency_key: str | None = Header(None), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from .history import create_project as create
    return create(project_in, idempotency_key, db, current_user)


@router.get('/{project_id}', response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return require_project_access(db, current_user, project_id)


def editable_project(db, user, project_id):
    project = require_project_access(db, user, project_id)
    service.require_writable(project)
    revision = service.ensure_revision(db, project)
    if revision.state != 'draft' or project.status == 'analyzing':
        raise HTTPException(409, 'Uploads are locked after analysis starts. Create a new revision to change the inputs.')
    enforce_limit(db, f'upload:{user.id}', 30, 3600)
    return project


@router.post('/{project_id}/upload-srs')
async def upload_srs(project_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = editable_project(db, current_user, project_id)
    content, format, filename = await accept_upload(file)
    artifact = store_artifact(db, project, 'srs', content, format, filename)
    return {'message': 'SRS uploaded', 'artifact_id': artifact.id}


@router.post('/{project_id}/upload-uml')
async def upload_uml(project_id: int, uml_type: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = editable_project(db, current_user, project_id)
    if uml_type not in {'usecase', 'class', 'sequence'}:
        raise HTTPException(400, 'Invalid UML type')
    content, format, filename = await accept_upload(file, uml=True)
    artifact = store_artifact(db, project, f'uml_{uml_type}', content, format, filename)
    return {'message': f'{uml_type} UML uploaded', 'artifact_id': artifact.id}


def queue_run(db, user, project_id, background_tasks, idempotency_key, *, repeat):
    project = require_project_access(db, user, project_id)
    scope, body = f'legacy_run:{project_id}', {'repeat': repeat}
    if saved := service.replay(db, user.id, scope, idempotency_key, body):
        return saved
    if not repeat and project.status in {'analyzing', 'done'}:
        raise HTTPException(400, 'Project analysis already started or finished')
    db.rollback(); enforce_limit(db, f'analysis:{user.id}', 10, 3600)
    if saved := service.replay(db, user.id, scope, idempotency_key, body):
        return saved
    revision = service.ensure_revision(db, project)
    run = service.start_run(db, project, revision, user.id, idempotency_key=idempotency_key)
    result = {'message': 'Analysis started', 'run_id': run.id}
    service.remember(db, user.id, scope, idempotency_key, body, result)
    db.commit()
    return result


@router.post('/{project_id}/analyze')
def analyze_project(project_id: int, background_tasks: BackgroundTasks, idempotency_key: str | None = Header(None), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return queue_run(db, current_user, project_id, background_tasks, idempotency_key, repeat=False)


@router.post('/{project_id}/reanalyze')
def reanalyze_project(project_id: int, background_tasks: BackgroundTasks, idempotency_key: str | None = Header(None), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return queue_run(db, current_user, project_id, background_tasks, idempotency_key, repeat=True)


@router.get('/{project_id}/extraction')
def get_extraction(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = require_project_access(db, current_user, project_id)
    revision_id = project.current_revision_id
    if project.published_run_id:
        revision_id = db.get(AnalysisRun, project.published_run_id).revision_id
    return [{'artifact_id': a.id, 'type': a.artifact_type, 'filename': a.original_filename,
        'extraction': json.loads(a.extracted_content) if a.extracted_content else None}
        for a in db.query(Artifact).filter_by(project_id=project_id, revision_id=revision_id)]


@router.get('/{project_id}/compare')
def compare_versions(project_id: int, with_version: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = require_project_access(db, current_user, project_id)
    previous = db.query(ProjectRevision).filter_by(project_id=project.id, number=with_version).first()
    previous_run = db.query(AnalysisRun).filter(AnalysisRun.revision_id == previous.id,
        AnalysisRun.status.in_(['completed', 'partial'])).order_by(AnalysisRun.created_at.desc()).first() if previous else None
    current_run = db.get(AnalysisRun, project.published_run_id) if project.published_run_id else None
    if not current_run or not previous_run:
        raise HTTPException(404, 'Previous report not found in this project')
    return {'current_version': db.get(ProjectRevision, current_run.revision_id).number,
        'previous_version': previous.number, **service.compare_runs(db, previous_run, current_run)}
