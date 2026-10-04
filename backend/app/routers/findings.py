from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..core.database import get_db
from ..core.deps import get_current_user, require_instructor
from ..models.user import User
from ..models.submission import Submission
from ..models.finding import Finding, InstructorDecision
from ..schemas.finding import FindingOut, DecisionCreate

router = APIRouter(prefix="/findings", tags=["findings"])


@router.get("/submission/{submission_id}", response_model=List[FindingOut])
def list_findings(
    submission_id: int,
    severity: str = None,
    finding_type: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List findings for a submission with optional filters."""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if current_user.role == "student" and submission.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    query = db.query(Finding).filter(Finding.submission_id == submission_id)
    if severity:
        query = query.filter(Finding.severity == severity)
    if finding_type:
        query = query.filter(Finding.finding_type == finding_type)

    findings = query.all()
    result = []
    for f in findings:
        fd = FindingOut.model_validate(f)
        if f.instructor_decision:
            fd.instructor_decision = {
                "status": f.instructor_decision.status,
                "comment": f.instructor_decision.comment,
                "decided_at": f.instructor_decision.decided_at.isoformat()
            }
        result.append(fd)
    return result


@router.post("/{finding_id}/decision", status_code=status.HTTP_201_CREATED)
def make_decision(
    finding_id: int,
    decision_data: DecisionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor)
):
    """Accept or reject a finding (instructor only)."""
    if decision_data.status not in ("accepted", "rejected"):
        raise HTTPException(status_code=400, detail="Status must be 'accepted' or 'rejected'")

    finding = db.query(Finding).filter(Finding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    # Upsert decision
    existing = db.query(InstructorDecision).filter(InstructorDecision.finding_id == finding_id).first()
    if existing:
        existing.status = decision_data.status
        existing.comment = decision_data.comment
        existing.instructor_id = current_user.id
    else:
        decision = InstructorDecision(
            finding_id=finding_id,
            instructor_id=current_user.id,
            status=decision_data.status,
            comment=decision_data.comment
        )
        db.add(decision)
    db.commit()
    return {"message": "Decision recorded", "finding_id": finding_id, "status": decision_data.status}
