import os

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + '\n')

def delete_file(path):
    if os.path.exists(path):
        os.remove(path)

# Delete assignments router
delete_file('backend/app/routers/assignments.py')

# Delete old submissions router
delete_file('backend/app/routers/submissions.py')

# Write projects router
write_file('backend/app/routers/projects.py', """
import os
import uuid
import json
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from ..core.database import get_db
from ..core.deps import get_current_user
from ..models.user import User
from ..models.project import Project
from ..models.artifact import Artifact
from ..models.score import QualityScore
from ..models.finding import Finding
from ..schemas.project import ProjectOut, ProjectCreate
from ..pipeline.analyzer import run_analysis_pipeline

router = APIRouter(prefix="/projects", tags=["projects"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "../../../uploads")

@router.get("/", response_model=List[ProjectOut])
def list_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Project).filter(Project.user_id == current_user.id).order_by(Project.created_at.desc()).all()

@router.post("/", response_model=ProjectOut)
def create_project(project_in: ProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Check if a project with this name already exists for this user to increment version
    existing = db.query(Project).filter(Project.name == project_in.name, Project.user_id == current_user.id).order_by(Project.version.desc()).first()
    version = (existing.version + 1) if existing else 1

    project = Project(
        user_id=current_user.id,
        name=project_in.name,
        description=project_in.description,
        version=version,
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

@router.post("/{project_id}/upload-srs")
async def upload_srs(project_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_ext = file.filename.split('.')[-1]
    safe_name = f"{uuid.uuid4()}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    artifact = Artifact(
        project_id=project.id,
        artifact_type="srs",
        file_format=file_ext.lower(),
        file_path=file_path,
        original_filename=file.filename
    )
    db.add(artifact)
    db.commit()
    return {"message": "SRS uploaded"}

@router.post("/{project_id}/upload-uml")
async def upload_uml(project_id: int, uml_type: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if uml_type not in ["usecase", "class", "sequence"]:
        raise HTTPException(status_code=400, detail="Invalid UML type")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_ext = file.filename.split('.')[-1]
    safe_name = f"{uuid.uuid4()}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    artifact = Artifact(
        project_id=project.id,
        artifact_type=f"uml_{uml_type}",
        file_format=file_ext.lower(),
        file_path=file_path,
        original_filename=file.filename
    )
    db.add(artifact)
    db.commit()
    return {"message": f"{uml_type} UML uploaded"}

@router.post("/{project_id}/analyze")
def analyze_project(project_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status in ["analyzing", "done"]:
        raise HTTPException(status_code=400, detail="Project analysis already started or finished")

    project.status = "analyzing"
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

    project.status = "analyzing"
    db.commit()

    background_tasks.add_task(run_analysis_pipeline, project.id)
    return {"message": "Re-analysis started"}

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
        return (f.rule_id, f.artifact_type, f.requirement_id, f.quoted_text)
        
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
""")
