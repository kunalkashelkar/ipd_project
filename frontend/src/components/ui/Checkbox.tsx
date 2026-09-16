import * as React from "react"
import { cn } from "./Button"
import { Check } from "lucide-react"

export interface CheckboxProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {
  label?: string
  description?: string
}

export const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, label, description, id, checked, ...props }, ref) => {
    const inputId = id || React.useId()

    return (
      <div className="flex items-start space-x-3">
        <div className="relative flex items-center justify-center">
          <input
            id={inputId}
            type="checkbox"
            checked={checked}
            ref={ref}
            className={cn(
              "peer h-4 w-4 shrink-0 rounded border border-border bg-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 checked:bg-primary checked:border-primary transition-colors cursor-pointer accent-primary",
              className
            )}
            {...props}
          />
        </div>
        {(label || description) && (
          <div className="grid gap-1 leading-none select-none">
            {label && (
              <label
                htmlFor={inputId}
                className="text-sm font-medium text-foreground cursor-pointer peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                {label}
              </label>
            )}
            {description && (
              <p className="text-xs text-muted-foreground">{description}</p>
            )}
          </div>
        )}
      </div>
    )
  }
)
Checkbox.displayName = "Checkbox"
