"use client";

import React, { useState, useEffect } from "react";
import {
  api,
  Plan,
  ProgressEventPayload,
  SAMPLE_PLAN,
  getFairnessScore,
  getMeanScore,
  getSpreadScore,
} from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { ScoreBar } from "@/components/ui/ScoreBar";
import { Chip } from "@/components/ui/Chip";
import { AppWindow } from "@/components/ui/AppWindow";
import {
  X,
  Sparkles,
  MapPin,
  Calendar,
  Coffee,
  Utensils,
  Music,
  Sliders,
  CheckCircle2,
  Loader2,
  ShieldCheck,
} from "lucide-react";

export interface PlanModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const PlanModal: React.FC<PlanModalProps> = ({ isOpen, onClose }) => {
  const [loading, setLoading] = useState<boolean>(false);
  const [progressMsg, setProgressMsg] = useState<string>("");
  const [progressPct, setProgressPct] = useState<number>(0);
  const [plan, setPlan] = useState<Plan | null>(SAMPLE_PLAN);
  const [adventurous, setAdventurous] = useState<number>(0.5);
  const [cultural, setCultural] = useState<number>(0.5);

  const handleStartGeneration = async () => {
    setLoading(true);
    setProgressMsg("Creating demo trip with 4 friends...");
    setProgressPct(5);

    try {
      const demoRes = await api.createDemoTrip();
      const tripId = demoRes.trip_id;

      await api.generatePlan(tripId);

      const unsubscribe = api.subscribeProgress(
        tripId,
        (data: ProgressEventPayload) => {
          setProgressMsg(data.message);
          setProgressPct(data.percent);
          if (data.status === "done") {
            api.getPlan(tripId).then((finalPlan) => {
              setPlan(finalPlan);
              setLoading(false);
            });
          }
        },
        () => {
          // Fallback to sample plan on network error
          setPlan(SAMPLE_PLAN);
          setLoading(false);
        }
      );
    } catch {
      setPlan(SAMPLE_PLAN);
      setLoading(false);
    }
  };

  const handleRebalance = async () => {
    if (!plan) return;
    try {
      const updated = await api.rebalancePlan(plan.trip_id, {
        adventurous,
        cultural,
      });
      setPlan(updated);
    } catch {
      // Local preview update
      setPlan({
        ...plan,
        under_the_hood: {
          ...plan.under_the_hood,
          rebalanced_parameters: { adventurous, cultural },
        },
      });
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-nearblack/60 backdrop-blur-md overflow-y-auto select-none">
      <div className="relative w-full max-w-5xl rounded-3xl bg-white border border-borderline shadow-float my-8 flex flex-col max-h-[90vh] overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-borderline bg-subtle/40">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-brand-violet flex items-center justify-center text-white">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-nearblack tracking-tight">
                4-Friend Live Lisbon Demo
              </h3>
              <p className="text-xs text-ink-500 font-mono">
                Aisha • Rohan • Meera • Kabir
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="primary"
              size="sm"
              onClick={handleStartGeneration}
              disabled={loading}
              icon={loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
            >
              {loading ? "Generating..." : "Run Live Generator"}
            </Button>
            <button
              onClick={onClose}
              className="p-2 rounded-full hover:bg-subtle text-ink-400 hover:text-nearblack transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6">
          {/* Progress Banner (if active) */}
          {loading && (
            <div className="p-4 rounded-2xl bg-brand-violet/10 border border-brand-violet/20 space-y-2">
              <div className="flex items-center justify-between text-xs font-mono font-medium text-brand-violet">
                <span className="flex items-center gap-2">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  {progressMsg || "Planning itinerary..."}
                </span>
                <span>{progressPct}%</span>
              </div>
              <div className="h-1.5 w-full bg-brand-violet/20 rounded-full overflow-hidden">
                <div
                  className="h-full bg-brand-violet transition-all duration-300"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
            </div>
          )}

          {plan && (
            <>
              {/* Hotel Stay Banner */}
              {plan.stay && (
              <div className="p-5 rounded-3xl bg-subtle/80 border border-borderline/80 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-brand-violet uppercase">
                      🏨 Stay Selection
                    </span>
                    <span className="text-xs font-mono text-ink-500">
                      {plan.stay.price_level} • {plan.stay.location}
                    </span>
                  </div>
                  <h4 className="text-lg font-bold text-nearblack tracking-tight">
                    {plan.stay.name}
                  </h4>
                  <p className="text-xs text-ink-500 max-w-2xl leading-relaxed">
                    {plan.stay.description}
                  </p>
                </div>
                <div className="flex flex-wrap gap-1.5 shrink-0">
                  {(plan.stay.tags || []).slice(0, 3).map((tag, i) => (
                    <Chip key={i} variant="outline" size="sm">
                      {tag}
                    </Chip>
                  ))}
                </div>
              </div>
              )}

              {/* Group Fairness Metric Strip */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3.5 rounded-2xl bg-white border border-borderline/70">
                  <span className="text-[10px] font-mono text-ink-400 uppercase">Group Fairness</span>
                  <p className="text-lg font-mono font-bold text-brand-violet">
                    {getFairnessScore(plan.fairness)}%
                  </p>
                </div>
                <div className="p-3.5 rounded-2xl bg-white border border-borderline/70">
                  <span className="text-[10px] font-mono text-ink-400 uppercase">Mean Score</span>
                  <p className="text-lg font-mono font-bold text-nearblack">
                    {getMeanScore(plan.fairness)}%
                  </p>
                </div>
                <div className="p-3.5 rounded-2xl bg-white border border-borderline/70">
                  <span className="text-[10px] font-mono text-ink-400 uppercase">Max Variance</span>
                  <p className="text-lg font-mono font-bold text-emerald-700">
                    {getSpreadScore(plan.fairness)}
                  </p>
                </div>
                <div className="p-3.5 rounded-2xl bg-white border border-borderline/70">
                  <span className="text-[10px] font-mono text-ink-400 uppercase">Qloo Calls</span>
                  <p className="text-lg font-mono font-bold text-brand-cyan">
                    {plan.under_the_hood?.qloo_calls?.total_queries ?? plan.under_the_hood?.qloo_calls?.total ?? "—"}
                  </p>
                </div>
              </div>

              {/* Days Itinerary Timeline */}
              <div className="space-y-6">
                {plan.days.map((day) => (
                  <div key={day.day} className="space-y-3">
                    <div className="flex items-center justify-between pb-1 border-b border-borderline">
                      <span className="text-xs font-mono font-bold text-nearblack uppercase tracking-wider">
                        DAY {day.day} • {day.theme}
                      </span>
                      <span className="text-xs font-mono text-ink-400">
                        {day.slots.length} Curated Stops
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {day.slots.map((slot, sIdx) => (
                        <div
                          key={sIdx}
                          className="p-4 rounded-2xl bg-white border border-borderline/70 space-y-2 shadow-xs"
                        >
                          <div className="flex items-center justify-between text-xs font-mono">
                            <span className="font-bold text-nearblack">
                              [{slot.time}] {slot.type}
                            </span>
                            {slot.spotlight && (
                              <Chip variant="spotlight" size="sm">
                                ★ Spotlight: {slot.spotlight}
                              </Chip>
                            )}
                            {slot.bridge && (
                              <Chip variant="bridge" size="sm">
                                🌉 Bridge: {slot.bridge}
                              </Chip>
                            )}
                          </div>
                          <h5 className="text-xs font-bold text-nearblack line-clamp-1">
                            {slot.name}
                          </h5>
                          <p className="text-[11px] text-ink-500 leading-relaxed line-clamp-2">
                            {slot.why}
                          </p>
                          <div className="pt-2 flex items-center justify-between text-[10px] font-mono border-t border-borderline/40 text-ink-500">
                            <span>Per Person:</span>
                            {Object.entries(slot.per_person).map(([pName, pScore]) => (
                              <span key={pName}>
                                {pName[0]}: {Math.round(pScore * 100)}%
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              {/* Collaborative Soundtrack Card */}
              {plan.extras?.playlist && (
                <div className="p-5 rounded-3xl bg-subtle/80 border border-borderline/80 space-y-3">
                  <div className="flex items-center gap-2">
                    <Music className="w-4 h-4 text-brand-violet" />
                    <h4 className="text-xs font-mono font-bold text-nearblack uppercase tracking-wider">
                      Collaborative Trip Soundtrack (Cross-Taste Bridges)
                    </h4>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {plan.extras.playlist.map((track, tIdx) => (
                      <div
                        key={tIdx}
                        className="p-3 rounded-2xl bg-white border border-borderline/60 space-y-1"
                      >
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-bold text-nearblack">
                            {track.title}
                          </span>
                          <span className="font-mono text-ink-500 text-[11px]">
                            {track.artist}
                          </span>
                        </div>
                        <p className="text-[10px] text-ink-500 leading-tight">
                          {track.note}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

