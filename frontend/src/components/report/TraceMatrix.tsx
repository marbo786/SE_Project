import { EmptyState } from '@/components/ui/empty-state'
import { Link2 } from 'lucide-react'
import { cn, traceStatusColor } from '@/lib/utils'
import type { TraceLink } from './types'
export function TraceMatrix({ filteredTraceLinks, traceLinks, reviewBusy, updateLinkStatus }: { filteredTraceLinks: TraceLink[]; traceLinks: TraceLink[]; reviewBusy: boolean; updateLinkStatus: (id: number, status: 'confirmed' | 'rejected') => Promise<void> }) {
  return <div className="rounded border border-border bg-card overflow-hidden">
            <div tabIndex={0} role="region" aria-label="Trace matrix scroll area" className="overflow-x-auto scrollbar-technical">
              <table className="w-full text-left text-xs"><caption className="sr-only">Traceability relationships and review decisions</caption>
                <thead>
                  <tr className="border-b border-border bg-secondary text-xs font-mono uppercase tracking-wider text-muted-foreground">
                    <th className="py-2.5 px-3.5 font-medium">Source Requirement</th>
                    <th className="py-2.5 px-3 font-medium text-center">Status</th>
                    <th className="py-2.5 px-3 font-medium">Target Architecture Element</th>
                    <th className="py-2.5 px-3.5 text-right font-medium print:hidden">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {filteredTraceLinks.length === 0 ? (
                    <tr>
                      <td colSpan={4}>
                        <EmptyState
                          icon={Link2}
                          title={traceLinks.length === 0 ? 'No traceability traces mapped' : 'No trace links match filter'}
                          description={traceLinks.length === 0
                            ? 'UML model diagrams (.puml) must be uploaded to generate automated architecture mappings.'
                            : 'Adjust the status filter to inspect other trace links.'
                          }
                          className="m-4 border-0"
                        />
                      </td>
                    </tr>
                  ) : (
                    filteredTraceLinks.map(t => (
                      <tr key={t.id} className="hover:bg-accent/40 transition-none">
                        <td className="py-2.5 px-3.5 font-mono">
                          <span className="font-semibold text-foreground">{t.source_label || t.source_id}</span>
                          <span className="text-xs text-muted-foreground ml-1.5">[{t.source_type}]</span>
                        </td>
                        <td className="py-2.5 px-3 text-center whitespace-nowrap">
                          <span
                            className={cn(
                              "inline-flex items-center px-1.5 py-0.2 rounded-sm text-xs font-mono border uppercase",
                              traceStatusColor(t.status)
                            )}
                          >
                            {t.is_stale ? 'stale' : t.status}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 font-mono">
                          <span className="font-semibold text-foreground">{t.target_label || t.target_id}</span>
                          <span className="text-xs text-muted-foreground ml-1.5">[{t.target_type}]</span>
                          {t.evidence && <details><summary className="cursor-pointer">Link evidence</summary><pre className="whitespace-pre-wrap break-all max-w-md">{JSON.stringify(t.evidence, null, 2)}</pre></details>}
                          <p className="text-xs text-muted-foreground mt-1">{t.origin?.replace(/_/g, ' ')} {t.confidence != null && `· similarity ${t.confidence.toFixed(2)} (not a probability)`}</p>
                        </td>
                        <td className="py-2.5 px-3.5 text-right whitespace-nowrap print:hidden">
                          {!t.is_stale ? (
                            <div className="flex items-center justify-end gap-1 font-mono">
                              <button
                                disabled={reviewBusy || t.status === 'confirmed'}
                                onClick={() => updateLinkStatus(t.id, 'confirmed')}
                                className="px-2 py-0.5 rounded border border-success/40 bg-success/10 text-success text-xs hover:bg-success/20"
                              >
                                Confirm
                              </button>
                              <button
                                disabled={reviewBusy || t.status === 'rejected'}
                                onClick={() => updateLinkStatus(t.id, 'rejected')}
                                className="px-2 py-0.5 rounded border border-danger/40 bg-danger/10 text-danger text-xs hover:bg-danger/20"
                              >
                                Reject
                              </button>
                            </div>
                          ) : (
                            <span className="text-xs font-mono text-muted-foreground">
                              REVIEWED
                            </span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
}
