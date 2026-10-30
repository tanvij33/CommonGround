import React from "react";
import { Music, Film, ShoppingBag, UtensilsCrossed, Landmark, Sparkles } from "lucide-react";

export const TasteGraphStrip: React.FC = () => {
  const domains = [
    { label: "Music & Artists", icon: <Music className="w-3.5 h-3.5" /> },
    { label: "Cinema & Television", icon: <Film className="w-3.5 h-3.5" /> },
    { label: "Fashion & Brands", icon: <ShoppingBag className="w-3.5 h-3.5" /> },
    { label: "Culinary & Dining", icon: <UtensilsCrossed className="w-3.5 h-3.5" /> },
    { label: "Architecture & Culture", icon: <Landmark className="w-3.5 h-3.5" /> },
  ];

  return (
    <section className="border-y border-borderline/60 bg-white/70 backdrop-blur-sm py-4 select-none">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-xs font-mono text-ink-500 shrink-0">
          <Sparkles className="w-3.5 h-3.5 text-brand-violet" />
          <span className="font-semibold text-nearblack">Qloo Taste Graph:</span>
          <span>575M+ verified cultural entities</span>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-2 sm:gap-4">
          {domains.map((d, i) => (
            <div
              key={i}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-pill bg-subtle/80 text-[11px] font-medium text-ink-700 border border-borderline/50"
            >
              <span className="text-brand-violet">{d.icon}</span>
              <span>{d.label}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

