import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-sm border px-1.5 py-0.5 text-[11px] font-mono font-medium tracking-tight transition-none select-none",
  {
    variants: {
      variant: {
        default: "border-[#7895B5]/40 bg-[#7895B5]/10 text-[#96B2D1]",
        secondary: "border-[#303136] bg-[#17181B] text-[#A1A1AA]",
        destructive: "border-[#C04848]/40 bg-[#C04848]/10 text-[#E06C6C]",
        outline: "border-[#303136] text-[#A1A1AA] bg-transparent",
        success: "border-[#4E8752]/40 bg-[#4E8752]/10 text-[#68A86C]",
        warning: "border-[#B8863A]/40 bg-[#B8863A]/10 text-[#D49E4B]",
        info: "border-[#7895B5]/40 bg-[#7895B5]/10 text-[#96B2D1]",
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
