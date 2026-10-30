import React from "react";
import { cn, formatPercent } from "@/lib/utils";

export interface ScoreBarProps {
  label: string;
  score: number; // 0.0 to 1.0 or 0 to 100
  sublabel?: string;
  className?: string;
  color?: "violet" | "emerald" | "amber" | "indigo";
  showValue?: boolean;
}

export const ScoreBar: React.FC<ScoreBarProps> = ({
  label,
  score,
  sublabel,
  className,
  color = "violet",
  showValue = true,
}) => {
  // Normalize 0-100 or 0-1 to percentage 0-100
  const normalized = score > 1 ? Math.min(100, Math.max(0, score)) : Math.min(100, Math.max(0, score * 100));

  const barColors = {
    violet: "bg-brand-violet",
    indigo: "bg-brand-indigo",
    emerald: "bg-brand-emerald",
    amber: "bg-brand-amber",
  };

  return (
    <div className={cn("space-y-1.5 select-none", className)}>
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium text-ink-900 tracking-tight flex items-center gap-1.5">
          {label}
          {sublabel && <span className="text-ink-500 font-normal">({sublabel})</span>}
        </span>
        {showValue && (
          <span className="font-mono text-ink-700 font-semibold">
            {formatPercent(normalized / 100)}
          </span>
        )}
      </div>
      <div className="h-2 w-full bg-subtle rounded-pill overflow-hidden border border-borderline/40 p-0.5">
        <div
          className={cn("h-full rounded-pill transition-all duration-700 ease-out", barColors[color])}
          style={{ width: `${normalized}%` }}
        />
      </div>
    </div>
  );
};

