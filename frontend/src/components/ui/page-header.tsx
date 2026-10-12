import { cn } from "@/lib/utils"

interface PageHeaderProps {
  title: string
  description?: string
  children?: React.ReactNode
  className?: string
}

export function PageHeader({ title, description, children, className }: PageHeaderProps) {
  return (
    <div className={cn("flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-4 mb-6 border-b border-[#303136]/70", className)}>
      <div className="space-y-0.5">
        <h1 className="text-base font-semibold tracking-tight text-[#E7E7E9]">{title}</h1>
        {description && (
          <p className="text-xs text-[#777981]">{description}</p>
        )}
      </div>
      {children && (
        <div className="flex items-center gap-2">
          {children}
        </div>
      )}
    </div>
  )
}

interface BreadcrumbItem {
  label: string
  href?: string
}

interface BreadcrumbsProps {
  items: BreadcrumbItem[]
  className?: string
}

export function Breadcrumbs({ items, className }: BreadcrumbsProps) {
  return (
    <nav aria-label="Breadcrumb" className={cn("flex items-center gap-1.5 text-xs mb-3 font-mono", className)}>
      {items.map((item, index) => (
        <span key={index} className="flex items-center gap-1.5">
          {index > 0 && (
            <span className="text-[#303136]">/</span>
          )}
          {item.href ? (
            <a
              href={item.href}
              className="text-[#777981] hover:text-[#E7E7E9] transition-none"
            >
              {item.label}
            </a>
          ) : (
            <span className="text-[#A1A1AA] font-medium">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  )
}
