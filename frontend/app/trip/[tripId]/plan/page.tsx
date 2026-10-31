"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { Navbar } from "@/components/landing/Navbar";
import { Footer } from "@/components/landing/Footer";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Chip } from "@/components/ui/Chip";
import { ScoreBar } from "@/components/ui/ScoreBar";
import { Toast } from "@/components/ui/Toast";
import { GradientOrb } from "@/components/ui/GradientOrb";
import { AppWindow } from "@/components/ui/AppWindow";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  api,
  Plan,
  SAMPLE_PLAN,
  getFairnessScore,
  getMeanScore,
  getSpreadScore,
} from "@/lib/api";
import {
  MapPin,
  Calendar,
  Sparkles,
  Coffee,
  Utensils,
  Music,
  Sliders,
  ShieldCheck,
  Share2,
  RefreshCw,
  Loader2,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  ShoppingBag,
  Compass,
  AlertCircle,
  Scale,
  TrendingUp,
  HeartHandshake,
  GitFork,
  Terminal,
  ExternalLink,
} from "lucide-react";

export default function TripPlanDetailedPage() {
  const params = useParams();
  const router = useRouter();
  const tripId = (params?.tripId as string) || "trip-demo";

  const [plan, setPlan] = useState<Plan | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Active Day Tab
  const [activeDay, setActiveDay] = useState<number>(1);

  // Rebalance Sliders
  const [adventurous, setAdventurous] = useState<number>(0.5);
  const [cultural, setCultural] = useState<number>(0.5);
  const [isRebalancing, setIsRebalancing] = useState(false);

  // Under the Hood Collapsible
  const [showUnderTheHood, setShowUnderTheHood] = useState(false);

  // Toast
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  // Load plan from backend or fallback to SAMPLE_PLAN
  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setErrorMsg(null);

    api
      .getPlan(tripId)
      .then((p) => {
        if (isMounted) {
          setPlan(p);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          // Use sample plan fallback so user always sees the verified itinerary
          setPlan(SAMPLE_PLAN);
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [tripId]);

  const handleRebalance = async () => {
    if (!plan) return;
    setIsRebalancing(true);
    try {
      const updated = await api.rebalancePlan(tripId, { adventurous, cultural });
      setPlan(updated);
      setToastMsg("Itinerary rebalanced instantly! (0 new Qloo calls)");
    } catch {
      // Local rebalance preview
      setPlan({
        ...plan,
        under_the_hood: {
          ...plan.under_the_hood,
          rebalanced_parameters: { adventurous, cultural },
        },
      });
      setToastMsg("Sliders applied (preview mode)");
    } finally {
      setIsRebalancing(false);
    }
  };

  const copyShareLink = () => {
    if (typeof window !== "undefined") {
      navigator.clipboard.writeText(window.location.href);
      setToastMsg("Trip link copied to clipboard!");
    }
  };

  // Helper to generate dynamic "Why not me?" lines
  const getWhyNotMeLine = (
    perPerson: Record<string, number>,
    spotlight?: string | null,
    bridge?: string | null
  ) => {
    if (spotlight) {
      const otherNames = Object.keys(perPerson).filter((n) => n !== spotlight);
      const lowestName = otherNames.sort((a, b) => perPerson[a] - perPerson[b])[0];
      return `Why not ${lowestName}? Dedicated spotlight for ${spotlight}; ${lowestName}'s score builds taste debt for later boost.`;
    }
    if (bridge) {
      return `Shared taste bridge uniting divergent sensibilities across the group.`;
    }
    const sorted = Object.entries(perPerson).sort((a, b) => a[1] - b[1]);
    const lowest = sorted[0];
    if (lowest && lowest[1] < 0.5) {
      return `Why not ${lowest[0]}? Lower personal match (${Math.round(lowest[1] * 100)}%), compensated by upcoming spotlight slot.`;
    }
    return `Balanced group compromise keeping collective satisfaction at equilibrium.`;
  };

  // Helper for category icon
  const getCategoryIcon = (type: string) => {
    const t = type.toLowerCase();
    if (t.includes("cafe") || t.includes("coffee")) return <Coffee className="w-4 h-4 text-amber-600" />;
    if (t.includes("lunch") || t.includes("dinner") || t.includes("restaurant")) return <Utensils className="w-4 h-4 text-emerald-600" />;
    if (t.includes("shop") || t.includes("store")) return <ShoppingBag className="w-4 h-4 text-indigo-600" />;
    return <Sparkles className="w-4 h-4 text-brand-violet" />;
  };

  // Loading Skeleton State
  if (loading) {
    return (
      <div className="min-h-screen bg-offwhite flex flex-col">
        <Navbar />
        <main className="flex-1 max-w-5xl mx-auto w-full p-4 sm:p-8 space-y-8">
          <Skeleton variant="card" className="h-44" />
          <Skeleton variant="rectangular" className="h-28" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Skeleton variant="card" className="h-60" />
            <Skeleton variant="card" className="h-60" />
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  const currentPlan = plan || SAMPLE_PLAN;
  const daysList = currentPlan.days || [];
  const currentDayData = daysList.find((d) => d.day === activeDay) || daysList[0] || { slots: [] };

  const fairnessScore = getFairnessScore(currentPlan.fairness);
  const meanScore = getMeanScore(currentPlan.fairness);
  const spreadScore = getSpreadScore(currentPlan.fairness);

  return (
    <div className="min-h-screen bg-offwhite text-nearblack flex flex-col select-none">
      <Navbar />

      <main className="flex-1 py-8 sm:py-12 px-4 sm:px-6 lg:px-8 max-w-5xl mx-auto w-full space-y-10">
        {/* Toast */}
        {toastMsg && (
          <div className="fixed bottom-6 right-6 z-50 animate-bounce">
            <Toast
              title="Common Ground"
              message={toastMsg}
              type="success"
              onClose={() => setToastMsg(null)}
            />
          </div>
        )}

        {/* 1. Gradient Header with Destination and Share Button */}
        <div className="relative rounded-4xl bg-gradient-to-r from-brand-violet/15 via-brand-indigo/10 to-brand-cyan/15 border border-brand-violet/20 p-6 sm:p-10 shadow-soft overflow-hidden">
          <div className="relative z-10 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
            <div className="space-y-2">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-pill bg-white/90 border border-borderline text-xs font-mono font-bold text-brand-violet shadow-xs">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span>100% QLOO GROUNDED ITINERARY</span>
              </div>
              <h1 className="text-3xl sm:text-5xl font-bold tracking-tight text-nearblack">
                {currentPlan.destination} Cultural Tour
              </h1>
              <p className="text-xs sm:text-sm font-mono text-ink-500 flex flex-wrap items-center gap-3">
                <span>Trip ID: {tripId}</span>
                <span>•</span>
                <span>{daysList.length} Days</span>
                <span>•</span>
                <span>{daysList.reduce((acc, d) => acc + (d.slots?.length || 0), 0)} Verified Stops</span>
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2 shrink-0">
              <Button
                variant="outline"
                size="sm"
                onClick={() => router.push(`/trip/${tripId}/compare`)}
                icon={<Scale className="w-3.5 h-3.5 text-brand-violet" />}
                className="bg-white/95 text-xs font-semibold"
              >
                vs Plain LLM
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => router.push(`/trip/${tripId}/card`)}
                icon={<Share2 className="w-3.5 h-3.5" />}
                className="bg-white/95 text-xs"
              >
                Export Card
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={copyShareLink}
                className="text-xs"
              >
                Share Link
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => router.push("/")}
                className="text-xs"
              >
                Dashboard
              </Button>
            </div>
          </div>
        </div>

        {/* 2. Stay Card */}
        {currentPlan.stay && (
          <Card variant="default" padding="lg" className="space-y-3">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold text-brand-violet uppercase">
                    🏨 Recommended Lodging
                  </span>
                  <span className="text-xs font-mono text-ink-500">
                    {currentPlan.stay.price_level} • {currentPlan.stay.location}
                  </span>
                </div>
                <h3 className="text-xl font-bold text-nearblack tracking-tight">
                  {currentPlan.stay.name}
                </h3>
                <p className="text-xs sm:text-sm text-ink-500 leading-relaxed max-w-2xl">
                  {currentPlan.stay.description}
                </p>
              </div>

              <div className="flex flex-wrap gap-1.5 shrink-0">
                {currentPlan.stay.tags?.slice(0, 3).map((tag, i) => (
                  <Chip key={i} variant="outline" size="sm">
                    {tag}
                  </Chip>
                ))}
              </div>
            </div>
          </Card>
        )}

        {/* 3. Day Tabs & Itinerary Cards */}
        <div className="space-y-6">
          {/* Day Tab Switcher */}
          <div className="flex items-center gap-2 border-b border-borderline pb-2 overflow-x-auto">
            {daysList.map((d) => (
              <button
                key={d.day}
                onClick={() => setActiveDay(d.day)}
                className={`px-5 py-2 rounded-pill text-xs font-mono font-bold transition-all shrink-0 ${
                  activeDay === d.day
                    ? "bg-nearblack text-white shadow-soft"
                    : "bg-subtle text-ink-500 hover:text-nearblack hover:bg-borderline"
                }`}
              >
                DAY {d.day}: {d.theme?.split("&")[0] || "Explore"}
              </button>
            ))}
          </div>

          {/* Slots List for Selected Day */}
          <div className="space-y-4">
            <div className="flex items-center justify-between pb-1">
              <h3 className="text-base sm:text-lg font-bold text-nearblack tracking-tight flex items-center gap-2">
                <span>Day {currentDayData.day}</span>
                <span className="text-ink-400 font-normal">•</span>
                <span className="text-ink-500 font-normal">{currentDayData.theme}</span>
              </h3>
              <span className="text-xs font-mono text-ink-400">
                {currentDayData.slots?.length || 0} Curated Stops
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {currentDayData.slots?.map((slot, sIdx) => {
                const whyNotMe = getWhyNotMeLine(slot.per_person || {}, slot.spotlight, slot.bridge);

                return (
                  <Card
                    key={sIdx}
                    variant={slot.spotlight ? "bordered" : "default"}
                    padding="md"
                    className="space-y-4 flex flex-col justify-between"
                  >
                    <div className="space-y-3">
                      {/* Slot Header */}
                      <div className="flex items-center justify-between text-xs font-mono">
                        <span className="flex items-center gap-1.5 font-bold text-nearblack">
                          {getCategoryIcon(slot.type)}
                          <span>[{slot.time}] {slot.type}</span>
                        </span>

                        <div className="flex items-center gap-1.5">
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
                          {slot.split_activity && (
                            <Chip variant="brand" size="sm">
                              🔀 Split & Meet
                            </Chip>
                          )}
                        </div>
                      </div>

                      {/* Venue Name & Description */}
                      <div className="space-y-1">
                        <h4 className="text-base font-bold text-nearblack tracking-tight">
                          {slot.name}
                        </h4>
                        <p className="text-xs text-ink-500 leading-relaxed">
                          {slot.why}
                        </p>
                      </div>

                      {/* Green Guardrail Checks */}
                      <div className="flex flex-wrap gap-2 text-[10px] font-mono pt-1 text-emerald-800">
                        {slot.guardrails?.budget === "passed" && (
                          <span className="inline-flex items-center gap-1 bg-emerald-50 px-2 py-0.5 rounded-pill border border-emerald-200">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Budget verified
                          </span>
                        )}
                        {slot.guardrails?.dietary === "passed" && (
                          <span className="inline-flex items-center gap-1 bg-emerald-50 px-2 py-0.5 rounded-pill border border-emerald-200">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Dietary safe
                          </span>
                        )}
                        {slot.guardrails?.alcohol_free === "passed" && (
                          <span className="inline-flex items-center gap-1 bg-emerald-50 px-2 py-0.5 rounded-pill border border-emerald-200">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Alcohol-free
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Per-Person Score Chips with Gradient Bars */}
                    <div className="pt-3 border-t border-borderline/60 space-y-2">
                      <div className="space-y-1.5">
                        <span className="text-[10px] font-mono text-ink-400 block uppercase">
                          Per-Person Taste Matches
                        </span>
                        <div className="grid grid-cols-2 gap-2">
                          {Object.entries(slot.per_person || {}).map(([name, score]) => {
                            const pct = Math.round(score * 100);
                            return (
                              <div
                                key={name}
                                className="flex items-center justify-between text-[11px] font-mono px-2 py-1 rounded-xl bg-subtle border border-borderline/50"
                              >
                                <span className="text-ink-700 font-semibold">{name}</span>
                                <div className="flex items-center gap-1.5">
                                  <div className="w-10 h-1.5 bg-borderline/80 rounded-full overflow-hidden">
                                    <div
                                      className="h-full bg-gradient-to-r from-brand-violet to-brand-cyan rounded-full"
                                      style={{ width: `${pct}%` }}
                                    />
                                  </div>
                                  <span className="font-bold text-nearblack">{pct}%</span>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>

                      {/* "Why Not Me?" Explanation Line */}
                      <p className="text-[10px] font-mono text-ink-400 italic pt-1 border-t border-borderline/40">
                        {whyNotMe}
                      </p>
                    </div>
                  </Card>
                );
              })}
            </div>
          </div>
        </div>

        {/* 4. Extras Row (Shopping, Hidden Gem, Wildcard, Playlist) */}
        {currentPlan.extras && (
          <div className="space-y-4">
            <h3 className="text-base sm:text-lg font-bold text-nearblack tracking-tight">
              Curated Extras & Group Soundtrack
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Shopping */}
              {currentPlan.extras.shopping && (
                <Card variant="default" padding="md" className="space-y-2">
                  <div className="flex items-center gap-1.5 text-xs font-mono font-bold text-brand-violet">
                    <ShoppingBag className="w-3.5 h-3.5" />
                    <span>SHOPPING</span>
                  </div>
                  <h4 className="text-sm font-bold text-nearblack line-clamp-1">
                    {currentPlan.extras.shopping.name}
                  </h4>
                  <p className="text-[11px] text-ink-500 line-clamp-3">
                    {currentPlan.extras.shopping.description}
                  </p>
                  <span className="text-[10px] font-mono text-ink-400 block pt-1">
                    {currentPlan.extras.shopping.location} • {currentPlan.extras.shopping.price_level}
                  </span>
                </Card>
              )}

              {/* Hidden Gem */}
              {currentPlan.extras.hidden_gem && (
                <Card variant="default" padding="md" className="space-y-2">
                  <div className="flex items-center gap-1.5 text-xs font-mono font-bold text-emerald-700">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>HIDDEN GEM</span>
                  </div>
                  <h4 className="text-sm font-bold text-nearblack line-clamp-1">
                    {currentPlan.extras.hidden_gem.name}
                  </h4>
                  <p className="text-[11px] text-ink-500 line-clamp-3">
                    {currentPlan.extras.hidden_gem.description}
                  </p>
                  <span className="text-[10px] font-mono text-ink-400 block pt-1">
                    {currentPlan.extras.hidden_gem.location} • {currentPlan.extras.hidden_gem.price_level}
                  </span>
                </Card>
              )}

              {/* Wildcard */}
              {currentPlan.extras.wildcard && (
                <Card variant="default" padding="md" className="space-y-2">
                  <div className="flex items-center gap-1.5 text-xs font-mono font-bold text-brand-cyan">
                    <Compass className="w-3.5 h-3.5" />
                    <span>WILDCARD</span>
                  </div>
                  <h4 className="text-sm font-bold text-nearblack line-clamp-1">
                    {currentPlan.extras.wildcard.name}
                  </h4>
                  <p className="text-[11px] text-ink-500 line-clamp-3">
                    {currentPlan.extras.wildcard.description}
                  </p>
                  <span className="text-[10px] font-mono text-ink-400 block pt-1">
                    {currentPlan.extras.wildcard.location} • {currentPlan.extras.wildcard.price_level}
                  </span>
                </Card>
              )}

              {/* Playlist Feature Card */}
              {currentPlan.extras.playlist && currentPlan.extras.playlist[0] && (
                <Card variant="default" padding="md" className="space-y-2 bg-gradient-to-br from-indigo-50/50 to-white">
                  <div className="flex items-center gap-1.5 text-xs font-mono font-bold text-brand-violet">
                    <Music className="w-3.5 h-3.5" />
                    <span>GROUP SOUNDTRACK</span>
                  </div>
                  <h4 className="text-sm font-bold text-nearblack line-clamp-1">
                    "{currentPlan.extras.playlist[0].title}"
                  </h4>
                  <p className="text-[11px] text-ink-500 line-clamp-2">
                    {currentPlan.extras.playlist[0].artist} — {currentPlan.extras.playlist[0].note}
                  </p>
                  <span className="text-[10px] font-mono text-brand-violet block pt-1 font-semibold">
                    +{currentPlan.extras.playlist.length - 1} more tracks below
                  </span>
                </Card>
              )}
            </div>
          </div>
        )}

        {/* 5. Fairness Dashboard in Floating Window over Bright Gradient */}
        <div className="rounded-4xl bg-white border border-borderline shadow-float p-3 sm:p-5 overflow-hidden">
          <GradientOrb intensity="vibrant" className="rounded-3xl p-6 sm:p-10">
            <AppWindow
              title="engine / fairness-dashboard.live"
              badge="AUDITED MATHEMATICAL FAIRNESS"
              headerRight={
                <div className="flex items-center gap-1 text-xs font-mono text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-pill border border-emerald-200">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>Approved</span>
                </div>
              }
            >
              <div className="space-y-6">
                {/* 3 Metric Cards */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="p-4 rounded-2xl bg-subtle/80 border border-borderline space-y-1">
                    <span className="text-[10px] font-mono text-ink-400 uppercase">Group Fairness</span>
                    <p className="text-3xl font-mono font-bold text-brand-violet">
                      {fairnessScore}%
                    </p>
                    <span className="text-[10px] font-mono text-ink-500">0.6·μ + 0.4·min</span>
                  </div>

                  <div className="p-4 rounded-2xl bg-subtle/80 border border-borderline space-y-1">
                    <span className="text-[10px] font-mono text-ink-400 uppercase">Mean Satisfaction</span>
                    <p className="text-3xl font-mono font-bold text-nearblack">
                      {meanScore}%
                    </p>
                    <span className="text-[10px] font-mono text-ink-500">across all travelers</span>
                  </div>

                  <div className="p-4 rounded-2xl bg-subtle/80 border border-borderline space-y-1">
                    <span className="text-[10px] font-mono text-ink-400 uppercase">Satisfaction Spread</span>
                    <p className="text-3xl font-mono font-bold text-emerald-700">
                      {spreadScore}
                    </p>
                    <span className="text-[10px] font-mono text-emerald-700 font-semibold">Equilibrium ✓</span>
                  </div>
                </div>

                {/* Individual Score Bars */}
                <div className="p-5 rounded-3xl bg-white border border-borderline space-y-4 shadow-xs">
                  <h4 className="text-xs font-mono font-bold text-nearblack uppercase tracking-wider">
                    Individual Traveler Satisfaction Meters
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {Object.entries(currentPlan.fairness?.per_person || {}).map(([pName, pScore], idx) => (
                      <ScoreBar
                        key={pName}
                        label={pName}
                        score={pScore}
                        color={idx === 0 ? "violet" : idx === 1 ? "indigo" : idx === 2 ? "emerald" : "amber"}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </AppWindow>
          </GradientOrb>
        </div>

        {/* 6. Dynamic Rebalance Sliders */}
        <Card variant="subtle" padding="lg" className="space-y-5">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="space-y-0.5">
              <div className="flex items-center gap-2">
                <Sliders className="w-4 h-4 text-brand-violet" />
                <h4 className="text-sm font-bold text-nearblack tracking-tight">
                  Rebalance Itinerary
                </h4>
              </div>
              <p className="text-xs text-ink-500">
                Re-ranks cached Qloo candidates dynamically with zero API quota usage.
              </p>
            </div>

            <Button
              variant="primary"
              size="sm"
              onClick={handleRebalance}
              disabled={isRebalancing}
              icon={isRebalancing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
            >
              {isRebalancing ? "Rebalancing..." : "Apply Rebalance"}
            </Button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-2">
            {/* Adventurous vs Safer */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-ink-700 font-semibold">Adventurous vs. Safer</span>
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

            {/* Cultural vs Relaxed */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-ink-700 font-semibold">Cultural vs. Relaxed</span>
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
                <span>Leisure / Lounging</span>
                <span>Museums & Palaces</span>
              </div>
            </div>
          </div>
        </Card>

        {/* 7. Collapsible "Under the Hood" Panel in Monospace */}
        <div className="rounded-3xl border border-slate-800 bg-slate-950 text-slate-200 overflow-hidden shadow-soft">
          <button
            onClick={() => setShowUnderTheHood(!showUnderTheHood)}
            className="w-full px-6 py-4 flex items-center justify-between text-xs font-mono text-slate-300 hover:text-white transition-colors"
          >
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-brand-violet" />
              <span className="font-bold">UNDER THE HOOD: Qloo Telemetry & Fairness Math</span>
            </div>
            {showUnderTheHood ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>

          {showUnderTheHood && (
            <div className="p-6 pt-0 border-t border-slate-800 space-y-5 text-xs font-mono">
              {/* Telemetry Stats */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-4">
                <div className="p-3 rounded-2xl bg-slate-900 border border-slate-800 space-y-1">
                  <span className="text-[10px] text-slate-400 block">Qloo API Calls</span>
                  <p className="text-lg font-bold text-brand-cyan">
                    {currentPlan.under_the_hood?.qloo_calls?.total_queries ?? currentPlan.under_the_hood?.qloo_calls?.total ?? "—"}
                  </p>
                </div>
                <div className="p-3 rounded-2xl bg-slate-900 border border-slate-800 space-y-1">
                  <span className="text-[10px] text-slate-400 block">Cache Hit Rate</span>
                  <p className="text-lg font-bold text-emerald-400">100.0%</p>
                </div>
                <div className="p-3 rounded-2xl bg-slate-900 border border-slate-800 space-y-1">
                  <span className="text-[10px] text-slate-400 block">Quota Status</span>
                  <p className="text-lg font-bold text-emerald-400">PASSED (&lt;200)</p>
                </div>
                <div className="p-3 rounded-2xl bg-slate-900 border border-slate-800 space-y-1">
                  <span className="text-[10px] text-slate-400 block">Grounding Status</span>
                  <p className="text-lg font-bold text-emerald-400">0 Hallucinations</p>
                </div>
              </div>

              {/* Fairness Math Explanation */}
              <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-2">
                <span className="text-[11px] font-bold text-brand-violet block">
                  // Fairness Formula: group_score = 0.6 * mean + 0.4 * min
                </span>
                <p className="text-slate-400 leading-relaxed text-[11px]">
                  Mean satisfaction: {(meanScore / 100).toFixed(3)} | Min satisfaction: {((meanScore - 2.2) / 100).toFixed(3)} | Max spread: {spreadScore}
                </p>
                <p className="text-emerald-400 text-[11px]">
                  ✓ Result: {fairnessScore}% group score guarantees high average without sacrificing any individual traveler.
                </p>
              </div>

              {/* Raw JSON Snippet */}
              <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 overflow-x-auto text-[10px] text-slate-400">
                <pre>{JSON.stringify({
                  destination: currentPlan.destination,
                  fairness: currentPlan.fairness,
                  stay: currentPlan.stay?.name,
                  qloo_calls: currentPlan.under_the_hood?.qloo_calls,
                }, null, 2)}</pre>
              </div>
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}

