import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function severityColor(severity: string): string {
  switch (severity?.toLowerCase()) {
    case 'critical':
      return 'bg-[#C04848]/10 text-[#E06C6C] border-[#C04848]/30'
    case 'major':
      return 'bg-[#B8863A]/10 text-[#D49E4B] border-[#B8863A]/30'
    case 'minor':
      return 'bg-[#A89048]/10 text-[#C4AC55] border-[#A89048]/30'
    case 'info':
      return 'bg-[#7895B5]/10 text-[#96B2D1] border-[#7895B5]/30'
    default:
      return 'bg-[#17181B] text-[#A1A1AA] border-[#303136]'
  }
}

export function severityBorderColor(severity: string): string {
  switch (severity?.toLowerCase()) {
    case 'critical':
      return 'border-l-[#C04848]'
    case 'major':
      return 'border-l-[#B8863A]'
    case 'minor':
      return 'border-l-[#A89048]'
    case 'info':
      return 'border-l-[#7895B5]'
    default:
      return 'border-l-[#303136]'
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
      return 'bg-[#4E8752]/10 text-[#68A86C] border-[#4E8752]/30'
    case 'analyzing':
      return 'bg-[#7895B5]/10 text-[#96B2D1] border-[#7895B5]/30'
    case 'error':
      return 'bg-[#C04848]/10 text-[#E06C6C] border-[#C04848]/30'
    case 'pending':
    case 'partial':
      return 'bg-[#17181B] text-[#A1A1AA] border-[#303136]'
    default:
      return 'bg-[#17181B] text-[#777981] border-[#303136]'
  }
}

export function traceStatusColor(status: string): string {
  switch (status?.toLowerCase()) {
    case 'confirmed':
      return 'bg-[#4E8752]/10 text-[#68A86C] border-[#4E8752]/30'
    case 'rejected':
      return 'bg-[#C04848]/10 text-[#E06C6C] border-[#C04848]/30'
    case 'suggested':
      return 'bg-[#B8863A]/10 text-[#D49E4B] border-[#B8863A]/30'
    default:
      return 'bg-[#17181B] text-[#777981] border-[#303136]'
  }
}

export function scoreColor(score: number): string {
  if (score >= 80) return 'text-[#68A86C]'
  if (score >= 60) return 'text-[#D49E4B]'
  return 'text-[#E06C6C]'
}

export function formatDate(date: string | Date): string {
  if (!date) return '—'
  return new Date(date).toLocaleDateString('en-US', {
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
  const d = new Date(date)
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
