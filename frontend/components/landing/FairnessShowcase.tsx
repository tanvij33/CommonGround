import React, { useState } from "react";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { GradientOrb } from "@/components/ui/GradientOrb";
import { AppWindow } from "@/components/ui/AppWindow";
import { ScoreBar } from "@/components/ui/ScoreBar";
import { Chip } from "@/components/ui/Chip";
import { Sliders, ShieldCheck, Sparkles, Scale, RefreshCw } from "lucide-react";

export const FairnessShowcase: React.FC = () => {
  const [adventurous, setAdventurous] = useState<number>(0.5);
  const [cultural, setCultural] = useState<number>(0.5);

  // Dynamic adjustment preview
  const aishaScore = Math.min(0.98, 0.563 + (cultural - 0.5) * 0.12);
  const rohanScore = Math.min(0.98, 0.540 + (adventurous - 0.5) * 0.14);
  const meeraScore = Math.min(0.98, 0.588 + (cultural - 0.5) * 0.08);
  const kabirScore = Math.min(0.98, 0.557 - (adventurous - 0.5) * 0.06);

  const mean = (aishaScore + rohanScore + meeraScore + kabirScore) / 4;
  const min = Math.min(aishaScore, rohanScore, meeraScore, kabirScore);
  const groupScore = 0.6 * mean + 0.4 * min;
  const variance = Math.max(aishaScore, rohanScore, meeraScore, kabirScore) - min;

  return (
    <section id="fairness" className="py-20 sm:py-28 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-12">
        <SectionHeader
          kicker="FAIRNESS ENGINE"
          title="Mathematical fairness, audited in real-time"
          description="We replaced subjective group debates with a rigorous mathematical model: group_score = 0.6 * mean + 0.4 * min."
        />

        {/* Large Gradient Showcase */}
        <div className="rounded-4xl bg-white border border-borderline/80 p-3 sm:p-5 shadow-float overflow-hidden">
          <GradientOrb intensity="vibrant" className="rounded-3xl p-6 sm:p-10 lg:p-14">
            <div className="max-w-4xl mx-auto">
              <AppWindow
                title="engine / fairness-evaluation.dashboard"
                badge="ZERO TASTE DEBT"
                headerRight={
                  <div className="flex items-center gap-1.5 text-[11px] font-mono text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-pill border border-emerald-200">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>Self-Critique: PASS</span>
                  </div>
                }
              >
                <div className="space-y-8">
                  {/* Top Summary Stats */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div className="rounded-2xl bg-subtle/80 border border-borderline/70 p-4 space-y-1">
                      <span className="text-[11px] font-mono text-ink-400 uppercase tracking-wider block">
                        Collective Fairness
                      </span>
                      <div className="flex items-baseline gap-2">
                        <span className="text-3xl font-bold font-mono text-brand-violet">
                          {Math.round(groupScore * 100)}%
                        </span>
                        <span className="text-xs text-ink-500 font-mono">0.6·μ + 0.4·min</span>
                      </div>
                    </div>

                    <div className="rounded-2xl bg-subtle/80 border border-borderline/70 p-4 space-y-1">
                      <span className="text-[11px] font-mono text-ink-400 uppercase tracking-wider block">
                        Mean Satisfaction
                      </span>
                      <div className="flex items-baseline gap-2">
                        <span className="text-3xl font-bold font-mono text-nearblack">
                          {Math.round(mean * 100)}%
                        </span>
                        <span className="text-xs text-ink-500 font-mono">across 4 friends</span>
                      </div>
                    </div>

                    <div className="rounded-2xl bg-subtle/80 border border-borderline/70 p-4 space-y-1">
                      <span className="text-[11px] font-mono text-ink-400 uppercase tracking-wider block">
                        Satisfaction Spread
                      </span>
                      <div className="flex items-baseline gap-2">
                        <span className="text-3xl font-bold font-mono text-emerald-700">
                          {(variance * 100).toFixed(1)}%
                        </span>
                        <span className="text-xs text-emerald-700 font-mono font-medium">Equilibrium ✓</span>
                      </div>
                    </div>
                  </div>

                  {/* Individual Satisfaction Bars */}
                  <div className="rounded-3xl bg-white border border-borderline/80 p-6 space-y-4 shadow-xs">
                    <div className="flex items-center justify-between pb-2 border-b border-borderline/50">
                      <h4 className="text-xs font-mono font-bold text-nearblack uppercase tracking-wider">
                        Individual Taste Satisfaction Breakdown
                      </h4>
                      <span className="text-[11px] font-mono text-ink-400">
                        Normalized [0.0 - 1.0]
                      </span>
                    </div>

                    <div className="space-y-4">
                      <ScoreBar
                        label="Aisha"
                        sublabel="Burial, Radiohead, Aesop • Veg Safe"
                        score={aishaScore}
                        color="violet"
                      />
                      <ScoreBar
                        label="Rohan"
                        sublabel="Metallica, Black Sabbath, Nike • Late Nights"
                        score={rohanScore}
                        color="indigo"
                      />
                      <ScoreBar
                        label="Meera"
                        sublabel="Norah Jones, Wes Anderson • Alcohol-Free"
                        score={meeraScore}
                        color="emerald"
                      />
                      <ScoreBar
                        label="Kabir"
                        sublabel="Taylor Swift, Zara, Dua Lipa • Budget $$"
                        score={kabirScore}
                        color="amber"
                      />
                    </div>
                  </div>

                  {/* Interactive Dynamic Rebalancing Slider Controls */}
                  <div className="rounded-3xl bg-subtle/80 border border-borderline/80 p-6 space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Sliders className="w-4 h-4 text-brand-violet" />
                        <h4 className="text-xs font-mono font-bold text-nearblack uppercase tracking-wider">
                          Instant Slider Rebalancing (0 New Qloo Calls)
                        </h4>
                      </div>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-pill bg-white border border-borderline text-ink-500">
                        Cached Pool Re-ranking
                      </span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-1">
                      {/* Adventurous Slider */}
                      <div className="space-y-2">
                        <div className="flex justify-between text-xs font-mono">
                          <span className="text-ink-700">Adventurous Tone</span>
                          <span className="font-bold text-nearblack">{Math.round(adventurous * 100)}%</span>
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.05"
                          value={adventurous}
                          onChange={(e) => setAdventurous(parseFloat(e.target.value))}
                          className="w-full accent-brand-violet cursor-pointer"
                        />
                        <div className="flex justify-between text-[10px] font-mono text-ink-400">
                          <span>Classic Comforts</span>
                          <span>Off-the-beaten-path</span>
                        </div>
                      </div>

                      {/* Cultural Depth Slider */}
                      <div className="space-y-2">
                        <div className="flex justify-between text-xs font-mono">
                          <span className="text-ink-700">Cultural & Architectural Depth</span>
                          <span className="font-bold text-nearblack">{Math.round(cultural * 100)}%</span>
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.05"
                          value={cultural}
                          onChange={(e) => setCultural(parseFloat(e.target.value))}
                          className="w-full accent-brand-violet cursor-pointer"
                        />
                        <div className="flex justify-between text-[10px] font-mono text-ink-400">
                          <span>Leisure & Social</span>
                          <span>Museums & Palaces</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </AppWindow>
            </div>
          </GradientOrb>
        </div>
      </div>
    </section>
  );
};

