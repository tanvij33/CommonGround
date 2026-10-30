import React from "react";
import { cn } from "@/lib/utils";

export interface ChipProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "brand" | "spotlight" | "bridge" | "success" | "warning" | "outline";
  size?: "sm" | "md";
  icon?: React.ReactNode;
}

export const Chip: React.FC<ChipProps> = ({
  children,
  className,
  variant = "default",
  size = "md",
  icon,
  ...props
}) => {
  const baseStyles =
    "inline-flex items-center gap-1.5 font-medium rounded-pill transition-colors select-none tracking-tight";

  const sizeStyles = {
    sm: "text-[11px] px-2.5 py-0.5",
    md: "text-xs px-3 py-1",
  };

  const variantStyles = {
    default: "bg-subtle text-ink-700 border border-borderline/70",
    brand: "bg-brand-violet/10 text-brand-violet border border-brand-violet/25 font-semibold",
    spotlight: "bg-brand-amber/15 text-amber-900 border border-brand-amber/30 font-semibold",
    bridge: "bg-brand-cyan/15 text-cyan-900 border border-brand-cyan/30 font-semibold",
    success: "bg-brand-emerald/10 text-emerald-800 border border-brand-emerald/25",
    warning: "bg-brand-rose/10 text-rose-800 border border-brand-rose/25",
    outline: "bg-white/90 backdrop-blur text-ink-700 border border-borderline shadow-sm",
  };

  return (
    <span
      className={cn(baseStyles, sizeStyles[size], variantStyles[variant], className)}
      {...props}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      {children}
    </span>
  );
};

