import * as React from "react"
import { cn } from "@/lib/utils"

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          "flex min-h-[70px] w-full rounded border border-[#303136] bg-[#17181B] px-2.5 py-2 text-xs text-[#E7E7E9] placeholder:text-[#777981] focus:outline-none focus:border-[#7895B5] focus:ring-1 focus:ring-[#7895B5] disabled:cursor-not-allowed disabled:opacity-40 transition-none resize-none font-sans",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Textarea.displayName = "Textarea"

export { Textarea }
