// Generated from FastAPI OpenAPI by scripts/generate_api_types.py. Do not edit.

export type ArtifactSummary = {
  "id": number;
  "type": string;
  "filename": string;
  "sha256": (string | null);
  "size_bytes": (number | null);
}

export type Body_upload_srs_projects__project_id__upload_srs_post = {
  "file": string;
}

export type Body_upload_uml_projects__project_id__upload_uml_post = {
  "uml_type": string;
  "file": string;
}

export type Body_upload_v1_projects__project_id__revisions__revision_id__artifacts_post = {
  "kind": string;
  "file": string;
  "replace_artifact_id"?: (number | null);
}

export type DecisionCreate = {
  "target_type": "finding" | "trace";
  "target_id": number;
  "status": "suggested" | "confirmed" | "rejected" | "accepted" | "dismissed" | "needs_review";
  "reason"?: (string | null);
  "expected_decision_id"?: number;
}

export type DraftCreate = {
  "parent_revision_id"?: (number | null);
}

export type FindingOut = {
  "id": number;
  "rule_id": string;
  "severity": string;
  "quoted_text": (string | null);
  "explanation": string;
  "artifact_type": (string | null);
  "requirement_id": (string | null);
  "source_ref"?: (string | null);
  "source_spans"?: (Array<Record<string, unknown>> | null);
  "element_id"?: (string | null);
  "finding_type": string;
  "rewrite_suggestion": (string | null);
  "rewrite_attempts"?: (number | null);
  "rewrite_passed"?: (boolean | null);
  "created_at": string;
}

export type HTTPValidationError = {
  "detail"?: Array<ValidationError>;
}

export type ManualTrace = {
  "source_type": "requirement" | "usecase" | "sequence";
  "source_id": string;
  "target_type": "usecase" | "sequence" | "class";
  "target_id": string;
  "reason": string;
}

export type ProjectCreate = {
  "name": string;
  "description"?: (string | null);
  "analysis_profile"?: "srs_only" | "architecture";
  "analysis_mode"?: "deterministic" | "ai";
}

export type ProjectLifecycle = {
  "action": "archive" | "restore" | "delete";
  "confirmation"?: (string | null);
}

export type ProjectOut = {
  "id": number;
  "user_id": number;
  "name": string;
  "description": (string | null);
  "version": number;
  "status": string;
  "analysis_profile": string;
  "analysis_mode": string;
  "analysis_error"?: (string | null);
  "current_revision_id"?: (number | null);
  "latest_run_id"?: (string | null);
  "published_run_id"?: (string | null);
  "archived_at"?: (string | null);
  "deleted_at"?: (string | null);
  "quality_score"?: (ScoreOut | null);
  "created_at": string;
}

export type ProjectRename = {
  "name": string;
  "expected_name": string;
}

export type RecoveryRequest = {
  "email": string;
}

export type RequirementUpdate = {
  "text"?: (string | null);
  "id"?: (string | null);
  "class"?: ("functional" | "non_functional" | null);
  "subtype"?: ("performance" | "availability" | "security" | "usability" | "reliability" | "maintainability" | "portability" | "other" | null);
}

export type ResetPassword = {
  "token": string;
  "password": string;
}

export type RevisionOut = {
  "id": number;
  "project_id": number;
  "number": number;
  "parent_id": (number | null);
  "state": "draft" | "sealed";
  "edit_version": number;
  "analysis_profile": "srs_only" | "architecture";
  "analysis_mode": "deterministic" | "ai";
  "extraction_confirmed": boolean;
  "legacy_version": (number | null);
  "created_at": string;
  "sealed_at": (string | null);
  "artifacts": Array<ArtifactSummary>;
}

export type RevisionUpdate = {
  "analysis_profile"?: ("srs_only" | "architecture" | null);
  "analysis_mode"?: ("deterministic" | "ai" | null);
  "extraction_confirmed"?: (boolean | null);
}

export type RunOut = {
  "id": string;
  "project_id": number;
  "revision_id": number;
  "has_report": boolean;
  "attempt_count": number;
  "cancel_requested": boolean;
  "heartbeat_at": (string | null);
  "status": "queued" | "running" | "completed" | "partial" | "failed" | "cancelled";
  "stage": string;
  "counts": Record<string, number>;
  "versions": Record<string, string>;
  "input_hash": (string | null);
  "error_code": (string | null);
  "error_message": (string | null);
  "created_at": string;
  "started_at": (string | null);
  "finished_at": (string | null);
}

export type ScoreOut = {
  "requirements_score": (number | null);
  "uml_score": (number | null);
  "traceability_score": (number | null);
  "overall_score": (number | null);
  "details"?: (Record<string, unknown> | null);
  "computed_at": string;
}

export type SuggestionInput = {
  "action": "accepted" | "edited" | "rejected";
  "expected_decision_id"?: number;
  "draft_id"?: (number | null);
  "text"?: (string | null);
  "confirm_intent"?: boolean;
}

export type Token = {
  "access_token": string;
  "token_type"?: string;
  "user": UserOut;
}

export type TraceLinkOut = {
  "id": number;
  "source_type": string;
  "source_id": string;
  "target_type": string;
  "target_id": string;
  "status": string;
  "source_label"?: (string | null);
  "target_label"?: (string | null);
  "confidence"?: (number | null);
  "origin"?: string;
  "evidence"?: (Record<string, unknown> | null);
  "is_stale"?: boolean;
  "created_at": string;
}

export type TraceLinkUpdate = {
  "status": string;
}

export type UserCreate = {
  "email": string;
  "password": string;
  "name": string;
}

export type UserLogin = {
  "email": string;
  "password": string;
}

export type UserOut = {
  "id": number;
  "name": string;
  "email": string;
  "email_verified"?: boolean;
}

export type ValidationError = {
  "loc": Array<(string | number)>;
  "msg": string;
  "type": string;
  "input"?: unknown;
  "ctx"?: Record<string, unknown>;
}

export type VerifyEmail = {
  "token": string;
}
