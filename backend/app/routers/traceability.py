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
