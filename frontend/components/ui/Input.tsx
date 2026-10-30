import React from "react";
import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  icon?: React.ReactNode;
  iconPosition?: "left" | "right";
  error?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, icon, iconPosition = "left", error, ...props }, ref) => {
    return (
      <div className="w-full space-y-1">
        <div className="relative flex items-center">
          {icon && iconPosition === "left" && (
            <span className="absolute left-3.5 text-ink-400 pointer-events-none shrink-0">
              {icon}
            </span>
          )}
          <input
            ref={ref}
            className={cn(
              "w-full rounded-pill bg-white border border-borderline px-4 py-2.5 text-sm text-nearblack placeholder:text-ink-400 shadow-sm transition-all focus:outline-none focus:border-brand-violet focus:ring-2 focus:ring-brand-violet/20 disabled:opacity-50",
              icon && iconPosition === "left" && "pl-10",
              icon && iconPosition === "right" && "pr-10",
              error && "border-rose-400 focus:border-rose-500 focus:ring-rose-500/20",
              className
            )}
            {...props}
          />
          {icon && iconPosition === "right" && (
            <span className="absolute right-3.5 text-ink-400 pointer-events-none shrink-0">
              {icon}
            </span>
          )}
        </div>
        {error && <p className="text-xs text-rose-500 px-3">{error}</p>}
      </div>
    );
  }
);

Input.displayName = "Input";

