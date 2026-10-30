import React from "react";
import { cn } from "@/lib/utils";
import { Check } from "lucide-react";

export interface StepItem {
  id: string | number;
  label: string;
  description?: string;
}

export interface StepperProps {
  steps: StepItem[];
  currentStep: number; // 0-indexed
  onStepClick?: (index: number) => void;
  className?: string;
}

export const Stepper: React.FC<StepperProps> = ({
  steps,
  currentStep,
  onStepClick,
  className,
}) => {
  return (
    <div className={cn("flex items-center justify-between w-full select-none", className)}>
      {steps.map((step, index) => {
        const isCompleted = index < currentStep;
        const isCurrent = index === currentStep;

        return (
          <React.Fragment key={step.id}>
            <div
              onClick={() => onStepClick && onStepClick(index)}
              className={cn(
                "flex items-center gap-2.5 transition-colors",
                onStepClick && "cursor-pointer"
              )}
            >
              <div
                className={cn(
                  "w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold transition-all",
                  isCompleted && "bg-brand-emerald text-white shadow-xs",
                  isCurrent && "bg-nearblack text-white shadow-soft ring-4 ring-nearblack/10",
                  !isCompleted && !isCurrent && "bg-subtle text-ink-400 border border-borderline"
                )}
              >
                {isCompleted ? <Check className="w-3.5 h-3.5 stroke-[3]" /> : index + 1}
              </div>
              <div className="hidden sm:block">
                <span
                  className={cn(
                    "text-xs font-medium tracking-tight block",
                    isCurrent ? "text-nearblack font-semibold" : "text-ink-500"
                  )}
                >
                  {step.label}
                </span>
              </div>
            </div>

            {index < steps.length - 1 && (
              <div
                className={cn(
                  "flex-1 h-0.5 mx-3 rounded-full transition-colors",
                  index < currentStep ? "bg-brand-emerald/40" : "bg-borderline/60"
                )}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};

