import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-accent-primary focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-accent-primary text-background",
        secondary: "border-transparent bg-background-tertiary text-foreground-secondary",
        success: "border-transparent bg-accent-success text-background",
        warning: "border-transparent bg-accent-warning text-background",
        destructive: "border-transparent bg-accent-danger text-white",
        info: "border-transparent bg-accent-info text-white",
        outline: "border-border text-foreground",
        glass: "border-border/50 glass text-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }