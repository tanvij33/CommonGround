"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { GradientOrb } from "@/components/ui/GradientOrb";
import { AppWindow } from "@/components/ui/AppWindow";
import { Button } from "@/components/ui/Button";
import { api, ProgressEventPayload } from "@/lib/api";
import {
  Sparkles,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Compass,
  ArrowRight,
  ShieldCheck,
  Music,
  Activity,
} from "lucide-react";

export default function GeneratingPlanPage() {
  const params = useParams();
  const router = useRouter();
  const tripId = (params?.tripId as string) || "trip-demo";

  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [percent, setPercent] = useState(10);
  const [statusMessage, setStatusMessage] = useState("Initializing Cultural AI planner...");
  const [isFailed, setIsFailed] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const plannedStages = [
    { label: "Reading traveler taste signals & constraints", pct: 15 },
    { label: "Querying Qloo's 575M+ entity graph across 6 categories", pct: 35 },
    { label: "Enforcing strict municipal metro boundaries", pct: 50 },
    { label: "Filtering dietary & alcohol-free guardrails", pct: 65 },
    { label: "Calculating group fairness (0.6·μ + 0.4·min)", pct: 80 },
    { label: "Programmatic self-critique: zero hallucinations", pct: 92 },
    { label: "Compiling group soundtrack & final itinerary", pct: 100 },
  ];

  useEffect(() => {
    let isMounted = true;
    let timer: NodeJS.Timeout;
    let unsubscribe: (() => void) | undefined;

    const startGenerationAndListen = async () => {
      try {
        // Trigger background plan generation; a refusal (for example no travelers yet) is shown, not swallowed
        await api.generatePlan(tripId);
        if (!isMounted) return; // effect was cleaned up while the request was in flight (React StrictMode)

        // Subscribe to live SSE progress stream
        unsubscribe = api.subscribeProgress(
          tripId,
          (payload: ProgressEventPayload) => {
            if (!isMounted) return;

            setStatusMessage(payload.message);
            setPercent(payload.percent);

            // Update step indicator based on percent
            if (payload.percent >= 95) setCurrentStepIndex(6);
            else if (payload.percent >= 85) setCurrentStepIndex(5);
            else if (payload.percent >= 65) setCurrentStepIndex(4);
            else if (payload.percent >= 50) setCurrentStepIndex(3);
            else if (payload.percent >= 30) setCurrentStepIndex(2);
            else if (payload.percent >= 15) setCurrentStepIndex(1);

            if (payload.status === "done") {
              setPercent(100);
              setStatusMessage("Itinerary verified and ready!");
              timer = setTimeout(() => {
                router.push(`/trip/${tripId}/plan`);
              }, 1200);
            } else if (payload.status === "failed") {
              setIsFailed(true);
              setErrorMessage(payload.message);
            }
          },
          () => {
            // Never fake progress or jump to a plan page: tell the user the connection was lost
            if (!isMounted) return;
            setIsFailed(true);
            setErrorMessage("Lost the connection to the server while planning. Check that the backend is running, then retry.");
          }
        );
      } catch (err: any) {
        if (!isMounted) return;
        setIsFailed(true);
        setErrorMessage(err?.message || "Failed to initiate generation");
      }
    };

    startGenerationAndListen();

    return () => {
      isMounted = false;
      if (timer) clearTimeout(timer);
      unsubscribe?.(); // close the event stream on unmount or retry
    };
  }, [tripId, router]);

  const handleRetry = () => {
    setIsFailed(false);
    setErrorMessage(null);
    setPercent(10);
    setCurrentStepIndex(0);
    // router.refresh() does not re-run the effect that starts generation; a reload does
    window.location.reload();
  };

  return (
    <div className="min-h-screen bg-offwhite text-nearblack flex flex-col justify-center items-center p-4 sm:p-6 relative overflow-hidden select-none">
      {/* Soft Animated Multicolor Gradient Mesh strictly inside background visual */}
      <GradientOrb intensity="vibrant" className="w-full max-w-2xl rounded-4xl p-2 sm:p-4 shadow-float">
        <AppWindow
          title={`agent / ${tripId} / live-telemetry.stream`}
          badge="SSE ACTIVE"
          className="w-full bg-white/95 backdrop-blur-xl"
        >
          <div className="space-y-8 p-2 sm:p-4">
            {/* Top Indicator */}
            <div className="text-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-brand-violet/10 border border-brand-violet/20 flex items-center justify-center text-brand-violet mx-auto shadow-xs">
                {isFailed ? (
                  <AlertCircle className="w-6 h-6 text-rose-500" />
                ) : (
                  <Loader2 className="w-6 h-6 animate-spin text-brand-violet" />
                )}
              </div>

              <div className="space-y-1">
                <span className="text-xs font-mono font-bold text-brand-violet uppercase tracking-wider">
                  Autonomous Taste-Fair Agent
                </span>
                <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-nearblack">
                  {isFailed ? "Generation Paused" : "Synthesizing Common Ground"}
                </h2>
                <p className="text-xs sm:text-sm font-mono text-ink-500 max-w-md mx-auto">
                  {statusMessage}
                </p>
              </div>
            </div>

            {/* Live Progress Bar */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-ink-500">Pipeline Execution:</span>
                <span className="font-bold text-nearblack">{percent}%</span>
              </div>
              <div className="h-2 w-full bg-subtle rounded-pill overflow-hidden border border-borderline/60">
                <div
                  className="h-full bg-brand-violet rounded-pill transition-all duration-500 ease-out"
                  style={{ width: `${percent}%` }}
                />
              </div>
            </div>

            {/* Stepper Timeline */}
            <div className="space-y-2.5 pt-2 border-t border-borderline/50">
              {plannedStages.map((stage, idx) => {
                const isCompleted = idx < currentStepIndex;
                const isCurrent = idx === currentStepIndex && !isFailed;

                return (
                  <div
                    key={idx}
                    className={`flex items-center justify-between text-xs p-2.5 rounded-2xl border transition-all ${
                      isCompleted
                        ? "bg-white border-emerald-200 text-ink-900"
                        : isCurrent
                        ? "bg-brand-violet/5 border-brand-violet/30 text-brand-violet font-semibold shadow-xs"
                        : "bg-subtle/40 border-borderline/40 text-ink-400"
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      {isCompleted ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                      ) : isCurrent ? (
                        <Loader2 className="w-4 h-4 animate-spin text-brand-violet shrink-0" />
                      ) : (
                        <div className="w-4 h-4 rounded-full border border-borderline/80 shrink-0" />
                      )}
                      <span className="tracking-tight">{stage.label}</span>
                    </div>

                    <span className="text-[10px] font-mono">
                      {stage.pct}%
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Error Actions (if failed) */}
            {isFailed && (
              <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-center space-y-3">
                <p className="text-xs text-rose-700 font-mono">
                  {errorMessage || "Connection timed out. You can retry or view fallback plan."}
                </p>
                <div className="flex justify-center gap-3">
                  <Button variant="primary" size="sm" onClick={handleRetry}>
                    Retry Pipeline
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => router.push(`/trip/${tripId}`)}
                  >
                    Open plan page
                  </Button>
                </div>
              </div>
            )}
          </div>
        </AppWindow>
      </GradientOrb>
    </div>
  );
}

