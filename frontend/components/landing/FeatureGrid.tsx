import React from "react";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Card } from "@/components/ui/Card";
import { Scale, HeartHandshake, Sparkles, TrendingUp, ShieldAlert, GitFork } from "lucide-react";

export const FeatureGrid: React.FC = () => {
  const features = [
    {
      icon: <Scale className="w-5 h-5 text-brand-violet" />,
      title: "Fairness Scoring",
      badge: "0.6·μ + 0.4·min",
      description:
        "Guarantees that the group's overall average never comes at the expense of an ignored traveler. Mathematically defends the lowest personal score.",
    },
    {
      icon: <HeartHandshake className="w-5 h-5 text-brand-cyan" />,
      title: "Taste Bridges",
      badge: "Cross-Pollination",
      description:
        "Identifies the two most divergent friends in the group and finds venues that score high for both, creating shared memories out of opposing tastes.",
    },
    {
      icon: <Sparkles className="w-5 h-5 text-brand-amber" />,
      title: "Spotlight Slots",
      badge: "Guaranteed ★",
      description:
        "Every single friend is guaranteed dedicated slots matching their absolute top cultural taste signals (art galleries, vinyl stores, or iconic landmarks).",
    },
    {
      icon: <TrendingUp className="w-5 h-5 text-brand-emerald" />,
      title: "Taste Debt Balancing",
      badge: "Dynamic Compensation",
      description:
        "Tracks cumulative satisfaction throughout the day. Whoever makes a compromise in the morning is automatically prioritized for afternoon and evening slots.",
    },
    {
      icon: <ShieldAlert className="w-5 h-5 text-brand-rose" />,
      title: "Hard Guardrails",
      badge: "100% Verified",
      description:
        "Strictly enforces dietary needs (vegetarian/vegan), alcohol-free requirements, wheelchair accessibility, and price-bracket ceilings ($$).",
    },
    {
      icon: <GitFork className="w-5 h-5 text-brand-indigo" />,
      title: "Split-and-Meet Tracks",
      badge: "Parallel Tracks",
      description:
        "For hours where taste divergence is extreme, the engine designs parallel walking tracks before orchestrating a reunion at a shared bridge restaurant.",
    },
  ];

  return (
    <section id="features" className="py-20 sm:py-28 px-4 sm:px-6 lg:px-8 bg-subtle/50 border-y border-borderline/50">
      <div className="max-w-7xl mx-auto space-y-12">
        <SectionHeader
          kicker="ALGORITHMIC INNOVATIONS"
          title="Engineered for group harmony"
          description="Six algorithmic breakthroughs solving the classical problems of multi-person travel planning."
        />

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((f, i) => (
            <Card
              key={i}
              variant="default"
              padding="lg"
              className="space-y-4 hover:border-brand-violet/40 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="w-10 h-10 rounded-2xl bg-subtle border border-borderline flex items-center justify-center shadow-xs">
                  {f.icon}
                </div>
                <span className="text-[10px] font-mono font-bold text-ink-500 bg-subtle px-2.5 py-0.5 rounded-pill border border-borderline/60">
                  {f.badge}
                </span>
              </div>

              <div className="space-y-1.5">
                <h4 className="text-lg font-bold text-nearblack tracking-tight">
                  {f.title}
                </h4>
                <p className="text-xs sm:text-sm text-ink-500 leading-relaxed">
                  {f.description}
                </p>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
};

