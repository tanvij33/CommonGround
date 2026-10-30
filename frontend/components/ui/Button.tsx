import React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "gradient";
  size?: "sm" | "md" | "lg";
  icon?: React.ReactNode;
  iconPosition?: "left" | "right";
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "md",
      icon,
      iconPosition = "left",
      children,
      disabled,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      "inline-flex items-center justify-center font-medium rounded-pill transition-all duration-200 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none select-none tracking-tight";

    const sizeStyles = {
      sm: "text-xs px-3.5 py-1.5 gap-1.5",
      md: "text-sm px-5 py-2.5 gap-2",
      lg: "text-base px-6 py-3 gap-2.5 font-semibold",
    };

    const variantStyles = {
      primary:
        "bg-nearblack text-white hover:bg-black shadow-sm hover:shadow",
      secondary:
        "bg-subtle text-nearblack hover:bg-borderline border border-borderline/60",
      outline:
        "bg-white/80 backdrop-blur text-nearblack border border-borderline hover:bg-subtle shadow-sm",
      ghost:
        "bg-transparent text-ink-700 hover:text-nearblack hover:bg-subtle",
      gradient:
        "bg-gradient-to-r from-brand-violet via-brand-indigo to-brand-blue text-white shadow-soft hover:shadow-glow",
    };

    return (
      <button
        ref={ref}
        disabled={disabled}
        className={cn(baseStyles, sizeStyles[size], variantStyles[variant], className)}
        {...props}
      >
        {icon && iconPosition === "left" && <span className="shrink-0">{icon}</span>}
        {children}
        {icon && iconPosition === "right" && <span className="shrink-0">{icon}</span>}
      </button>
    );
  }
);

Button.displayName = "Button";

