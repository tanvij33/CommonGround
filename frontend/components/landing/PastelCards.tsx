import React from "react";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Card } from "@/components/ui/Card";
import { AlertTriangle, Sparkles, TrendingUp, Compass, HeartHandshake } from "lucide-react";

export const PastelCards: React.FC = () => {
  return (
    <section id="taste-graph" className="py-20 sm:py-28 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-12">
        <SectionHeader
          kicker="THE TASTE GRAPH"
          title="Many tastes, one shared taste graph"
          description="How cross-domain cultural intelligence turns personal taste divergence into shared excitement."
        />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 lg:gap-8">
          {/* Card 1: The Zero-Sum Trap (Pastel Warm / Rose-Amber) */}
          <div className="rounded-3xl p-8 sm:p-10 bg-gradient-to-br from-rose-50/90 via-amber-50/50 to-white border border-rose-200/60 shadow-soft space-y-6">
            <div className="w-10 h-10 rounded-2xl bg-white border border-rose-200 flex items-center justify-center text-rose-600 shadow-xs">
              <AlertTriangle className="w-5 h-5" />
            </div>

            <div className="space-y-2">
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-rose-700">
                The Conventional Trap
              </span>
              <h3 className="text-2xl sm:text-3xl font-bold text-nearblack tracking-tight leading-tight">
                The zero-sum compromise of group itineraries
              </h3>
            </div>

            <p className="text-sm sm:text-base text-ink-700 leading-relaxed">
              When friends try to plan together, one of two things happens: the most opinionated person dictates the whole trip, or the group retreats to generic, overcrowded tourist hubs that nobody truly enjoys.
            </p>

            <div className="space-y-3 pt-2 text-xs font-mono text-ink-500">
              <div className="flex items-center gap-2">
                <span className="text-rose-500 font-bold">✕</span>
                <span>The "loudest planner" syndrome leaves quiet friends dissatisfied</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-rose-500 font-bold">✕</span>
                <span>Generic tourist spots (Time Out Market, Tram 28) cause taste fatigue</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-rose-500 font-bold">✕</span>
                <span>Unbalanced compromises create silent resentment across the group</span>
              </div>
            </div>
          </div>

          {/* Card 2: The Cultural Affinity Solution (Pastel Cool / Violet-Cyan) */}
          <div className="rounded-3xl p-8 sm:p-10 bg-gradient-to-br from-indigo-50/90 via-cyan-50/50 to-white border border-indigo-200/60 shadow-soft space-y-6">
            <div className="w-10 h-10 rounded-2xl bg-white border border-indigo-200 flex items-center justify-center text-brand-violet shadow-xs">
              <Sparkles className="w-5 h-5" />
            </div>

            <div className="space-y-2">
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-brand-indigo">
                The Common Ground Way
              </span>
              <h3 className="text-2xl sm:text-3xl font-bold text-nearblack tracking-tight leading-tight">
                Cross-domain intelligence predicts delight
              </h3>
            </div>

            <p className="text-sm sm:text-base text-ink-700 leading-relaxed">
              Qloo connects disparate cultural affinities. Knowing someone loves burial, Wes Anderson cinema, and Aesop enables our engine to find architectural cafes and intimate vinyl bars that deeply satisfy them while charming their pop-loving friends.
            </p>

            <div className="space-y-3 pt-2 text-xs font-mono text-ink-500">
              <div className="flex items-center gap-2">
                <span className="text-emerald-600 font-bold">✓</span>
                <span>Correlates music, fashion, and cinema to curate local dining & lodging</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-emerald-600 font-bold">✓</span>
                <span>Mathematical fairness formula: maximizes group mean while defending minimums</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-emerald-600 font-bold">✓</span>
                <span>Every single traveler gets personal spotlight slots they rave about</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

