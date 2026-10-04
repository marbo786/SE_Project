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
