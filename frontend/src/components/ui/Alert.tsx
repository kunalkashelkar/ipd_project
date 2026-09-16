import * as React from "react"
import { cn } from "./Button"
import { AlertCircle, CheckCircle2, Info, AlertTriangle } from "lucide-react"

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "info" | "success" | "warning" | "destructive"
  title?: string
  icon?: React.ReactNode
}

export const Alert = React.forwardRef<HTMLDivElement, AlertProps>(
  ({ className, variant = "info", title, icon, children, ...props }, ref) => {
    const variants = {
      info: "bg-blue-500/10 text-blue-400 border-blue-500/20",
      success: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
      warning: "bg-amber-500/10 text-amber-400 border-amber-500/20",
      destructive: "bg-destructive/10 text-destructive border-destructive/20",
    }

    const defaultIcons = {
      info: <Info className="h-5 w-5 shrink-0" />,
      success: <CheckCircle2 className="h-5 w-5 shrink-0" />,
      warning: <AlertTriangle className="h-5 w-5 shrink-0" />,
      destructive: <AlertCircle className="h-5 w-5 shrink-0" />,
    }

    return (
      <div
        ref={ref}
        role="alert"
        className={cn(
          "relative w-full rounded-lg border p-4 flex gap-3 text-sm transition-colors",
          variants[variant],
          className
        )}
        {...props}
      >
        <div className="pt-0.5">{icon || defaultIcons[variant]}</div>
        <div className="flex-1 space-y-1">
          {title && <h5 className="font-semibold leading-none tracking-tight">{title}</h5>}
          <div className="text-muted-foreground text-xs leading-relaxed">{children}</div>
        </div>
      </div>
    )
  }
)
Alert.displayName = "Alert"
