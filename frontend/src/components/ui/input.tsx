import * as React from "react"
import { cn } from "@/lib/utils"
import { Search } from "lucide-react"

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-8 w-full rounded border border-[#303136] bg-[#17181B] px-2.5 py-1.5 text-xs text-[#E7E7E9] placeholder:text-[#777981] focus:outline-none focus:border-[#7895B5] focus:ring-1 focus:ring-[#7895B5] disabled:cursor-not-allowed disabled:opacity-40 transition-none font-sans",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

interface SearchInputProps extends InputProps {
  containerClassName?: string
}

const SearchInput = React.forwardRef<HTMLInputElement, SearchInputProps>(
  ({ containerClassName, className, ...props }, ref) => {
    return (
      <div className={cn("relative", containerClassName)}>
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-[#777981]" />
        <Input ref={ref} className={cn("pl-8", className)} {...props} />
      </div>
    )
  }
)
SearchInput.displayName = "SearchInput"

export { Input, SearchInput }
