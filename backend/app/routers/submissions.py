import json
import os
import uuid
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional

from ..core.database import get_db
from ..core.deps import get_current_user, require_student, require_instructor
from ..models.user import User
from ..models.submission import Submission
from ..models.artifact import Artifact
from ..models.assignment import Assignment
from ..models.score import QualityScore
from ..schemas.submission import SubmissionOut
from ..pipeline.analyzer import run_analysis_pipeline

router = APIRouter(prefix="/submissions", tags=["submissions"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "../../../uploads")


def _ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)


async def _save_file(upload_file: UploadFile, subdir: str) -> tuple[str, str]:
    """Save an uploaded file; return (file_path, original_filename)."""
    _ensure_upload_dir()
    target_dir = os.path.join(UPLOAD_DIR, subdir)
    os.makedirs(target_dir, exist_ok=True)
    ext = os.path.splitext(upload_file.filename)[1]
    unique_name = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(target_dir, unique_name)
    content = await upload_file.read()
    with open(file_path, 'wb') as f:
        f.write(content)
    return file_path, upload_file.filename


def _detect_format(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext == '.pdf':
        return 'pdf'
    if ext in ('.docx', '.doc'):
        return 'docx'
    return 'plantuml'


@router.post("/", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED)
async def create_submission(
    background_tasks: BackgroundTasks,
    assignment_id: int = Form(...),
    team_name: str = Form(...),
    member_names: str = Form(...),  # JSON-encoded list
    srs_file: Optional[UploadFile] = File(None),
    usecase_file: Optional[UploadFile] = File(None),
    class_file: Optional[UploadFile] = File(None),
    sequence_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student)
):
    """
    Create a new submission with optional file uploads.
    Triggers analysis pipeline as a background task.
    """
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # Count existing submissions by this student for versioning
    existing_count = db.query(Submission).filter(
        Submission.assignment_id == assignment_id,
        Submission.student_id == current_user.id
    ).count()

    submission = Submission(
        assignment_id=assignment_id,
        student_id=current_user.id,
        team_name=team_name,
        member_names=member_names,
        version=existing_count + 1,
        status="pending"
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    # Save uploaded files and create artifact records
    file_map = [
        (srs_file, 'srs'),
        (usecase_file, 'uml_usecase'),
        (class_file, 'uml_class'),
        (sequence_file, 'uml_sequence'),
    ]
    for upload, artifact_type in file_map:
        if upload and upload.filename:
            file_path, orig_name = await _save_file(upload, str(submission.id))
            artifact = Artifact(
                submission_id=submission.id,
                artifact_type=artifact_type,
                file_format=_detect_format(orig_name),
                file_path=file_path,
                original_filename=orig_name
            )
            db.add(artifact)
    db.commit()

    # Kick off background analysis
    background_tasks.add_task(run_analysis_pipeline, submission.id, db)

    return submission


@router.get("/", response_model=List[SubmissionOut])
def list_submissions(
    assignment_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List submissions. Students see their own; instructors see all for their assignments."""
    query = db.query(Submission)
    if assignment_id:
        query = query.filter(Submission.assignment_id == assignment_id)
    if current_user.role == "student":
        query = query.filter(Submission.student_id == current_user.id)
    return query.order_by(Submission.created_at.desc()).all()


@router.get("/{submission_id}", response_model=SubmissionOut)
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a submission by ID."""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    # Authorization: student can only see own submissions
    if current_user.role == "student" and submission.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return submission


@router.get("/{submission_id}/score")
def get_submission_score(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get quality score for a submission."""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    if current_user.role == "student" and submission.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    score = db.query(QualityScore).filter(QualityScore.submission_id == submission_id).first()
    if not score:
        return {"message": "Score not yet computed", "status": submission.status}
    return {
        "submission_id": submission_id,
        "requirements_score": score.requirements_score,
        "uml_score": score.uml_score,
        "traceability_score": score.traceability_score,
        "overall_score": score.overall_score,
        "computed_at": score.computed_at
    }


@router.post("/{submission_id}/reanalyze", status_code=status.HTTP_202_ACCEPTED)
def reanalyze_submission(
    submission_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor)
):
    """Re-trigger analysis for a submission (instructor only)."""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    submission.status = "pending"
    db.commit()
    background_tasks.add_task(run_analysis_pipeline, submission_id, db)
    return {"message": "Re-analysis started", "submission_id": submission_id}
