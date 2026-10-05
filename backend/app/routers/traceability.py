from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List
import csv
import io

from ..core.database import get_db
from ..core.deps import get_current_user
from ..models.user import User
from ..models.traceability import TraceLink
from ..schemas.traceability import TraceLinkOut, TraceLinkUpdate

router = APIRouter(prefix="/traceability", tags=["traceability"])

@router.get("/project/{project_id}", response_model=List[TraceLinkOut])
def get_trace_links(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    links = db.query(TraceLink).filter(TraceLink.project_id == project_id).all()
    return links

@router.patch("/{link_id}", response_model=TraceLinkOut)
def update_trace_link(link_id: int, update_data: TraceLinkUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    link = db.query(TraceLink).filter(TraceLink.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    
    if update_data.status not in ["suggested", "confirmed", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    link.status = update_data.status
    db.commit()
    db.refresh(link)
    return link

@router.get("/project/{project_id}/export")
def export_traceability_matrix(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    links = db.query(TraceLink).filter(TraceLink.project_id == project_id).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Source Type", "Source ID", "Target Type", "Target ID", "Status"])
    
    for link in links:
        writer.writerow([link.source_type, link.source_id, link.target_type, link.target_id, link.status])
        
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=traceability_matrix_{project_id}.csv"}
    )
