import React from "react";
import { cn } from "@/lib/utils";

export interface GradientOrbProps extends React.HTMLAttributes<HTMLDivElement> {
  intensity?: "subtle" | "vibrant" | "soft";
}

export const GradientOrb: React.FC<GradientOrbProps> = ({
  className,
  intensity = "subtle",
  children,
  ...props
}) => {
  const intensityMap = {
    subtle: "opacity-40 blur-[80px]",
    soft: "opacity-60 blur-[90px]",
    vibrant: "opacity-80 blur-[100px]",
  };

  return (
    <div
      className={cn(
        "relative overflow-hidden isolate select-none",
        className
      )}
      {...props}
    >
      {/* Multicolor blurred gradient background elements */}
      <div
        className={cn(
          "pointer-events-none absolute -top-1/4 -left-1/4 w-[140%] h-[140%] -z-10",
          intensityMap[intensity]
        )}
      >
        <div className="absolute top-[10%] left-[20%] w-[38rem] h-[38rem] rounded-full bg-gradient-to-tr from-brand-violet/50 via-brand-indigo/40 to-transparent" />
        <div className="absolute top-[25%] right-[15%] w-[32rem] h-[32rem] rounded-full bg-gradient-to-bl from-brand-cyan/40 via-brand-blue/30 to-transparent" />
        <div className="absolute bottom-[10%] left-[30%] w-[36rem] h-[36rem] rounded-full bg-gradient-to-r from-brand-rose/30 via-brand-fuchsia/30 to-brand-amber/20" />
      </div>
      {children}
    </div>
  );
};

