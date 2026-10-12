import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"
import { Loader2 } from "lucide-react"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded text-xs font-medium tracking-normal transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#7895B5] disabled:pointer-events-none disabled:opacity-40 select-none",
  {
    variants: {
      variant: {
        default: "bg-[#7895B5] text-[#111214] font-semibold hover:bg-[#8CA8C8]",
        secondary: "bg-[#1D1E22] text-[#E7E7E9] border border-[#303136] hover:bg-[#24252A] hover:border-[#3D3E44]",
        outline: "bg-transparent text-[#E7E7E9] border border-[#303136] hover:bg-[#1D1E22] hover:border-[#3D3E44]",
        ghost: "bg-transparent text-[#A1A1AA] hover:text-[#E7E7E9] hover:bg-[#1D1E22]",
        destructive: "bg-[#C04848]/20 text-[#E06C6C] border border-[#C04848]/40 hover:bg-[#C04848]/30",
        link: "text-[#7895B5] underline-offset-4 hover:underline p-0 h-auto",
        success: "bg-[#4E8752]/20 text-[#68A86C] border border-[#4E8752]/40 hover:bg-[#4E8752]/30",
      },
      size: {
        default: "h-8 px-3 py-1.5",
        sm: "h-7 px-2.5 text-[11px]",
        lg: "h-9 px-4 text-xs font-semibold",
        icon: "h-8 w-8 p-0",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
  loading?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, loading = false, children, disabled, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={disabled || loading}
        {...props}
      >
        {loading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
        {children}
      </Comp>
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
