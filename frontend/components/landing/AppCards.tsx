import React from "react";
import { AppWindow } from "@/components/ui/AppWindow";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { CheckCircle2, Terminal, Activity, Database, ShieldCheck, Cpu } from "lucide-react";

export const AppCards: React.FC = () => {
  const agentSteps = [
    { label: "Resolve cultural taste signals", pct: 15, status: "done" },
    { label: "Fetch Qloo candidates (6 categories)", pct: 35, status: "done" },
    { label: "Strict Lisbon metro boundary enforcement", pct: 50, status: "done" },
    { label: "Filter hard constraints (dietary, alcohol-free)", pct: 65, status: "done" },
    { label: "Calculate fairness & dynamic taste debt", pct: 80, status: "done" },
    { label: "Programmatic self-critique & validation", pct: 95, status: "done" },
    { label: "Collaborative 4-track soundtrack generation", pct: 100, status: "done" },
  ];

  return (
    <section className="py-20 sm:py-28 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-12">
        <SectionHeader
          kicker="ARCHITECTURE & TRANSPARENCY"
          title="Autonomous agent pipeline & live telemetry"
          description="Every step of itinerary compilation is audited, streamed via Server-Sent Events, and grounded in real cultural intelligence."
        />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-stretch">
          {/* Card 1: Live Agent Timeline */}
          <div className="flex flex-col">
            <AppWindow
              title="agent / pipeline-execution.stream"
              badge="SSE STREAMING ACTIVE"
              className="h-full"
            >
              <div className="space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-borderline/60">
                  <div className="flex items-center gap-2">
                    <Activity className="w-4 h-4 text-brand-violet animate-pulse" />
                    <span className="text-xs font-mono font-bold text-nearblack uppercase">
                      Execution Stepper (8 Stages)
                    </span>
                  </div>
                  <span className="text-[11px] font-mono text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-pill border border-emerald-200">
                    Status: 100% Ready
                  </span>
                </div>

                <div className="space-y-3">
                  {agentSteps.map((s, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between text-xs p-2.5 rounded-2xl bg-subtle/50 border border-borderline/40"
                    >
                      <div className="flex items-center gap-2.5">
                        <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                        <span className="font-medium text-ink-900 tracking-tight">
                          {s.label}
                        </span>
                      </div>
                      <span className="text-[10px] font-mono font-semibold text-ink-500">
                        {s.pct}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </AppWindow>
          </div>

          {/* Card 2: Under-the-Hood Panel */}
          <div className="flex flex-col">
            <AppWindow
              title="audit / telemetry-log.jsonl"
              badge="AUDIT LOG VERIFIED"
              className="h-full bg-slate-950 text-slate-100 border-slate-800"
            >
              <div className="space-y-5 text-xs font-mono">
                {/* Header terminal bar */}
                <div className="flex items-center justify-between pb-3 border-b border-slate-800 text-slate-400">
                  <span className="flex items-center gap-1.5 text-brand-violet">
                    <Terminal className="w-3.5 h-3.5" /> telemetry@commonground:~#
                  </span>
                  <span>hit_rate=100.0%</span>
                </div>

                {/* Telemetry Stats */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-1">
                    <span className="text-[10px] text-slate-400">Total Qloo Calls</span>
                    <p className="text-xl font-bold text-emerald-400">136 / 200</p>
                    <span className="text-[10px] text-slate-500">All within quota</span>
                  </div>
                  <div className="p-3 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-1">
                    <span className="text-[10px] text-slate-400">Grounding Guarantee</span>
                    <p className="text-xl font-bold text-brand-cyan">100% Grounded</p>
                    <span className="text-[10px] text-slate-500">0 Hallucinations</span>
                  </div>
                </div>

                {/* Audit JSON Terminal Output */}
                <div className="p-3.5 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-1.5 text-[11px] leading-relaxed text-slate-300">
                  <p className="text-slate-500">// Programmatic Self-Critique Log</p>
                  <p><span className="text-emerald-400">✓</span> target_city: "Lisbon, Portugal"</p>
                  <p><span className="text-emerald-400">✓</span> metro_boundary_filtered: 0 cross-river venues</p>
                  <p><span className="text-emerald-400">✓</span> aisha_vegetarian_guarantee: 100% verified</p>
                  <p><span className="text-emerald-400">✓</span> meera_alcohol_free_filter: 0 bars assigned</p>
                  <p><span className="text-emerald-400">✓</span> kabir_budget_ceiling: max $$ preserved</p>
                  <p className="text-slate-500 pt-1">// Result: Programmatic Critique Approved</p>
                </div>
              </div>
            </AppWindow>
          </div>
        </div>
      </div>
    </section>
  );
};

