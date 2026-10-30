import React from "react";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import { XCircle, CheckCircle2, Bot, Sparkles, TrendingUp } from "lucide-react";

export const LlmComparisonTeaser: React.FC = () => {
  return (
    <section id="comparison" className="py-20 sm:py-28 px-4 sm:px-6 lg:px-8 bg-subtle/40 border-t border-borderline/60">
      <div className="max-w-7xl mx-auto space-y-12">
        <SectionHeader
          kicker="WHY GENERIC AI FAILS"
          title="Plain LLM vs. Common Ground"
          description="Prompting a generic frontier model with 4 contrasting tastes results in hallucinated tourist cliches. Qloo provides the ground truth of culture."
        />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-stretch">
          {/* Plain LLM Baseline (Flawed) */}
          <div className="rounded-3xl p-6 sm:p-8 bg-white border border-rose-200/80 shadow-soft flex flex-col justify-between space-y-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-full bg-rose-100 flex items-center justify-center text-rose-600">
                    <Bot className="w-4 h-4" />
                  </div>
                  <h4 className="text-base font-bold text-nearblack tracking-tight">
                    Standard Plain-LLM Prompt
                  </h4>
                </div>
                <span className="text-[10px] font-mono text-rose-700 bg-rose-50 px-2.5 py-0.5 rounded-pill border border-rose-200 font-semibold">
                  Fairness Score: 44.2%
                </span>
              </div>

              <p className="text-xs sm:text-sm text-ink-500 leading-relaxed">
                Prompt: <em>"Create a 2-day Lisbon itinerary for Aisha (Burial, Radiohead), Rohan (Metallica), Meera (Norah Jones), and Kabir (Taylor Swift)."</em>
              </p>

              {/* Flaws list */}
              <div className="space-y-3 pt-2">
                <div className="flex items-start gap-2.5 text-xs text-ink-700">
                  <XCircle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                  <div>
                    <strong className="text-nearblack font-semibold">Generic Tourist Defaults:</strong> Places Time Out Market and Tram 28 in every slot—neither satisfying Burial fans nor indie listeners.
                  </div>
                </div>
                <div className="flex items-start gap-2.5 text-xs text-ink-700">
                  <XCircle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                  <div>
                    <strong className="text-nearblack font-semibold">Severe Taste Disparity:</strong> 38% satisfaction variance. Kabir & Meera dominate; Aisha & Rohan are completely alienated.
                  </div>
                </div>
                <div className="flex items-start gap-2.5 text-xs text-ink-700">
                  <XCircle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                  <div>
                    <strong className="text-nearblack font-semibold">Hallucination Risk:</strong> Proposes bars with permanently closed kitchens or non-existent vegetarian menus.
                  </div>
                </div>
              </div>
            </div>

            {/* Satisfaction mini score bar */}
            <div className="pt-4 border-t border-borderline/60 flex items-center justify-between text-xs font-mono text-rose-600 bg-rose-50/50 p-3 rounded-2xl">
              <span>Satisfaction Spread: 38%</span>
              <span className="font-bold">Unhappy Group</span>
            </div>
          </div>

          {/* Common Ground (Optimized) */}
          <div className="rounded-3xl p-6 sm:p-8 bg-gradient-to-br from-indigo-50/40 via-white to-cyan-50/30 border-2 border-brand-violet/40 shadow-float flex flex-col justify-between space-y-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-full bg-brand-violet flex items-center justify-center text-white shadow-soft">
                    <Sparkles className="w-4 h-4" />
                  </div>
                  <h4 className="text-base font-bold text-nearblack tracking-tight">
                    Common Ground Engine
                  </h4>
                </div>
                <span className="text-[10px] font-mono text-emerald-800 bg-emerald-100/80 px-2.5 py-0.5 rounded-pill border border-emerald-300 font-bold">
                  Fairness Score: 63.3% (+19.1%)
                </span>
              </div>

              <p className="text-xs sm:text-sm text-ink-500 leading-relaxed">
                Qloo Cultural AI identifies cross-domain affinities and applies mathematical fairness optimization to every hour.
              </p>

              {/* Strengths list */}
              <div className="space-y-3 pt-2">
                <div className="flex items-start gap-2.5 text-xs text-ink-700">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <div>
                    <strong className="text-nearblack font-semibold">Latent Affinity Venues:</strong> Surfaced Underdogs Gallery and Lusophonica radio coffeehouse—unexpected hits for all 4 friends.
                  </div>
                </div>
                <div className="flex items-start gap-2.5 text-xs text-ink-700">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <div>
                    <strong className="text-nearblack font-semibold">Equilibrium Guaranteed:</strong> Max satisfaction variance is just 4.8%. Nobody is left carrying taste debt.
                  </div>
                </div>
                <div className="flex items-start gap-2.5 text-xs text-ink-700">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <div>
                    <strong className="text-nearblack font-semibold">100% Grounded in Qloo:</strong> Every single place exists in Lisbon metro with verified price, category, and dietary options.
                  </div>
                </div>
              </div>
            </div>

            {/* Satisfaction mini score bar */}
            <div className="pt-4 border-t border-borderline/60 flex items-center justify-between text-xs font-mono text-emerald-800 bg-emerald-50/70 p-3 rounded-2xl">
              <span>Satisfaction Spread: 4.8%</span>
              <span className="font-bold">Total Group Harmony ✓</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

