import React from "react";
import { cn } from "@/lib/utils";

export interface SectionHeaderProps {
  kicker?: string;
  title: string;
  description?: string;
  align?: "left" | "center";
  className?: string;
}

export const SectionHeader: React.FC<SectionHeaderProps> = ({
  kicker,
  title,
  description,
  align = "center",
  className,
}) => {
  return (
    <div
      className={cn(
        "space-y-3.5 max-w-2xl",
        align === "center" ? "mx-auto text-center" : "text-left",
        className
      )}
    >
      {kicker && (
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-pill bg-brand-violet/10 border border-brand-violet/20 text-brand-violet text-xs font-semibold tracking-tight">
          <span>●</span>
          <span>{kicker}</span>
        </div>
      )}
      <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight text-nearblack leading-[1.12]">
        {title}
      </h2>
      {description && (
        <p className="text-base sm:text-lg text-ink-500 font-normal leading-relaxed tracking-tight">
          {description}
        </p>
      )}
    </div>
  );
};

