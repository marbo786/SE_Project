import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function severityColor(severity: string): string {
  switch (severity?.toLowerCase()) {
    case 'critical':
      return 'bg-danger/10 text-danger border-danger/30'
    case 'major':
      return 'bg-warning/10 text-warning border-warning/30'
    case 'minor':
      return 'bg-warning/10 text-[#C4AC55] border-warning/30'
    case 'info':
      return 'bg-primary/10 text-primary border-primary/30'
    default:
      return 'bg-secondary text-muted-foreground border-border'
  }
}

export function severityBorderColor(severity: string): string {
  switch (severity?.toLowerCase()) {
    case 'critical':
      return 'border-l-danger'
    case 'major':
      return 'border-l-warning'
    case 'minor':
      return 'border-l-warning'
    case 'info':
      return 'border-l-primary'
    default:
      return 'border-l-border'
  }
}

export function severityBadgeVariant(severity: string): 'destructive' | 'default' | 'secondary' | 'outline' {
  switch (severity?.toLowerCase()) {
    case 'critical':
      return 'destructive'
    case 'major':
      return 'default'
    default:
      return 'secondary'
  }
}

export function statusColor(status: string): string {
  switch (status?.toLowerCase()) {
    case 'done':
      return 'bg-success/10 text-success border-success/30'
    case 'analyzing':
      return 'bg-primary/10 text-primary border-primary/30'
    case 'error':
      return 'bg-danger/10 text-danger border-danger/30'
    case 'pending':
    case 'partial':
      return 'bg-secondary text-muted-foreground border-border'
    default:
      return 'bg-secondary text-muted-foreground border-border'
  }
}

export function traceStatusColor(status: string): string {
  switch (status?.toLowerCase()) {
    case 'confirmed':
      return 'bg-success/10 text-success border-success/30'
    case 'rejected':
      return 'bg-danger/10 text-danger border-danger/30'
    case 'suggested':
      return 'bg-warning/10 text-warning border-warning/30'
    default:
      return 'bg-secondary text-muted-foreground border-border'
  }
}

export function scoreColor(score: number): string {
  if (score >= 80) return 'text-success'
  if (score >= 60) return 'text-warning'
  return 'text-danger'
}

function apiDate(date: string | Date): Date {
  // Legacy SQLite timestamps are UTC without an offset. Explicit offsets and
  // Date objects already describe an instant and must remain unchanged.
  return new Date(typeof date === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(date) && !/(Z|[+-]\d{2}:\d{2})$/i.test(date) ? `${date}Z` : date)
}

export function formatDate(date: string | Date): string {
  if (!date) return '—'
  return apiDate(date).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatRelativeDate(date: string | Date): string {
  if (!date) return '—'
  const now = new Date()
  const d = apiDate(date)
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  const diffHr = Math.floor(diffMin / 60)
  const diffDay = Math.floor(diffHr / 24)

  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  if (diffHr < 24) return `${diffHr}h ago`
  if (diffDay < 7) return `${diffDay}d ago`
  return formatDate(date)
}
