import * as React from "react"
import { Link } from "react-router-dom"
import { ChevronRight, Home } from "lucide-react"
import { cn } from "./Button"

export interface BreadcrumbItem {
  label: string
  to?: string
}

export interface BreadcrumbsProps {
  items: BreadcrumbItem[]
  showHome?: boolean
  className?: string
}

export const Breadcrumbs: React.FC<BreadcrumbsProps> = ({
  items,
  showHome = true,
  className,
}) => {
  return (
    <nav
      aria-label="Breadcrumbs"
      className={cn("flex items-center space-x-1 text-xs text-muted-foreground", className)}
    >
      {showHome && (
        <>
          <Link
            to="/dashboard"
            className="flex items-center hover:text-foreground transition-colors"
          >
            <Home className="h-3.5 w-3.5" />
            <span className="sr-only">Dashboard</span>
          </Link>
          <ChevronRight className="h-3 w-3 text-muted-foreground/60 shrink-0" />
        </>
      )}

      {items.map((item, index) => {
        const isLast = index === items.length - 1
        return (
          <React.Fragment key={index}>
            {item.to && !isLast ? (
              <Link
                to={item.to}
                className="hover:text-foreground transition-colors truncate max-w-[150px]"
              >
                {item.label}
              </Link>
            ) : (
              <span
                className={cn(
                  "truncate max-w-[200px]",
                  isLast && "font-medium text-foreground"
                )}
                aria-current={isLast ? "page" : undefined}
              >
                {item.label}
              </span>
            )}
            {!isLast && <ChevronRight className="h-3 w-3 text-muted-foreground/60 shrink-0" />}
          </React.Fragment>
        )
      })}
    </nav>
  )
}
