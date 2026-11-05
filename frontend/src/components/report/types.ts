/* ---------- Data Contracts ---------- */
export interface Project {
  id: number
  archived_at?: string | null
  name: string
  description?: string
  version: number
  status: string
  created_at: string
  analysis_profile: string
  analysis_mode: string
  analysis_error?: string
  current_revision_id: number
  published_run_id?: string
  latest_run_id?: string
  quality_score?: {
    overall_score: number | null
    computed_at: string
    details?: {
      ai_coverage?: Record<string, { total: number; reviewed: number; complete: boolean; note?: string }>
      rubric_version: string
      profile: string
      note: string
      categories: Record<string, { applicable: boolean; percentage: number | null; weight: number; eligible_count: number; contribution: number | null }>
    }
  }
}

export interface Finding {
  id: number
  element_id?: string
  rule_id: string
  severity: string
  explanation: string
  quoted_text?: string
  artifact_type?: string
  requirement_id?: string
  finding_type?: string
  source_ref?: string
  source_spans?: { artifact_id?: number }[]
  evidence?: string | string[]
  related_requirement?: { id?: string; text: string; source_ref?: string }
  rewrite_semantic_review?: { intent_preserved: boolean; explanation: string; original_quote: string; proposal_quote: string }
  rewrite_suggestion?: string
  rewrite_checks?: Record<string, boolean>
  rewrite_review_status?: string
  rewrite_passed?: boolean
  rewrite_error?: string
  rewrite_attempts?: number
}

export interface TraceLink {
  id: number
  source_id: string
  source_type: string
  target_id: string
  target_type: string
  source_label?: string
  target_label?: string
  evidence?: Record<string, unknown>
  origin?: string
  confidence?: number
  is_stale?: boolean
  status: string
}

export interface CompareData {
  resolved_findings?: Finding[]
  new_findings?: Finding[]
  persistent_findings?: Finding[]
  scores_comparable?: boolean
  comparability_note?: string
  requirements?: { added: unknown[]; deleted: unknown[]; changed: unknown[] }
}


export interface SuggestionDecision { id: number; finding_id: number; status: string; draft_id?: number }
