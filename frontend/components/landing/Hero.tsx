import React from "react";
import { Button } from "@/components/ui/Button";
import { ArrowRight, Sparkles, Compass } from "lucide-react";

export interface HeroProps {
  onOpenDemo: () => void;
  onOpenCreateTrip?: () => void;
  onScrollToFeatures: () => void;
}

export const Hero: React.FC<HeroProps> = ({ onOpenDemo, onOpenCreateTrip, onScrollToFeatures }) => {
  return (
    <section className="relative pt-12 pb-16 sm:pt-20 sm:pb-24 overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-14 items-start">
          {/* Main Hero Column (Left / 7 cols) */}
          <div className="lg:col-span-7 space-y-6">
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-pill bg-white border border-borderline shadow-xs">
              <span className="w-2 h-2 rounded-full bg-brand-violet animate-pulse" />
              <span className="text-xs font-mono font-medium text-ink-700 tracking-tight">
                Powered by Qloo Cultural AI
              </span>
            </div>

            <h1 className="text-4xl sm:text-6xl lg:text-[4.25rem] font-bold text-nearblack tracking-tight leading-[1.06]">
              Everyone’s taste. <br />
              <span className="text-brand-violet">One trip.</span>
            </h1>

            <p className="text-lg sm:text-xl text-ink-500 font-normal leading-relaxed max-w-xl tracking-tight">
              A taste-fair group travel planner that maps everyone’s distinct cultural tastes—music, cinema, fashion, and dining—into unforgettable itineraries with zero taste debt.
            </p>

            {/* Two Pill CTAs */}
            <div className="flex flex-wrap items-center gap-3 pt-2">
              <Button
                variant="primary"
                size="lg"
                onClick={onOpenCreateTrip || onOpenDemo}
                icon={<Sparkles className="w-4 h-4 text-brand-violet" />}
              >
                Create a Trip
              </Button>
              <Button
                variant="outline"
                size="lg"
                onClick={onOpenDemo}
                icon={<ArrowRight className="w-4 h-4" />}
                iconPosition="right"
              >
                Launch 4-Friend Demo
              </Button>
            </div>
          </div>

          {/* Small Editorial Text Block (Right / 5 cols) */}
          <div className="lg:col-span-5 lg:pt-8">
            <div className="rounded-3xl bg-white/70 backdrop-blur-sm border border-borderline/80 p-7 sm:p-8 space-y-4 shadow-soft">
              <div className="flex items-center gap-2 text-xs font-mono text-ink-400 uppercase tracking-wider">
                <Compass className="w-3.5 h-3.5 text-brand-violet" />
                <span>The Cultural Equilibrium</span>
              </div>
              <p className="text-sm sm:text-base text-ink-700 leading-relaxed tracking-tight">
                When ambient electronic listeners travel with stadium pop fans, traditional planners either surrender to the loudest voice or compromise everyone into sterile mediocrity.
              </p>
              <p className="text-xs sm:text-sm text-ink-500 leading-relaxed tracking-tight pt-1 border-t border-borderline/50">
                Common Ground queries Qloo’s 575M+ entity taste graph to surface shared latent affinities, assigning dedicated spotlight slots and shared bridges where everyone wins.
              </p>
              <div className="flex items-center gap-4 pt-2 text-xs font-mono text-ink-500">
                <div><span className="font-bold text-nearblack">4</span> Friends</div>
                <div>•</div>
                <div><span className="font-bold text-nearblack">4.8%</span> Max Variance</div>
                <div>•</div>
                <div><span className="font-bold text-nearblack">100%</span> Grounded</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

