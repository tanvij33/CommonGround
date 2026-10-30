import React from "react";
import { cn } from "@/lib/utils";

export interface AppWindowProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  badge?: string;
  headerRight?: React.ReactNode;
}

export const AppWindow: React.FC<AppWindowProps> = ({
  title,
  badge,
  headerRight,
  children,
  className,
  ...props
}) => {
  return (
    <div
      className={cn(
        "rounded-3xl bg-white/95 backdrop-blur-xl border border-borderline/80 shadow-float overflow-hidden flex flex-col",
        className
      )}
      {...props}
    >
      {/* Window Header */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-borderline/60 bg-subtle/50 select-none">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-400/80 inline-block border border-rose-500/20" />
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400/80 inline-block border border-amber-500/20" />
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400/80 inline-block border border-emerald-500/20" />
          </div>
          {title && (
            <span className="ml-3 text-xs font-mono font-medium text-ink-500 tracking-tight">
              {title}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2.5">
          {badge && (
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-pill bg-white border border-borderline/80 text-ink-700 font-semibold shadow-xs">
              {badge}
            </span>
          )}
          {headerRight}
        </div>
      </div>

      {/* Window Body */}
      <div className="flex-1 p-6 overflow-y-auto">{children}</div>
    </div>
  );
};

