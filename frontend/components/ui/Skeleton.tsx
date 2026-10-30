import React from "react";
import { cn } from "@/lib/utils";

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "text" | "rectangular" | "circular" | "card";
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className,
  variant = "text",
  ...props
}) => {
  const variantStyles = {
    text: "h-4 w-full rounded-md",
    rectangular: "h-24 w-full rounded-2xl",
    circular: "h-10 w-10 rounded-full",
    card: "h-48 w-full rounded-3xl",
  };

  return (
    <div
      className={cn(
        "animate-pulse bg-subtle/90 border border-borderline/30",
        variantStyles[variant],
        className
      )}
      {...props}
    />
  );
};

