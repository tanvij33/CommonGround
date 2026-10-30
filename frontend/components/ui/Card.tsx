import React from "react";
import { cn } from "@/lib/utils";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "elevated" | "subtle" | "bordered" | "interactive";
  padding?: "none" | "sm" | "md" | "lg" | "xl";
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  (
    {
      className,
      variant = "default",
      padding = "lg",
      children,
      ...props
    },
    ref
  ) => {
    const baseStyles = "rounded-3xl transition-all duration-200 relative overflow-hidden";

    const variantStyles = {
      default:
        "bg-white border border-borderline/80 shadow-soft",
      elevated:
        "bg-white border border-borderline/60 shadow-float",
      subtle:
        "bg-subtle/80 border border-borderline/40",
      bordered:
        "bg-white/90 backdrop-blur-md border border-brand-violet/20 shadow-soft",
      interactive:
        "bg-white border border-borderline/80 shadow-soft hover:shadow-float hover:-translate-y-0.5 cursor-pointer",
    };

    const paddingStyles = {
      none: "p-0",
      sm: "p-4",
      md: "p-6",
      lg: "p-8",
      xl: "p-10",
    };

    return (
      <div
        ref={ref}
        className={cn(baseStyles, variantStyles[variant], paddingStyles[padding], className)}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = "Card";

