import { TextDiff } from './RevisionDiff'
import { useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { historyApi, apiError, RunSummary } from '@/lib/api'
import { cn, severityColor, severityBorderColor } from '@/lib/utils'
import { Check, Copy, ChevronDown, ChevronRight } from 'lucide-react'
import type { Finding, SuggestionDecision } from './types'
function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      const ta = document.createElement('textarea')
      ta.value = text
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <button
      onClick={handleCopy}
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-border bg-secondary text-xs font-mono text-muted-foreground hover:text-foreground hover:border-primary/60 transition-none"
    >
      {copied ? (
        <>
          <Check className="h-3 w-3 text-success" />
          <span className="text-success">COPIED</span>
        </>
      ) : (
        <>
          <Copy className="h-3 w-3" />
          <span>COPY</span>
        </>
      )}
    </button>
  )
}



export function SuggestionReview({ finding, projectId, run, decision, saved }: { finding: Finding; projectId: number; run: RunSummary; decision?: SuggestionDecision; saved: () => Promise<unknown> }) {
  const [text, setText] = useState(finding.rewrite_suggestion || '')
  const [confirmed, setConfirmed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const pending = useRef<{ signature: string; send: () => Promise<unknown> } | null>(null)
  async function submit(reject: boolean) {
    setBusy(true); setError('')
    const action = reject ? 'rejected' : text === finding.rewrite_suggestion ? 'accepted' : 'edited'
    const signature = JSON.stringify([action, text, confirmed, decision?.id])
    try {
      if (pending.current?.signature !== signature) {
        const draft = reject ? null : (await historyApi.draft(projectId, run.revision_id)).data
        const data = { action, expected_decision_id: decision?.id || 0,
          ...(draft ? { draft_id: draft.id, text, confirm_intent: confirmed } : {}) }
        const key = crypto.randomUUID()
        pending.current = { signature, send: () => historyApi.suggestion(run.id, finding.id, data, key, draft?.edit_version) }
      }
      await pending.current!.send()
      pending.current = null
      await saved()
    } catch (error) {
      setError(apiError(error, 'The decision could not be saved. Retry or refresh to check its status.'))
    } finally { setBusy(false) }
  }
  return <section aria-label="Review rewrite suggestion" className="mt-3 space-y-2 print:hidden">
    {decision && <p role="status">Suggestion {decision.status}. {decision.draft_id && <Link className="underline" to={`/projects/${projectId}/revisions/${decision.draft_id}`}>Open draft and analyze</Link>}</p>}
    <TextDiff before={finding.quoted_text || ''} after={text} />
    {(!decision || decision.status === 'rejected') && <>
      <label className="block">Proposed requirement<textarea aria-label="Proposed requirement" maxLength={12000} rows={4} value={text} disabled={busy} onChange={event => setText(event.target.value)} className="block w-full bg-background border border-border rounded p-2 mt-1" /></label>
      <label className="flex gap-2 items-start"><input type="checkbox" checked={confirmed} disabled={busy} onChange={event => setConfirmed(event.target.checked)} />I reviewed the intent, thresholds, conditions and exceptions. Apply only to a draft.</label>
      <div className="flex flex-wrap gap-2"><Button disabled={busy || !confirmed || !text.trim()} onClick={() => submit(false)}>Apply to draft</Button><Button variant="outline" disabled={busy} onClick={() => submit(true)}>Reject suggestion</Button></div>
    </>}
    {error && <p role="alert">{error}</p>}
  </section>
}

export function FindingItem({ finding, review }: { finding: Finding; review?: React.ReactNode }) {
  const [expanded, setExpanded] = useState(true)

  return (
    <div
      className={cn(
        "rounded border border-border bg-card overflow-hidden border-l-[3px]",
        severityBorderColor(finding.severity)
      )}
    >
      {/* Header bar */}
      <div
        className="p-3 flex items-start gap-2.5 cursor-pointer hover:bg-accent/40 select-none transition-none"
      >
        <button
          type="button"
          className="mt-0.5 text-muted-foreground hover:text-foreground"
          onClick={() => setExpanded(!expanded)}
          aria-expanded={expanded}
          aria-label={expanded ? "Collapse finding" : "Expand finding"}
        >
          {expanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        </button>

        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-1.5 mb-1">
            <span
              className={cn(
                "inline-flex items-center px-1.5 py-0.2 rounded-sm text-xs font-mono uppercase font-semibold border",
                severityColor(finding.severity)
              )}
            >
              {finding.severity}
            </span>

            <span className="text-xs font-mono text-primary bg-secondary border border-border px-1.5 py-0.2 rounded-sm">
              {finding.rule_id}
            </span>

            {finding.requirement_id && (
              <span className="text-xs font-mono text-muted-foreground bg-secondary border border-border px-1.5 py-0.2 rounded-sm">
                {finding.requirement_id}
              </span>
            )}

            {finding.artifact_type && (
              <span className="text-xs font-mono uppercase text-muted-foreground border border-border px-1 py-0.2 rounded-sm">
                {finding.artifact_type}
              </span>
            )}
          </div>

          <p className="text-xs text-foreground leading-relaxed">
            {finding.explanation}
          </p>
        </div>
      </div>

      {/* Expanded Technical Inspection Details */}
      {expanded && (
        <div className="border-t border-border bg-secondary p-3 space-y-3 text-xs">
          {finding.source_ref && <p className="text-sm text-muted-foreground">Source: {finding.source_ref}{finding.source_spans?.[0]?.artifact_id ? ` · Artifact ${finding.source_spans[0].artifact_id}` : ''}</p>}
          {/* Problematic Quoted Text */}
          {finding.quoted_text && (
            <div>
              <p className="text-xs font-mono uppercase tracking-wider text-muted-foreground mb-1">
                Problematic Excerpt
              </p>
              <div className="border-l-2 border-danger/60 pl-2.5 py-1.5 bg-background text-foreground/90 font-mono text-xs rounded-r">
                "{finding.quoted_text}"
              </div>
            </div>
          )}

          {finding.evidence && <p>Source evidence: {Array.isArray(finding.evidence) ? finding.evidence.join(' / ') : finding.evidence}</p>}
          {finding.related_requirement && <p>Related requirement ({finding.related_requirement.source_ref || finding.related_requirement.id}): {finding.related_requirement.text}</p>}
          {finding.rewrite_error && <p role="status">Rewrite checks did not finish ({finding.rewrite_error}). Review is required.</p>}
          {review}
          {/* AI Revision Suggestion */}
          {finding.rewrite_suggestion && (
            <div>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <p className="text-xs font-mono uppercase tracking-wider text-muted-foreground">
                    Proposed Formal Revision
                  </p>
                  {finding.rewrite_passed !== undefined && (
                    <span className={cn(
                      "text-xs font-mono px-1 py-0.2 rounded-sm border",
                      finding.rewrite_passed
                        ? "text-success border-success/40 bg-success/10"
                        : "text-danger border-danger/40 bg-danger/10"
                    )}>
                      {finding.rewrite_passed ? 'CHECKS PASSED · REVIEW REQUIRED' : 'REVIEW REQUIRED'}
                    </span>
                  )}
                  {finding.rewrite_attempts !== undefined && finding.rewrite_attempts > 0 && (
                    <span className="text-xs font-mono text-muted-foreground">
                      ({finding.rewrite_attempts} iteration{finding.rewrite_attempts !== 1 ? 's' : ''})
                    </span>
                  )}
                </div>
                <CopyButton text={finding.rewrite_suggestion} />
              </div>

              <div className="p-2.5 rounded border border-border bg-background text-xs font-mono text-foreground whitespace-pre-wrap leading-relaxed">
                {finding.rewrite_suggestion}
              </div>
              {finding.rewrite_semantic_review && <p className="mt-2">Semantic review (advisory): {finding.rewrite_semantic_review.explanation} This does not prove equivalent intent.</p>}
              {finding.rewrite_checks && <ul className="mt-2 text-xs text-muted-foreground">
                {Object.entries(finding.rewrite_checks).map(([check, passed]) =>
                  <li key={check}>{passed ? 'Passed' : 'Needs review'}: {check.replace(/_/g, ' ')}</li>)}
                <li>Human review is required to confirm intent and approve any new thresholds.</li>
              </ul>}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

