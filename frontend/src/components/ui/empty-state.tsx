import { cn } from "@/lib/utils"
import { type LucideIcon } from "lucide-react"
import { Button } from "./button"

interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  description?: string
  action?: {
    label: string
    onClick?: () => void
    href?: string
  }
  className?: string
}

export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center py-10 px-4 text-center border border-dashed border-[#303136] rounded bg-[#17181B]/50", className)}>
      {Icon && (
        <div className="flex items-center justify-center w-8 h-8 rounded border border-[#303136] bg-[#1D1E22] mb-3 text-[#777981]">
          <Icon className="h-4 w-4" />
        </div>
      )}
      <p className="text-xs font-medium text-[#E7E7E9] mb-0.5">{title}</p>
      {description && (
        <p className="text-xs text-[#777981] max-w-sm mb-3">{description}</p>
      )}
      {action && (
        <Button
          variant="outline"
          size="sm"
          onClick={action.onClick}
        >
          {action.label}
        </Button>
      )}
    </div>
  )
}
