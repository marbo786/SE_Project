from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..core.database import get_db
from ..core.deps import require_instructor
from ..models.user import User
from ..models.submission import Submission
from ..models.finding import Finding
from ..models.score import QualityScore
from ..models.llm_log import LLMLog

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/instructor")
def instructor_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_instructor)
):
    """
    Aggregate dashboard data for instructor:
    - Submission count and status breakdown
    - Top findings by rule
    - Score distribution
    - LLM usage stats
    """
    # Submissions for instructor's assignments
    from ..models.assignment import Assignment
    assignment_ids = [
        a.id for a in db.query(Assignment).filter(Assignment.instructor_id == current_user.id).all()
    ]
    submissions = db.query(Submission).filter(Submission.assignment_id.in_(assignment_ids)).all()
    submission_ids = [s.id for s in submissions]

    status_counts = {}
    for s in submissions:
        status_counts[s.status] = status_counts.get(s.status, 0) + 1

    # Findings summary
    findings = db.query(Finding).filter(Finding.submission_id.in_(submission_ids)).all()
    severity_counts = {"critical": 0, "major": 0, "minor": 0}
    rule_counts = {}
    for f in findings:
        severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1
        rule_counts[f.rule_id] = rule_counts.get(f.rule_id, 0) + 1

    top_rules = sorted(rule_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    # Score distribution
    scores = db.query(QualityScore).filter(QualityScore.submission_id.in_(submission_ids)).all()
    avg_overall = round(sum(s.overall_score for s in scores) / len(scores), 2) if scores else 0.0
    avg_req = round(sum(s.requirements_score for s in scores) / len(scores), 2) if scores else 0.0
    avg_uml = round(sum(s.uml_score for s in scores) / len(scores), 2) if scores else 0.0
    avg_trace = round(sum(s.traceability_score for s in scores) / len(scores), 2) if scores else 0.0

    # LLM usage
    llm_logs = db.query(LLMLog).filter(LLMLog.submission_id.in_(submission_ids)).all()
    total_prompt_tokens = sum(l.prompt_tokens for l in llm_logs)
    total_completion_tokens = sum(l.completion_tokens for l in llm_logs)
    cache_hits = sum(1 for l in llm_logs if l.cache_hit == "true")

    return {
        "instructor_id": current_user.id,
        "total_assignments": len(assignment_ids),
        "total_submissions": len(submissions),
        "submission_status_breakdown": status_counts,
        "findings_by_severity": severity_counts,
        "top_rules": [{"rule_id": r, "count": c} for r, c in top_rules],
        "scores": {
            "avg_overall": avg_overall,
            "avg_requirements": avg_req,
            "avg_uml": avg_uml,
            "avg_traceability": avg_trace
        },
        "llm_usage": {
            "total_calls": len(llm_logs),
            "cache_hits": cache_hits,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens
        }
    }
