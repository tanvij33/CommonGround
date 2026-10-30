import React from "react";
import { cn } from "@/lib/utils";
import { CheckCircle2, AlertCircle, Info, X } from "lucide-react";

export interface ToastProps {
  type?: "success" | "error" | "info";
  title: string;
  message?: string;
  onClose?: () => void;
  className?: string;
}

export const Toast: React.FC<ToastProps> = ({
  type = "info",
  title,
  message,
  onClose,
  className,
}) => {
  const icons = {
    success: <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />,
    error: <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />,
    info: <Info className="w-4 h-4 text-brand-violet shrink-0" />,
  };

  const borders = {
    success: "border-emerald-200 bg-white/95",
    error: "border-rose-200 bg-white/95",
    info: "border-brand-violet/20 bg-white/95",
  };

  return (
    <div
      className={cn(
        "rounded-2xl p-4 shadow-float border backdrop-blur-md flex items-start gap-3 select-none max-w-sm transition-all",
        borders[type],
        className
      )}
    >
      {icons[type]}
      <div className="flex-1 space-y-0.5">
        <h4 className="text-xs font-semibold text-nearblack tracking-tight">{title}</h4>
        {message && <p className="text-xs text-ink-500 leading-relaxed">{message}</p>}
      </div>
      {onClose && (
        <button
          onClick={onClose}
          className="text-ink-400 hover:text-nearblack transition-colors -mr-1 -mt-1 p-1 rounded-full hover:bg-subtle"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
};

