import os
import uuid
import json
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from ..core.database import get_db
from ..core.config import get_settings
from ..core.deps import get_current_user, require_project_access
from ..core.uploads import accept_upload, store_artifact
from ..core.limits import enforce_limit
from ..models.user import User
from ..models.project import Project
from ..models.artifact import Artifact
from ..models.score import QualityScore
from ..models.finding import Finding
from ..schemas.project import ProjectOut, ProjectCreate
from ..pipeline.analyzer import run_analysis_pipeline

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/", response_model=List[ProjectOut])
def list_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Project).filter(Project.user_id == current_user.id).order_by(Project.created_at.desc()).all()

@router.post("/", response_model=ProjectOut)
def create_project(project_in: ProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    enforce_limit(db, f"create:{current_user.id}", 20, 3600)
    if db.query(Project).filter_by(user_id=current_user.id).count() >= get_settings().MAX_PROJECTS_PER_USER:
        raise HTTPException(409, "Project quota reached")
    # Legacy version grouping is replaced by explicit revision identity in M3.
    existing = db.query(Project).filter(Project.name == project_in.name, Project.user_id == current_user.id).order_by(Project.version.desc()).first()
    version = (existing.version + 1) if existing else 1

    project = Project(
        user_id=current_user.id,
        name=project_in.name,
        description=project_in.description,
        version=version,
        analysis_profile=project_in.analysis_profile,
        analysis_mode=project_in.analysis_mode,
        status="pending"
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

def require_analysis_inputs(db, project):
    available = {artifact.artifact_type for artifact in db.query(Artifact).filter_by(project_id=project.id)}
    required = {"srs", "uml_usecase", "uml_class", "uml_sequence"} if project.analysis_profile == "architecture" else {"srs"}
    if missing := required - available:
        raise HTTPException(409, "Upload the required inputs for this profile: " + ", ".join(sorted(missing)))
    if project.analysis_mode == "ai" and get_settings().LLM_PROVIDER == "mock":
        raise HTTPException(409, "AI analysis needs a configured provider. Use deterministic analysis for offline checks.")


def editable_project(db, current_user, project_id):
    project = require_project_access(db, current_user, project_id)
    if project.status != "pending":
        raise HTTPException(409, "Uploads are locked after analysis starts. Create a new revision to change the inputs.")
    enforce_limit(db, f"upload:{current_user.id}", 30, 3600)
    return project


@router.post("/{project_id}/upload-srs")
async def upload_srs(project_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = editable_project(db, current_user, project_id)
    content, format, filename = await accept_upload(file)
    store_artifact(db, project, "srs", content, format, filename)
    return {"message": "SRS uploaded"}


@router.post("/{project_id}/upload-uml")
async def upload_uml(project_id: int, uml_type: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = editable_project(db, current_user, project_id)
    if uml_type not in {"usecase", "class", "sequence"}:
        raise HTTPException(400, "Invalid UML type")
    content, format, filename = await accept_upload(file, uml=True)
    store_artifact(db, project, f"uml_{uml_type}", content, format, filename)
    return {"message": f"{uml_type} UML uploaded"}


@router.post("/{project_id}/analyze")
def analyze_project(project_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status in ["analyzing", "done"]:
        raise HTTPException(status_code=400, detail="Project analysis already started or finished")

    require_analysis_inputs(db, project)
    enforce_limit(db, f"analysis:{current_user.id}", 10, 3600)
    claimed = db.query(Project).filter(Project.id == project.id, Project.status != "analyzing").update({"status": "analyzing"})
    if not claimed:
        db.rollback()
        raise HTTPException(409, "Analysis is already running")
    db.commit()

    background_tasks.add_task(run_analysis_pipeline, project.id)
    return {"message": "Analysis started"}

@router.post("/{project_id}/reanalyze")
def reanalyze_project(project_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    if project.status == "analyzing":
        raise HTTPException(status_code=400, detail="Project analysis is currently running")

    require_analysis_inputs(db, project)
    enforce_limit(db, f"analysis:{current_user.id}", 10, 3600)
    claimed = db.query(Project).filter(Project.id == project.id, Project.status != "analyzing").update({"status": "analyzing"})
    if not claimed:
        db.rollback()
        raise HTTPException(409, "Analysis is already running")
    db.commit()

    background_tasks.add_task(run_analysis_pipeline, project.id)
    return {"message": "Re-analysis started"}


@router.get("/{project_id}/extraction")
def get_extraction(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    require_project_access(db, current_user, project_id)
    return [{"artifact_id": artifact.id, "type": artifact.artifact_type, "filename": artifact.original_filename,
        "extraction": json.loads(artifact.extracted_content) if artifact.extracted_content else None}
        for artifact in db.query(Artifact).filter_by(project_id=project_id)]

@router.get("/{project_id}/compare")
def compare_versions(project_id: int, with_version: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    current = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not current:
        raise HTTPException(status_code=404, detail="Project not found")
        
    previous = db.query(Project).filter(
        Project.name == current.name,
        Project.user_id == current.user_id,
        Project.version == with_version
    ).first()
    
    if not previous:
        raise HTTPException(status_code=404, detail="Previous version not found")
        
    curr_findings = db.query(Finding).filter(Finding.project_id == current.id).all()
    prev_findings = db.query(Finding).filter(Finding.project_id == previous.id).all()
    
    def _make_key(f):
        if f.requirement_id:
            return (f.rule_id, f.artifact_type, f.requirement_id, None)
        qt = f.quoted_text.lower().strip() if f.quoted_text else None
        return (f.rule_id, f.artifact_type, None, qt)
        
    curr_keys = { _make_key(f): f for f in curr_findings }
    prev_keys = { _make_key(f): f for f in prev_findings }
    
    resolved = []
    new_findings = []
    persistent = []
    
    for k, f in prev_keys.items():
        if k not in curr_keys:
            resolved.append(f)
        else:
            persistent.append(f)
            
    for k, f in curr_keys.items():
        if k not in prev_keys:
            new_findings.append(f)
            
    def _serialize(f):
        return {
            "id": f.id,
            "rule_id": f.rule_id,
            "severity": f.severity,
            "explanation": f.explanation,
            "requirement_id": f.requirement_id
        }
        
    return {
        "current_version": current.version,
        "previous_version": previous.version,
        "resolved_findings": [_serialize(f) for f in resolved],
        "new_findings": [_serialize(f) for f in new_findings],
        "persistent_findings": [_serialize(f) for f in persistent]
    }
