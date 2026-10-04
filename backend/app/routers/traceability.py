from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..core.database import get_db
from ..core.deps import get_current_user, require_instructor
from ..models.user import User
from ..models.submission import Submission
from ..models.traceability import TraceLink
from ..schemas.traceability import TraceLinkOut, TraceLinkUpdate, TraceLinkCreate

router = APIRouter(prefix="/traceability", tags=["traceability"])


@router.get("/submission/{submission_id}", response_model=List[TraceLinkOut])
def list_trace_links(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all trace links for a submission."""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if current_user.role == "student" and submission.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return db.query(TraceLink).filter(TraceLink.submission_id == submission_id).all()


@router.post("/submission/{submission_id}", response_model=TraceLinkOut, status_code=status.HTTP_201_CREATED)
def create_trace_link(
    submission_id: int,
    link_data: TraceLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor)
):
    """Manually add a trace link (instructor only)."""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    link = TraceLink(
        submission_id=submission_id,
        source_type=link_data.source_type,
        source_id=link_data.source_id,
        target_type=link_data.target_type,
        target_id=link_data.target_id,
        status='confirmed'
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


@router.patch("/{link_id}", response_model=TraceLinkOut)
def update_trace_link(
    link_id: int,
    update_data: TraceLinkUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor)
):
    """Update the status of a trace link (instructor confirms or rejects)."""
    if update_data.status not in ("confirmed", "rejected", "suggested"):
        raise HTTPException(status_code=400, detail="Status must be 'confirmed', 'rejected', or 'suggested'")
    link = db.query(TraceLink).filter(TraceLink.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Trace link not found")
    link.status = update_data.status
    db.commit()
    db.refresh(link)
    return link


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trace_link(
    link_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor)
):
    """Delete a trace link (instructor only)."""
    link = db.query(TraceLink).filter(TraceLink.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Trace link not found")
    db.delete(link)
    db.commit()
