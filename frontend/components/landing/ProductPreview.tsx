import React from "react";
import { GradientOrb } from "@/components/ui/GradientOrb";
import { AppWindow } from "@/components/ui/AppWindow";
import { Chip } from "@/components/ui/Chip";
import { Sparkles, MapPin, Coffee, Utensils, Compass, Music } from "lucide-react";

export const ProductPreview: React.FC = () => {
  return (
    <section className="relative px-4 sm:px-6 lg:px-8 pb-20">
      <div className="max-w-7xl mx-auto">
        {/* Large Rounded Card Container */}
        <div className="relative rounded-4xl bg-white border border-borderline/80 p-3 sm:p-5 shadow-float overflow-hidden">
          {/* Blurred Multicolor Gradients strictly inside product visual container */}
          <GradientOrb intensity="soft" className="rounded-3xl p-6 sm:p-10 lg:p-12">
            {/* Top Product Showcase Bar */}
            <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-white/90 backdrop-blur border border-borderline/80 flex items-center justify-center text-nearblack shadow-xs">
                  <MapPin className="w-4 h-4 text-brand-violet" />
                </div>
                <div>
                  <h3 className="text-base sm:text-lg font-bold text-nearblack tracking-tight">
                    Lisbon Cultural Equilibrium
                  </h3>
                  <p className="text-xs text-ink-500 font-mono">
                    2 Days • 4 Friends • 12 Verified Stops
                  </p>
                </div>
              </div>

              {/* Overall Group Health Metric */}
              <div className="flex items-center gap-2 bg-white/90 backdrop-blur px-4 py-2 rounded-pill border border-borderline/80 shadow-xs">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="text-xs font-mono font-medium text-ink-700">
                  Group Fairness: <span className="font-bold text-nearblack">63.3%</span>
                </span>
                <span className="text-[10px] font-mono text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-pill border border-emerald-200">
                  Spread 4.8%
                </span>
              </div>
            </div>

            {/* Inner App Window Preview */}
            <div className="relative">
              {/* Floating Chip 1: Aisha's Spotlight (Top Left) */}
              <div className="hidden md:flex absolute -top-4 -left-3 z-20 animate-float-slow">
                <div className="bg-white/95 backdrop-blur-md px-3.5 py-2 rounded-2xl border border-amber-200/80 shadow-soft flex items-center gap-2.5">
                  <span className="w-7 h-7 rounded-full bg-amber-100 flex items-center justify-center text-xs font-bold text-amber-800">
                    A
                  </span>
                  <div>
                    <div className="text-[11px] font-bold text-nearblack tracking-tight flex items-center gap-1">
                      ★ Aisha's Spotlight
                    </div>
                    <div className="text-[10px] font-mono text-ink-500">
                      Underdogs Gallery • 95% Match
                    </div>
                  </div>
                </div>
              </div>

              {/* Floating Chip 2: Meera's Spotlight (Top Right) */}
              <div className="hidden md:flex absolute -top-3 -right-2 z-20 animate-float-delayed">
                <div className="bg-white/95 backdrop-blur-md px-3.5 py-2 rounded-2xl border border-amber-200/80 shadow-soft flex items-center gap-2.5">
                  <span className="w-7 h-7 rounded-full bg-amber-100 flex items-center justify-center text-xs font-bold text-amber-800">
                    M
                  </span>
                  <div>
                    <div className="text-[11px] font-bold text-nearblack tracking-tight">
                      ★ Meera's Spotlight
                    </div>
                    <div className="text-[10px] font-mono text-ink-500">
                      Church of Saint Mary • 95% Match
                    </div>
                  </div>
                </div>
              </div>

              {/* Floating Chip 3: Taste Bridge (Bottom Right) */}
              <div className="hidden lg:flex absolute -bottom-5 right-8 z-20 animate-float-slow">
                <div className="bg-white/95 backdrop-blur-md px-4 py-2.5 rounded-2xl border border-cyan-200/80 shadow-float flex items-center gap-2.5">
                  <span className="text-base">🌉</span>
                  <div>
                    <div className="text-[11px] font-bold text-cyan-950 tracking-tight">
                      Taste Bridge: Aisha & Meera
                    </div>
                    <div className="text-[10px] font-mono text-ink-500">
                      Quinta da Regaleira • Balances 88% & 54%
                    </div>
                  </div>
                </div>
              </div>

              {/* Central Itinerary App Window */}
              <AppWindow
                title="commonground-plan / lisbon-2days.json"
                badge="100% QLOO GROUNDED"
                className="w-full"
              >
                <div className="space-y-6">
                  {/* Hotel Stay Banner */}
                  <div className="rounded-2xl bg-subtle/80 border border-borderline/80 p-4 sm:p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-bold text-brand-violet uppercase tracking-wider">
                          🏨 Lodging
                        </span>
                        <span className="text-xs font-mono px-2 py-0.5 rounded-pill bg-white border border-borderline text-ink-500">
                          $$ • Sé Quarters
                        </span>
                      </div>
                      <h4 className="text-base font-bold text-nearblack tracking-tight">
                        The Lisboans Apartments
                      </h4>
                      <p className="text-xs text-ink-500 max-w-xl">
                        Restored 19th-century factory with vintage furniture, local farm breakfast, and walking distance to Alfama.
                      </p>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <Chip variant="outline" size="sm">Central</Chip>
                      <Chip variant="outline" size="sm">Boutique</Chip>
                    </div>
                  </div>

                  {/* Day 1 Slots Sample Grid */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between pb-1 border-b border-borderline/40">
                      <span className="text-xs font-mono font-bold text-ink-700 tracking-tight">
                        DAY 1 • HISTORIC QUARTERS & CULTURE
                      </span>
                      <span className="text-[11px] font-mono text-ink-400">
                        6 Stops Scheduled
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      {/* Slot 1: Cafe */}
                      <div className="rounded-2xl bg-white border border-borderline/70 p-4 space-y-2 shadow-xs">
                        <div className="flex items-center justify-between text-[11px] font-mono text-ink-400">
                          <span className="flex items-center gap-1 font-semibold text-nearblack">
                            <Coffee className="w-3.5 h-3.5 text-amber-600" /> 09:00 Cafe
                          </span>
                          <span>Budget: $</span>
                        </div>
                        <h5 className="text-xs font-bold text-nearblack line-clamp-1">
                          Lusophonica - Farol De Santa Marta
                        </h5>
                        <p className="text-[11px] text-ink-500 line-clamp-2">
                          Lighthouse coffeehouse & online radio playing experimental global beats.
                        </p>
                        <div className="pt-1.5 flex items-center justify-between text-[10px] font-mono border-t border-borderline/30 text-ink-500">
                          <span>A: 95%</span>
                          <span>R: 46%</span>
                          <span>M: 57%</span>
                          <span>K: 55%</span>
                        </div>
                      </div>

                      {/* Slot 2: Spotlight */}
                      <div className="rounded-2xl bg-white border-2 border-amber-300/60 p-4 space-y-2 shadow-xs relative">
                        <div className="flex items-center justify-between text-[11px] font-mono">
                          <span className="flex items-center gap-1 font-bold text-amber-900">
                            <Sparkles className="w-3.5 h-3.5 text-amber-600" /> 11:30 Spotlight
                          </span>
                          <span className="text-[10px] font-bold text-amber-800 bg-amber-50 px-1.5 py-0.5 rounded-pill">
                            Aisha
                          </span>
                        </div>
                        <h5 className="text-xs font-bold text-nearblack line-clamp-1">
                          Underdogs Contemporary Gallery
                        </h5>
                        <p className="text-[11px] text-ink-500 line-clamp-2">
                          Lisbon public art space & limited edition print shop in Marvila.
                        </p>
                        <div className="pt-1.5 flex items-center justify-between text-[10px] font-mono border-t border-borderline/30 text-ink-500 font-semibold">
                          <span className="text-amber-700">A: 95%</span>
                          <span>R: 46%</span>
                          <span>M: 51%</span>
                          <span>K: 62%</span>
                        </div>
                      </div>

                      {/* Slot 3: Restaurant */}
                      <div className="rounded-2xl bg-white border border-borderline/70 p-4 space-y-2 shadow-xs">
                        <div className="flex items-center justify-between text-[11px] font-mono text-ink-400">
                          <span className="flex items-center gap-1 font-semibold text-nearblack">
                            <Utensils className="w-3.5 h-3.5 text-emerald-600" /> 13:30 Lunch
                          </span>
                          <span className="text-emerald-700 font-semibold">Veg Safe ✓</span>
                        </div>
                        <h5 className="text-xs font-bold text-nearblack line-clamp-1">
                          Os Amigos Da Severa
                        </h5>
                        <p className="text-[11px] text-ink-500 line-clamp-2">
                          Heritage tavern serving classic petiscos with warm communal tables.
                        </p>
                        <div className="pt-1.5 flex items-center justify-between text-[10px] font-mono border-t border-borderline/30 text-ink-500">
                          <span>A: 82%</span>
                          <span>R: 42%</span>
                          <span>M: 92%</span>
                          <span>K: 82%</span>
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

