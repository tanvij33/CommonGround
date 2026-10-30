import React from "react";
import { Button } from "@/components/ui/Button";
import { Sparkles, ArrowRight, Github } from "lucide-react";

export interface FinalCtaProps {
  onOpenDemo: () => void;
  onOpenCreateTrip?: () => void;
}

export const FinalCta: React.FC<FinalCtaProps> = ({ onOpenDemo, onOpenCreateTrip }) => {
  return (
    <section className="py-20 sm:py-28 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto rounded-4xl bg-nearblack text-white p-8 sm:p-14 lg:p-16 relative overflow-hidden shadow-float">
        {/* Subtle background glow */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-brand-violet/20 rounded-full blur-[100px] pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-80 h-80 bg-brand-cyan/15 rounded-full blur-[90px] pointer-events-none" />

        <div className="relative z-10 max-w-2xl space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-pill bg-white/10 border border-white/15 text-xs font-mono text-slate-300">
            <Sparkles className="w-3.5 h-3.5 text-brand-violet" />
            <span>Built for the Qloo Hackathon</span>
          </div>

          <h2 className="text-3xl sm:text-5xl font-bold tracking-tight text-white leading-tight">
            Ready to plan a trip <br />
            your whole group loves?
          </h2>

          <p className="text-sm sm:text-base text-slate-300 leading-relaxed max-w-lg">
            Connect your friends’ tastes across music, film, fashion, and dining. Let Qloo Cultural AI find your common ground.
          </p>

          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Button
              variant="gradient"
              size="lg"
              onClick={onOpenCreateTrip || onOpenDemo}
              icon={<Sparkles className="w-4 h-4" />}
            >
              Create a Trip
            </Button>
            <Button
              variant="outline"
              size="lg"
              onClick={onOpenDemo}
              className="bg-white/10 text-white border-white/20 hover:bg-white/20"
              icon={<ArrowRight className="w-4 h-4" />}
              iconPosition="right"
            >
              Launch 4-Friend Demo
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
};

