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
