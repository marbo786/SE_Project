import os

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content.strip() + '\n')

def delete_file(path):
    if os.path.exists(path):
        os.remove(path)

# --- 5. MORE ROUTERS ---
write_file('backend/app/routers/findings.py', """
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..core.database import get_db
from ..core.deps import get_current_user
from ..models.user import User
from ..models.finding import Finding
from ..schemas.finding import FindingOut

router = APIRouter(prefix="/findings", tags=["findings"])

@router.get("/project/{project_id}", response_model=List[FindingOut])
def get_findings(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Simple fetch, no instructor decisions anymore
    findings = db.query(Finding).filter(Finding.project_id == project_id).all()
    return findings
""")

write_file('backend/app/routers/traceability.py', """
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..core.database import get_db
from ..core.deps import get_current_user
from ..models.user import User
from ..models.traceability import TraceLink
from ..schemas.traceability import TraceLinkOut

router = APIRouter(prefix="/traceability", tags=["traceability"])

@router.get("/project/{project_id}", response_model=List[TraceLinkOut])
def get_trace_links(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    links = db.query(TraceLink).filter(TraceLink.project_id == project_id).all()
    return links
""")

write_file('backend/app/routers/dashboard.py', """
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..core.deps import get_current_user
from ..models.user import User
from ..models.project import Project

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    total_projects = db.query(Project).filter(Project.user_id == current_user.id).count()
    analyzed_projects = db.query(Project).filter(
        Project.user_id == current_user.id,
        Project.status == 'done'
    ).count()
    analyzing_projects = db.query(Project).filter(
        Project.user_id == current_user.id,
        Project.status == 'analyzing'
    ).count()

    return {
        "role": "user",
        "total_projects": total_projects,
        "analyzed_projects": analyzed_projects,
        "analyzing_projects": analyzing_projects
    }
""")
