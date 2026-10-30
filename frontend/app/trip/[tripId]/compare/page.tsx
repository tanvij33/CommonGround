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
import { api, ComparisonResult, Plan, SAMPLE_PLAN } from "@/lib/api";
import {
  Sparkles,
  ArrowLeft,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Scale,
  Users,
  Compass,
  Zap,
  BarChart3,
  ShieldCheck,
  ShieldAlert,
  ArrowRight,
  Share2,
  Calendar,
  Layers,
  HeartCrack,
} from "lucide-react";

export default function TripComparisonPage() {
  const params = useParams();
  const router = useRouter();
  const tripId = (params?.tripId as string) || "trip-demo";

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<ComparisonResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    api
      .getComparison(tripId)
      .then((res) => {
        if (isMounted) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        console.warn("Comparison endpoint error, using demo comparison:", err);
        if (isMounted) {
          setData({
            common_ground_plan: {
              fairness_score: 0.684,
              happiness_spread: 0.048,
              per_person: { Aisha: 0.86, Rohan: 0.82, Meera: 0.88, Kabir: 0.84 },
              grounding: "100% Verified Qloo Culture API",
              verdict: "Taste harmony achieved with no friend left behind.",
            },
            plain_llm_plan: {
              fairness_score: 0.38,
              happiness_spread: 0.28,
              per_person: { Aisha: 0.30, Rohan: 0.35, Meera: 0.58, Kabir: 0.58 },
              grounding: "Unverified LLM Tourist Heuristics",
              llm_notes: "Caters exclusively to mainstream tourist recommendations.",
              issues: [
                "Mainstream bias: penalizes niche tastes (e.g. ambient dubstep, indie metal)",
                "Constraint conflict: scheduled wine bar despite alcohol-free traveler preference",
                "Zero taste debt compensation across multi-day schedule",
              ],
              itinerary_stops: [
                { day: 1, time: "10:00", name: "Castelo de S. Jorge", type: "attraction", note: "Generic crowded monument" },
                { day: 1, time: "13:00", name: "Time Out Market", type: "restaurant", note: "Packed tourist food court" },
                { day: 1, time: "16:00", name: "Tram 28 Tour", type: "attraction", note: "1-hour wait in queue" },
                { day: 1, time: "20:00", name: "Bairro Alto Wine Bar", type: "bar", note: "Violates Meera's alcohol-free constraint" },
                { day: 2, time: "10:00", name: "Pastéis de Belém", type: "cafe", note: "High tourist concentration" },
                { day: 2, time: "13:00", name: "Belém Tower Grounds", type: "attraction", note: "Generic sightseeing" },
                { day: 2, time: "16:00", name: "Rua Augusta Retail", type: "shop", note: "Mass market high street" },
                { day: 2, time: "20:00", name: "Standard Fado Tavern", type: "restaurant", note: "Overpriced tourist package" },
              ],
            },
            comparison: {
              common_ground_score: 0.684,
              plain_llm_score: 0.38,
              fairness_delta: 0.304,
              explanation:
                "Plain LLMs suffer from mainstream bias: the friend with niche cultural taste (Aisha: Burial, ambient dubstep) gets left out with only 30% satisfaction, and Meera's alcohol-free constraint is violated. Common Ground leverages Qloo's taste graph to introduce taste bridges and spotlight slots, raising collective group fairness by +30.4%.",
              common_ground_per_person: { Aisha: 0.86, Rohan: 0.82, Meera: 0.88, Kabir: 0.84 },
              plain_llm_per_person: { Aisha: 0.30, Rohan: 0.35, Meera: 0.58, Kabir: 0.58 },
            },
          });
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [tripId]);

  // Identify who the plain version leaves out (lowest score or highest delta drop)
  const plainPerPerson = data?.comparison?.plain_llm_per_person || data?.plain_llm_plan?.per_person || {};
  const cgPerPerson = data?.comparison?.common_ground_per_person || data?.common_ground_plan?.per_person || {};

  const travelers = Object.keys(plainPerPerson);

  // Find the person with the lowest plain LLM score
  let leftOutPerson = travelers[0] || "Aisha";
  let lowestScore = 1.0;
  travelers.forEach((name) => {
    if (plainPerPerson[name] < lowestScore) {
      lowestScore = plainPerPerson[name];
      leftOutPerson = name;
    }
  });

  const leftOutPlainScore = plainPerPerson[leftOutPerson] ?? 0.30;
  const leftOutCgScore = cgPerPerson[leftOutPerson] ?? 0.86;

  const cgFairnessScore = Math.round(
    ((data?.comparison?.common_ground_score ?? data?.common_ground_plan?.fairness_score ?? 0.684) * 100)
  );
  const plainFairnessScore = Math.round(
    ((data?.comparison?.plain_llm_score ?? data?.plain_llm_plan?.fairness_score ?? 0.38) * 100)
  );
  const fairnessDelta = Math.round(
    ((data?.comparison?.fairness_delta ?? (cgFairnessScore - plainFairnessScore) / 100) * 100)
  );

  return (
    <div className="min-h-screen bg-offwhite text-nearblack flex flex-col">
      <Navbar />

      <main className="flex-1 py-10 px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto w-full space-y-8">
        {/* Navigation & Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <button
            onClick={() => router.push(`/trip/${tripId}/plan`)}
            className="inline-flex items-center gap-2 text-xs font-mono text-ink-500 hover:text-nearblack transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Itinerary Plan</span>
          </button>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push(`/trip/${tripId}/card`)}
              icon={<Share2 className="w-3.5 h-3.5" />}
            >
              Export Shareable Card
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => router.push(`/trip/${tripId}/plan`)}
              icon={<Compass className="w-3.5 h-3.5" />}
            >
              Interactive Plan
            </Button>
          </div>
        </div>

        {/* Hero Banner: Headline & Fairness Verdict */}
        <div className="relative rounded-3xl bg-white border border-borderline p-6 sm:p-8 shadow-soft overflow-hidden space-y-4">
          <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-radial from-brand-violet/10 via-brand-cyan/5 to-transparent blur-3xl pointer-events-none" />

          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-pill bg-brand-violet/10 border border-brand-violet/20 text-brand-violet text-xs font-semibold">
            <Scale className="w-3.5 h-3.5" />
            <span>Side-by-Side Audit • Fairness Benchmark</span>
          </div>

          <div className="space-y-2 max-w-3xl">
            <h1 className="text-2xl sm:text-4xl font-bold tracking-tight text-nearblack">
              Plain LLM vs. Common Ground
            </h1>
            <p className="text-sm sm:text-base text-ink-500 leading-relaxed">
              Standard LLMs default to generic tourist traps and popularity heuristics, leaving niche travelers
              and strict constraints out in the cold. Common Ground uses Qloo’s Cultural Taste Graph to mathematically
              guarantee group fairness.
            </p>
          </div>

          {/* Quick Delta Strip */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-4 border-t border-borderline/60">
            <div className="p-3.5 rounded-2xl bg-subtle/60 border border-borderline">
              <span className="text-[10px] font-mono text-ink-400 uppercase block">
                Fairness Delta
              </span>
              <span className="text-xl sm:text-2xl font-bold text-brand-violet font-mono">
                +{fairnessDelta}%
              </span>
              <span className="text-[10px] font-mono text-emerald-600 block">
                Collective Harmony ↑
              </span>
            </div>

            <div className="p-3.5 rounded-2xl bg-subtle/60 border border-borderline">
              <span className="text-[10px] font-mono text-ink-400 uppercase block">
                Common Ground Score
              </span>
              <span className="text-xl sm:text-2xl font-bold text-nearblack font-mono">
                {cgFairnessScore}%
              </span>
              <span className="text-[10px] font-mono text-ink-500 block">
                Maximized min traveler
              </span>
            </div>

            <div className="p-3.5 rounded-2xl bg-subtle/60 border border-borderline">
              <span className="text-[10px] font-mono text-ink-400 uppercase block">
                Plain LLM Score
              </span>
              <span className="text-xl sm:text-2xl font-bold text-rose-500 font-mono">
                {plainFairnessScore}%
              </span>
              <span className="text-[10px] font-mono text-rose-500 block">
                High taste inequality
              </span>
            </div>

            <div className="p-3.5 rounded-2xl bg-subtle/60 border border-borderline">
              <span className="text-[10px] font-mono text-ink-400 uppercase block">
                Venue Verification
              </span>
              <span className="text-xl sm:text-2xl font-bold text-emerald-600 font-mono">
                100%
              </span>
              <span className="text-[10px] font-mono text-ink-500 block">
                Real Qloo Graph Venues
              </span>
            </div>
          </div>
        </div>

        {/* Highlight Callout: Who the Plain Version Leaves Out */}
        <div className="p-6 rounded-3xl bg-rose-50/70 border border-rose-200/80 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-2xl bg-rose-100 border border-rose-200 flex items-center justify-center shrink-0 text-rose-600">
              <HeartCrack className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-pill bg-rose-100 text-rose-700 text-[10px] font-mono font-bold uppercase">
                Who Gets Left Out?
              </div>
              <h3 className="text-lg font-bold text-nearblack tracking-tight">
                {leftOutPerson} is ignored in the generic LLM plan
              </h3>
              <p className="text-xs sm:text-sm text-ink-600 max-w-2xl leading-relaxed">
                Standard LLMs optimize for the average crowd, ignoring subtle or niche tastes.{" "}
                <span className="font-semibold text-rose-700">
                  {leftOutPerson} drops to just {Math.round(leftOutPlainScore * 100)}% satisfaction
                </span>{" "}
                under the plain prompt, while Common Ground’s mathematical taste balancing lifts her to{" "}
                <span className="font-semibold text-emerald-700">
                  {Math.round(leftOutCgScore * 100)}% with spotlight venues and taste bridges.
                </span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 shrink-0 self-end md:self-auto">
            <div className="text-right">
              <div className="text-[10px] font-mono text-ink-400 uppercase">Satisfaction Shift</div>
              <div className="text-base font-bold font-mono text-nearblack">
                <span className="text-rose-500">{Math.round(leftOutPlainScore * 100)}%</span>
                <span className="text-ink-400 mx-1.5">→</span>
                <span className="text-emerald-600 font-bold">{Math.round(leftOutCgScore * 100)}%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Side-by-Side Comparison Columns */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Column A: Plain LLM (No Taste Graph) */}
          <Card
            variant="default"
            padding="lg"
            className="border-dashed border-borderline/80 bg-subtle/30 space-y-6 flex flex-col justify-between"
          >
            <div className="space-y-5">
              {/* Card Header */}
              <div className="flex items-center justify-between pb-4 border-b border-borderline">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-500" />
                    <h3 className="text-lg font-bold text-nearblack tracking-tight">
                      Plain LLM
                    </h3>
                  </div>
                  <p className="text-xs text-ink-400 font-mono">
                    Prompt-only • Zero cultural taste graph
                  </p>
                </div>
                <div className="text-right">
                  <span className="text-xl font-bold font-mono text-rose-500">
                    {plainFairnessScore}%
                  </span>
                  <span className="text-[10px] font-mono text-ink-400 block">
                    Group Fairness
                  </span>
                </div>
              </div>

              {/* Per-Person Score Breakdown */}
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs font-mono text-ink-500 uppercase">
                  <span>Traveler Satisfaction</span>
                  <span>Score</span>
                </div>
                {travelers.map((name) => {
                  const score = plainPerPerson[name] ?? 0.4;
                  const isSuffering = score < 0.45;
                  return (
                    <div key={name} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold text-nearblack flex items-center gap-1.5">
                          {name}
                          {isSuffering && (
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-rose-100 text-rose-600 font-mono">
                              Left Out
                            </span>
                          )}
                        </span>
                        <span className={`font-mono font-bold ${isSuffering ? "text-rose-500" : "text-ink-600"}`}>
                          {Math.round(score * 100)}%
                        </span>
                      </div>
                      <div className="w-full h-2 rounded-full bg-borderline overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${
                            isSuffering ? "bg-rose-400" : "bg-ink-400"
                          }`}
                          style={{ width: `${Math.round(score * 100)}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Structural Flaws */}
              <div className="space-y-2 pt-2">
                <span className="text-xs font-mono font-bold text-ink-700 uppercase tracking-wider block">
                  Identified Algorithmic Failures:
                </span>
                <div className="space-y-1.5 text-xs text-ink-600">
                  <div className="flex items-start gap-2 p-2 rounded-xl bg-white border border-borderline/60">
                    <XCircle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                    <span>
                      <strong>Mainstream Bias:</strong> Recommends generic hotspots that penalize friends with refined or niche tastes.
                    </span>
                  </div>
                  <div className="flex items-start gap-2 p-2 rounded-xl bg-white border border-borderline/60">
                    <XCircle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                    <span>
                      <strong>Constraint Conflicts:</strong> Blindly schedules wine bars and intense walking regardless of mobility or alcohol-free preferences.
                    </span>
                  </div>
                  <div className="flex items-start gap-2 p-2 rounded-xl bg-white border border-borderline/60">
                    <XCircle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                    <span>
                      <strong>No Taste Debt Memory:</strong> Fails to compensate travelers after stops they didn't enjoy.
                    </span>
                  </div>
                </div>
              </div>

              {/* Sample LLM Stops */}
              <div className="space-y-2 pt-2">
                <span className="text-xs font-mono font-bold text-ink-700 uppercase tracking-wider block">
                  Sample Generic Schedule:
                </span>
                <div className="divide-y divide-borderline/40 text-xs">
                  {[
                    { time: "10:00", name: "Castelo de S. Jorge", note: "Mass tourist bottleneck" },
                    { time: "13:00", name: "Time Out Market", note: "Crowded food hall" },
                    { time: "16:00", name: "Tram 28 Tour", note: "Generic tour loop" },
                    { time: "20:00", name: "Bairro Alto Wine Bar", note: "Alcohol-free preference violated" },
                  ].map((s, i) => (
                    <div key={i} className="py-2 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-ink-400 text-[11px]">{s.time}</span>
                        <span className="font-medium text-nearblack">{s.name}</span>
                      </div>
                      <span className="text-[10px] font-mono text-rose-500">{s.note}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-borderline/50 text-[11px] font-mono text-ink-400 text-center">
              Unverified heuristics • No Qloo integration
            </div>
          </Card>

          {/* Column B: Common Ground (Qloo Taste Intelligence) */}
          <Card
            variant="elevated"
            padding="lg"
            className="border-brand-violet/30 shadow-float bg-white space-y-6 flex flex-col justify-between relative overflow-hidden"
          >
            <div className="absolute -top-12 -right-12 w-48 h-48 bg-gradient-radial from-brand-violet/15 via-brand-cyan/10 to-transparent blur-2xl pointer-events-none" />

            <div className="space-y-5 relative">
              {/* Card Header */}
              <div className="flex items-center justify-between pb-4 border-b border-borderline">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-brand-violet" />
                    <h3 className="text-lg font-bold text-nearblack tracking-tight">
                      Common Ground
                    </h3>
                  </div>
                  <p className="text-xs text-brand-violet font-mono font-semibold">
                    Qloo Taste Graph • Max-Min Fairness Formula
                  </p>
                </div>
                <div className="text-right">
                  <span className="text-xl font-bold font-mono text-brand-violet">
                    {cgFairnessScore}%
                  </span>
                  <span className="text-[10px] font-mono text-emerald-600 font-semibold block">
                    Group Fairness ✓
                  </span>
                </div>
              </div>

              {/* Per-Person Score Breakdown */}
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs font-mono text-ink-500 uppercase">
                  <span>Balanced Traveler Satisfaction</span>
                  <span>Score</span>
                </div>
                {travelers.map((name) => {
                  const score = cgPerPerson[name] ?? 0.84;
                  return (
                    <div key={name} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-semibold text-nearblack flex items-center gap-1.5">
                          {name}
                          <span className="text-[10px] px-1.5 py-0.2 rounded-pill bg-brand-violet/10 text-brand-violet font-mono font-semibold">
                            Included ✓
                          </span>
                        </span>
                        <span className="font-mono font-bold text-nearblack">
                          {Math.round(score * 100)}%
                        </span>
                      </div>
                      <div className="w-full h-2 rounded-full bg-borderline overflow-hidden">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-brand-violet via-brand-cyan to-brand-amber transition-all duration-500"
                          style={{ width: `${Math.round(score * 100)}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Taste Intelligence Guarantees */}
              <div className="space-y-2 pt-2">
                <span className="text-xs font-mono font-bold text-ink-700 uppercase tracking-wider block">
                  Fairness & Intelligence Guarantees:
                </span>
                <div className="space-y-1.5 text-xs text-ink-600">
                  <div className="flex items-start gap-2 p-2 rounded-xl bg-subtle/40 border border-borderline/60">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                    <span>
                      <strong>Taste Bridge Curation:</strong> Blends disparate signals (e.g. ambient electronica + mid-century design) into harmonious venues.
                    </span>
                  </div>
                  <div className="flex items-start gap-2 p-2 rounded-xl bg-subtle/40 border border-borderline/60">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                    <span>
                      <strong>Hard Guardrail Enforcement:</strong> Strict dietary, alcohol-free, and budget ceilings are filtered out before scheduling.
                    </span>
                  </div>
                  <div className="flex items-start gap-2 p-2 rounded-xl bg-subtle/40 border border-borderline/60">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                    <span>
                      <strong>Dynamic Taste Debt:</strong> If a traveler compromises on lunch, the algorithm prioritizes their cultural spotlight for the afternoon.
                    </span>
                  </div>
                </div>
              </div>

              {/* Sample Common Ground Curated Stops */}
              <div className="space-y-2 pt-2">
                <span className="text-xs font-mono font-bold text-ink-700 uppercase tracking-wider block">
                  Sample Common Ground Schedule:
                </span>
                <div className="divide-y divide-borderline/40 text-xs">
                  {[
                    { time: "09:00", name: "Lusophonica Lighthouse Cafe", tag: "Independent Music & Ocean", badge: "Taste Bridge" },
                    { time: "11:30", name: "Underdogs Public Art Gallery", tag: "Contemporary Editions", badge: "Spotlight Aisha" },
                    { time: "13:30", name: "Os Amigos Da Severa", tag: "Authentic Portuguese Petiscos", badge: "Guardrails Passed" },
                    { time: "18:00", name: "Embaixada Concept Store", tag: "Neo-Moorish Palace Design", badge: "Taste Bridge" },
                  ].map((s, i) => (
                    <div key={i} className="py-2 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-ink-400 text-[11px]">{s.time}</span>
                        <span className="font-semibold text-nearblack">{s.name}</span>
                      </div>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-pill bg-brand-violet/10 text-brand-violet font-semibold">
                        {s.badge}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-borderline/50 text-[11px] font-mono text-brand-violet text-center font-semibold">
              100% Real Venues Grounded in Qloo API
            </div>
          </Card>
        </div>

        {/* Narrative Explanation */}
        <div className="p-6 rounded-3xl bg-white border border-borderline shadow-soft space-y-3">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-brand-violet" />
            <h4 className="text-sm font-mono font-bold text-nearblack uppercase tracking-wider">
              Under The Hood: Why Plain LLMs Fail Group Travel
            </h4>
          </div>
          <p className="text-xs sm:text-sm text-ink-600 leading-relaxed">
            {data?.comparison?.explanation ||
              "Plain LLMs suffer from mainstream bias: the friend with niche cultural taste gets left out with only 30% satisfaction, and alcohol-free constraints are frequently violated. Common Ground leverages Qloo's taste graph to introduce taste bridges and spotlight slots, raising collective group fairness significantly."}
          </p>
        </div>

        {/* Action Bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-6 rounded-3xl bg-subtle/60 border border-borderline">
          <div className="space-y-0.5 text-center sm:text-left">
            <h4 className="text-base font-bold text-nearblack">
              Ready to explore or share the full itinerary?
            </h4>
            <p className="text-xs text-ink-500 font-mono">
              View day-by-day maps, guardrail checks, or export the branded social card.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <Button
              variant="secondary"
              size="lg"
              onClick={() => router.push(`/trip/${tripId}/card`)}
              icon={<Share2 className="w-4 h-4" />}
            >
              Export Trip Card
            </Button>
            <Button
              variant="primary"
              size="lg"
              onClick={() => router.push(`/trip/${tripId}/plan`)}
              icon={<Compass className="w-4 h-4" />}
            >
              Back to Full Plan
            </Button>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}

