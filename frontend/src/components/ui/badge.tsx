import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-sm border px-1.5 py-0.5 text-xs font-mono font-medium tracking-tight transition-none select-none",
  {
    variants: {
      variant: {
        default: "border-primary/40 bg-primary/10 text-primary",
        secondary: "border-border bg-secondary text-muted-foreground",
        destructive: "border-danger/40 bg-danger/10 text-danger",
        outline: "border-border text-muted-foreground bg-transparent",
        success: "border-success/40 bg-success/10 text-success",
        warning: "border-warning/40 bg-warning/10 text-warning",
        info: "border-primary/40 bg-primary/10 text-primary",
      },
    },
    defaultVariants: { variant: "default" },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
