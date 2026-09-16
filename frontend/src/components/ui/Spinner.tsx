import * as React from "react"
import { Loader2 } from "lucide-react"
import { cn } from "./Button"

export interface SpinnerProps extends React.HTMLAttributes<HTMLDivElement> {
  size?: "sm" | "default" | "lg"
}

export const Spinner: React.FC<SpinnerProps> = ({
  size = "default",
  className,
  ...props
}) => {
  const sizeClasses = {
    sm: "h-4 w-4",
    default: "h-6 w-6",
    lg: "h-10 w-10",
  }

  return (
    <div
      role="status"
      aria-label="Loading"
      className={cn("flex items-center justify-center text-primary", className)}
      {...props}
    >
      <Loader2 className={cn("animate-spin", sizeClasses[size])} />
      <span className="sr-only">Loading...</span>
    </div>
  )
}
