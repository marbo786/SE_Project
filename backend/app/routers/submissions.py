import json
import os
import uuid
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


async def _save_file(upload_file: UploadFile, subdir: str) -> tuple:
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


from ..schemas.submission import SubmissionCreate, SubmissionOut

@router.post("", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_submission(
    data: SubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_student)
):
    """
    Create a new submission.
    Files must be uploaded separately via /upload-srs and /upload-uml endpoints.
    """
    assignment = db.query(Assignment).filter(Assignment.id == data.assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    existing_count = db.query(Submission).filter(
        Submission.assignment_id == data.assignment_id,
        Submission.student_id == current_user.id
    ).count()

    submission = Submission(
        assignment_id=data.assignment_id,
        student_id=current_user.id,
        team_name=data.team_name,
        member_names=json.dumps(data.member_names),
        version=existing_count + 1,
        status="pending"
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission




@router.post("/{submission_id}/upload-srs")
async def upload_srs(
    submission_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload an SRS document (DOCX or PDF) for an existing submission."""
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    if current_user.role == "student" and sub.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    ext = os.path.splitext(file.filename)[-1].lower()
    if ext not in {".docx", ".pdf"}:
        raise HTTPException(status_code=400, detail="Unsupported file type. Supported: .docx, .pdf")

    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 20 MB.")

    file_path, orig_name = await _save_file(file, str(submission_id))
    # Actually re-read since we already consumed the file
    save_path = os.path.join(UPLOAD_DIR, str(submission_id))
    os.makedirs(save_path, exist_ok=True)
    unique = f"{uuid.uuid4()}{ext}"
    full_path = os.path.join(save_path, unique)
    with open(full_path, 'wb') as f:
        f.write(content)

    # Remove old SRS artifact if exists
    old = db.query(Artifact).filter(
        Artifact.submission_id == submission_id,
        Artifact.artifact_type == "srs"
    ).first()
    if old:
        db.delete(old)

    artifact = Artifact(
        submission_id=submission_id,
        artifact_type="srs",
        file_format=ext.lstrip("."),
        file_path=full_path,
        original_filename=file.filename
    )
    db.add(artifact)
    db.commit()
    return {"message": "SRS uploaded", "artifact_id": artifact.id}


@router.post("/{submission_id}/upload-uml")
async def upload_uml(
    submission_id: int,
    file: UploadFile = File(...),
    diagram_type: str = Form("usecase"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a PlantUML diagram for an existing submission."""
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    if current_user.role == "student" and sub.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if diagram_type not in ("usecase", "class", "sequence"):
        raise HTTPException(status_code=400, detail="diagram_type must be: usecase, class, or sequence")

    content = await file.read()
    save_path = os.path.join(UPLOAD_DIR, str(submission_id))
    os.makedirs(save_path, exist_ok=True)
    ext = os.path.splitext(file.filename)[-1].lower()
    unique = f"{uuid.uuid4()}{ext}"
    full_path = os.path.join(save_path, unique)
    with open(full_path, 'wb') as f:
        f.write(content)

    artifact = Artifact(
        submission_id=submission_id,
        artifact_type=f"uml_{diagram_type}",
        file_format="plantuml",
        file_path=full_path,
        original_filename=file.filename
    )
    db.add(artifact)
    db.commit()
    return {"message": "UML diagram uploaded", "artifact_id": artifact.id}


@router.post("/{submission_id}/analyze")
def analyze_submission(
    submission_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Trigger the analysis pipeline for a submission."""
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    if current_user.role == "student" and sub.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    has_srs = db.query(Artifact).filter(
        Artifact.submission_id == submission_id,
        Artifact.artifact_type == "srs"
    ).first()
    if not has_srs:
        raise HTTPException(status_code=400, detail="Upload an SRS file before triggering analysis")
        
    if sub.status in ("analyzing", "done"):
        raise HTTPException(status_code=400, detail=f"Submission is already {sub.status}")

    sub.status = "analyzing"
    db.commit()

    background_tasks.add_task(run_analysis_pipeline, submission_id)
    return {"message": "Analysis started", "submission_id": submission_id}


@router.get("", response_model=List[SubmissionOut])
@router.get("/", response_model=List[SubmissionOut], include_in_schema=False)
def list_submissions(
    assignment_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List submissions. Students see their own; instructors see all."""
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
    if submission.status == "analyzing":
        raise HTTPException(status_code=400, detail="Submission is already analyzing")
    submission.status = "pending"
    db.commit()
    background_tasks.add_task(run_analysis_pipeline, submission_id)
    return {"message": "Re-analysis started", "submission_id": submission_id}
