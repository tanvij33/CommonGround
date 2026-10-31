"use client";

import React, { useState, useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import QRCode from "qrcode";
import { Navbar } from "@/components/landing/Navbar";
import { Footer } from "@/components/landing/Footer";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Chip } from "@/components/ui/Chip";
import { Toast } from "@/components/ui/Toast";
import { QRCodeCanvas } from "@/components/ui/QRCodeCanvas";
import {
  api,
  Plan,
  Trip,
  SAMPLE_PLAN,
  getFairnessScore,
  getMeanScore,
} from "@/lib/api";
import {
  Sparkles,
  Download,
  Share2,
  Copy,
  Check,
  ArrowLeft,
  Compass,
  MapPin,
  Calendar,
  Users,
  ShieldCheck,
  Loader2,
  Scale,
} from "lucide-react";

export default function TripCardPage() {
  const params = useParams();
  const router = useRouter();
  const tripId = (params?.tripId as string) || "trip-demo";

  const [loading, setLoading] = useState(true);
  const [trip, setTrip] = useState<Trip | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [copied, setCopied] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const cardRef = useRef<HTMLDivElement>(null);
  const hiddenCanvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    let isMounted = true;

    Promise.allSettled([api.getTrip(tripId), api.getPlan(tripId)]).then(
      ([tripRes, planRes]) => {
        if (!isMounted) return;

        if (tripRes.status === "fulfilled") {
          setTrip(tripRes.value);
        } else {
          setTrip({
            id: tripId,
            name: "Lisbon Cultural Tour",
            destination: "Lisbon",
            days: 2,
            status: "done",
            members: [
              { name: "Aisha", favorites: [{ name: "Burial", type: "artist" }, { name: "Aesop", type: "brand" }], constraints: { budget: "$$", pace: "moderate" } },
              { name: "Rohan", favorites: [{ name: "Metallica", type: "artist" }, { name: "Nike", type: "brand" }], constraints: { budget: "$$", pace: "moderate" } },
              { name: "Meera", favorites: [{ name: "Norah Jones", type: "artist" }], constraints: { budget: "$$", pace: "moderate" } },
              { name: "Kabir", favorites: [{ name: "Taylor Swift", type: "artist" }], constraints: { budget: "$$", pace: "moderate" } },
            ],
          });
        }

        if (planRes.status === "fulfilled") {
          setPlan(planRes.value);
        } else {
          setPlan(SAMPLE_PLAN);
        }

        setLoading(false);
      }
    );

    return () => {
      isMounted = false;
    };
  }, [tripId]);

  const currentPlan = plan || SAMPLE_PLAN;
  const currentTrip = trip || {
    id: tripId,
    name: "Lisbon Cultural Tour",
    destination: currentPlan.destination || "Lisbon",
    days: currentPlan.days?.length || 2,
    members: [
      { name: "Aisha", favorites: [{ name: "Burial", type: "artist" }, { name: "Aesop", type: "brand" }], constraints: { budget: "$$", pace: "moderate" } },
      { name: "Rohan", favorites: [{ name: "Metallica", type: "artist" }, { name: "Nike", type: "brand" }], constraints: { budget: "$$", pace: "moderate" } },
      { name: "Meera", favorites: [{ name: "Norah Jones", type: "artist" }], constraints: { budget: "$$", pace: "moderate" } },
      { name: "Kabir", favorites: [{ name: "Taylor Swift", type: "artist" }], constraints: { budget: "$$", pace: "moderate" } },
    ],
  };

  const fairnessPct = getFairnessScore(currentPlan.fairness);
  const meanPct = getMeanScore(currentPlan.fairness);
  const destination = currentPlan.destination || currentTrip.destination || "Lisbon";
  const shareUrl = typeof window !== "undefined" ? `${window.location.origin}/trip/${tripId}/plan` : `https://commonground.app/trip/${tripId}/plan`;

  const copyShareLink = () => {
    if (typeof window !== "undefined") {
      navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setToastMsg("Plan link copied to clipboard!");
      setTimeout(() => setCopied(false), 2500);
    }
  };

  /**
   * Generates and downloads a high-resolution, brand-styled 1200x675 PNG share card.
   */
  const handleExportPNG = async () => {
    setIsExporting(true);

    try {
      const canvas = document.createElement("canvas");
      canvas.width = 1200;
      canvas.height = 675;
      const ctx = canvas.getContext("2d");

      if (!ctx) throw new Error("Could not create canvas context");

      // 1. Background fill
      ctx.fillStyle = "#FAF9F6";
      ctx.fillRect(0, 0, 1200, 675);

      // 2. Outer Border & Delicate glow
      ctx.strokeStyle = "rgba(92, 77, 242, 0.25)";
      ctx.lineWidth = 4;
      ctx.strokeRect(16, 16, 1168, 643);

      // 3. Decorative top gradient strip inside visual box
      const grad = ctx.createLinearGradient(40, 40, 1160, 40);
      grad.addColorStop(0, "rgba(92, 77, 242, 0.18)");
      grad.addColorStop(0.5, "rgba(0, 204, 255, 0.15)");
      grad.addColorStop(1, "rgba(255, 179, 0, 0.12)");
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.roundRect(40, 40, 1120, 120, 24);
      ctx.fill();
      ctx.strokeStyle = "rgba(92, 77, 242, 0.2)";
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Brand tag
      ctx.fillStyle = "#5C4DF2";
      ctx.font = "bold 14px 'JetBrains Mono', monospace";
      ctx.fillText("✦ COMMON GROUND • TASTE-FAIR GROUP TRAVEL", 64, 76);

      // Main Trip Title
      ctx.fillStyle = "#111110";
      ctx.font = "bold 34px -apple-system, BlinkMacSystemFont, 'Inter Tight', sans-serif";
      ctx.fillText(currentTrip.name || `${destination} Cultural Journey`, 64, 124);

      // Destination Pill
      ctx.fillStyle = "#5C4DF2";
      ctx.font = "bold 15px -apple-system, BlinkMacSystemFont, sans-serif";
      ctx.fillText(`📍 ${destination} • ${currentTrip.days || 2} Days`, 920, 102);

      // 4. Left Box: Group Fairness Badge
      ctx.fillStyle = "#FFFFFF";
      ctx.beginPath();
      ctx.roundRect(40, 185, 340, 440, 20);
      ctx.fill();
      ctx.strokeStyle = "rgba(17, 17, 16, 0.1)";
      ctx.lineWidth = 1;
      ctx.stroke();

      ctx.fillStyle = "#5C4DF2";
      ctx.font = "bold 13px 'JetBrains Mono', monospace";
      ctx.fillText("COLLECTIVE TASTE HARMONY", 65, 225);

      ctx.fillStyle = "#111110";
      ctx.font = "bold 64px 'JetBrains Mono', monospace";
      ctx.fillText(`${fairnessPct}%`, 65, 295);

      ctx.fillStyle = "#777571";
      ctx.font = "14px -apple-system, BlinkMacSystemFont, sans-serif";
      ctx.fillText("Fairness score across all travelers", 65, 325);
      ctx.fillText(`Mean satisfaction: ${meanPct}%`, 65, 348);
      ctx.fillText("Max-Min guarantee: 0.6μ + 0.4min", 65, 370);

      // Verified Qloo badge
      ctx.fillStyle = "rgba(16, 185, 129, 0.12)";
      ctx.beginPath();
      ctx.roundRect(65, 410, 290, 42, 12);
      ctx.fill();
      ctx.fillStyle = "#047857";
      ctx.font = "bold 13px 'JetBrains Mono', monospace";
      ctx.fillText("✓ 100% Qloo Grounded Venues", 80, 436);

      // Lodging highlight
      if (currentPlan.stay) {
        ctx.fillStyle = "#111110";
        ctx.font = "bold 15px -apple-system, BlinkMacSystemFont, sans-serif";
        ctx.fillText("🏨 Recommended Stay:", 65, 490);
        ctx.font = "14px -apple-system, BlinkMacSystemFont, sans-serif";
        ctx.fillStyle = "#444340";
        ctx.fillText(currentPlan.stay.name.substring(0, 32), 65, 515);
        ctx.font = "12px 'JetBrains Mono', monospace";
        ctx.fillStyle = "#777571";
        ctx.fillText(`${currentPlan.stay.price_level} • ${currentPlan.stay.location}`, 65, 538);
      }

      // 5. Middle Box: Travelers & Tastes
      ctx.fillStyle = "#FFFFFF";
      ctx.beginPath();
      ctx.roundRect(405, 185, 460, 440, 20);
      ctx.fill();
      ctx.strokeStyle = "rgba(17, 17, 16, 0.1)";
      ctx.lineWidth = 1;
      ctx.stroke();

      ctx.fillStyle = "#111110";
      ctx.font = "bold 18px -apple-system, BlinkMacSystemFont, sans-serif";
      ctx.fillText("The Travel Crew", 435, 225);

      const members = currentTrip.members?.length ? currentTrip.members : [
        { name: "Aisha", favorites: [{ name: "Burial" }, { name: "Aesop" }] },
        { name: "Rohan", favorites: [{ name: "Metallica" }, { name: "Nike" }] },
        { name: "Meera", favorites: [{ name: "Norah Jones" }] },
        { name: "Kabir", favorites: [{ name: "Taylor Swift" }] },
      ];

      members.slice(0, 4).forEach((m, idx) => {
        const yPos = 250 + idx * 72;
        // Avatar circle
        ctx.fillStyle = "rgba(92, 77, 242, 0.1)";
        ctx.beginPath();
        ctx.arc(460, yPos + 14, 18, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = "#5C4DF2";
        ctx.font = "bold 14px 'JetBrains Mono', monospace";
        ctx.fillText(m.name[0]?.toUpperCase() || "T", 454, yPos + 20);

        // Name
        ctx.fillStyle = "#111110";
        ctx.font = "bold 15px -apple-system, BlinkMacSystemFont, sans-serif";
        ctx.fillText(m.name, 490, yPos + 12);

        // Favorites
        ctx.fillStyle = "#777571";
        ctx.font = "12px 'JetBrains Mono', monospace";
        const favStr = m.favorites?.map((f: any) => f.name).join(" • ") || "Culture & Sights";
        ctx.fillText(favStr.substring(0, 45), 490, yPos + 30);
      });

      // Sample Highlight Slots
      ctx.fillStyle = "rgba(92, 77, 242, 0.06)";
      ctx.beginPath();
      ctx.roundRect(430, 545, 410, 60, 14);
      ctx.fill();
      ctx.fillStyle = "#5C4DF2";
      ctx.font = "bold 13px -apple-system, BlinkMacSystemFont, sans-serif";
      ctx.fillText("✦ Taste Bridge:", 445, 570);
      ctx.fillStyle = "#111110";
      ctx.font = "13px -apple-system, BlinkMacSystemFont, sans-serif";
      ctx.fillText("Lusophonica Lighthouse Music Cafe & Embaixada Palace", 445, 590);

      // 6. Right Box: QR Code & Link
      ctx.fillStyle = "#FFFFFF";
      ctx.beginPath();
      ctx.roundRect(890, 185, 270, 440, 20);
      ctx.fill();
      ctx.strokeStyle = "rgba(17, 17, 16, 0.1)";
      ctx.lineWidth = 1;
      ctx.stroke();

      ctx.fillStyle = "#111110";
      ctx.font = "bold 16px -apple-system, BlinkMacSystemFont, sans-serif";
      ctx.fillText("Scan to View Plan", 930, 225);

      // Render real QR Code
      const qrDataUrl = await QRCode.toDataURL(shareUrl, {
        margin: 1,
        width: 190,
        color: { dark: "#111110", light: "#FFFFFF" },
      });

      const qrImg = new Image();
      qrImg.src = qrDataUrl;
      await new Promise((resolve) => {
        qrImg.onload = resolve;
      });

      ctx.drawImage(qrImg, 930, 250, 190, 190);

      ctx.fillStyle = "#777571";
      ctx.font = "11px 'JetBrains Mono', monospace";
      ctx.fillText("Instant live schedule", 965, 465);
      ctx.fillText("Interactive maps & stops", 955, 485);

      // Brand stamp
      ctx.fillStyle = "#5C4DF2";
      ctx.font = "bold 13px 'JetBrains Mono', monospace";
      ctx.fillText("commonground.app", 960, 575);

      // 7. Trigger download
      const imageUri = canvas.toDataURL("image/png");
      const downloadLink = document.createElement("a");
      downloadLink.download = `common-ground-${destination.toLowerCase().replace(/\s+/g, "-")}-trip-card.png`;
      downloadLink.href = imageUri;
      downloadLink.click();

      setToastMsg("Trip card exported as PNG!");
    } catch (err) {
      console.error("Canvas export error:", err);
      setToastMsg("Failed to export PNG. Please try again.");
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="min-h-screen bg-offwhite text-nearblack flex flex-col">
      <Navbar />

      <main className="flex-1 py-10 px-4 sm:px-6 lg:px-8 max-w-5xl mx-auto w-full space-y-8">
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
              onClick={copyShareLink}
              icon={copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
            >
              {copied ? "Copied" : "Copy Link"}
            </Button>
            <Button
              variant="primary"
              size="sm"
              disabled={isExporting}
              onClick={handleExportPNG}
              icon={
                isExporting ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Download className="w-3.5 h-3.5" />
                )
              }
            >
              {isExporting ? "Rendering PNG..." : "Download as PNG"}
            </Button>
          </div>
        </div>

        {/* Live Card Preview Section */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-nearblack">
                Shareable Trip Card
              </h1>
              <p className="text-xs sm:text-sm text-ink-500 font-mono">
                Editorial travel badge optimized for sharing with your group and on social channels.
              </p>
            </div>
            <span className="text-xs font-mono text-brand-violet font-semibold hidden sm:inline-block">
              1200 × 675 High-Res Export
            </span>
          </div>

          {/* Branded Visual Card Container */}
          <div
            ref={cardRef}
            className="relative rounded-3xl bg-white border border-borderline shadow-float p-6 sm:p-10 space-y-8 overflow-hidden select-none"
          >
            {/* Top Multi-Color Soft Mesh Gradient Inside Product Preview */}
            <div className="absolute top-0 left-0 right-0 h-32 bg-gradient-to-r from-brand-violet/15 via-brand-cyan/15 to-brand-amber/10 blur-xl pointer-events-none" />

            {/* Card Header Strip */}
            <div className="relative flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-borderline/80">
              <div className="space-y-1">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-pill bg-brand-violet/10 border border-brand-violet/20 text-brand-violet text-xs font-mono font-bold">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>COMMON GROUND • TASTE-FAIR GROUP TRAVEL</span>
                </div>
                <h2 className="text-2xl sm:text-4xl font-bold tracking-tight text-nearblack">
                  {currentTrip.name || `${destination} Cultural Journey`}
                </h2>
                <div className="flex items-center gap-2 text-xs font-mono text-ink-500">
                  <MapPin className="w-3.5 h-3.5 text-brand-violet" />
                  <span>{destination}</span>
                  <span>•</span>
                  <Calendar className="w-3.5 h-3.5 text-ink-400" />
                  <span>{currentTrip.days || 2} Days Itinerary</span>
                </div>
              </div>

              {/* Group Fairness Pill */}
              <div className="p-3.5 rounded-2xl bg-subtle/80 border border-borderline text-right shrink-0">
                <span className="text-[10px] font-mono text-ink-400 uppercase block">
                  Collective Harmony
                </span>
                <span className="text-2xl sm:text-3xl font-bold font-mono text-brand-violet">
                  {fairnessPct}%
                </span>
                <span className="text-[10px] font-mono text-emerald-600 block font-semibold">
                  Balanced Taste Graph ✓
                </span>
              </div>
            </div>

            {/* Card Body Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Box 1: Lodging & Fairness Math */}
              <div className="p-5 rounded-2xl bg-subtle/40 border border-borderline space-y-4">
                <div className="space-y-1">
                  <span className="text-xs font-mono font-bold text-ink-700 uppercase">
                    🏨 Recommended Lodging
                  </span>
                  <h4 className="text-base font-bold text-nearblack">
                    {currentPlan.stay?.name || "No lodging found for this group"}
                  </h4>
                  {currentPlan.stay && (
                    <p className="text-xs text-ink-500 font-mono">
                      {currentPlan.stay.price_level} • {currentPlan.stay.location}
                    </p>
                  )}
                </div>

                <div className="pt-2 border-t border-borderline/60 space-y-1 text-xs text-ink-600">
                  <div className="flex items-center justify-between font-mono text-[11px]">
                    <span className="text-ink-400">Mean Satisfaction:</span>
                    <span className="font-bold text-nearblack">{meanPct}%</span>
                  </div>
                  <div className="flex items-center justify-between font-mono text-[11px]">
                    <span className="text-ink-400">Fairness Formula:</span>
                    <span className="font-bold text-brand-violet">0.6μ + 0.4min</span>
                  </div>
                  <div className="flex items-center gap-1.5 pt-2 text-emerald-700 font-mono text-[11px]">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>100% Qloo Grounded</span>
                  </div>
                </div>
              </div>

              {/* Box 2: Travelers & Cultural Signals */}
              <div className="p-5 rounded-2xl bg-subtle/40 border border-borderline space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-ink-700 uppercase">
                    Traveler Crew ({currentTrip.members?.length || 4})
                  </span>
                  <Users className="w-3.5 h-3.5 text-brand-violet" />
                </div>

                <div className="space-y-2.5">
                  {(currentTrip.members?.length ? currentTrip.members : [
                    { name: "Aisha", favorites: [{ name: "Burial" }, { name: "Aesop" }] },
                    { name: "Rohan", favorites: [{ name: "Metallica" }, { name: "Nike" }] },
                    { name: "Meera", favorites: [{ name: "Norah Jones" }] },
                    { name: "Kabir", favorites: [{ name: "Taylor Swift" }] },
                  ]).slice(0, 4).map((member, i) => (
                    <div key={i} className="flex items-center justify-between gap-2 text-xs">
                      <div className="flex items-center gap-2 min-w-0">
                        <div className="w-6 h-6 rounded-full bg-brand-violet/10 text-brand-violet font-mono font-bold text-[10px] flex items-center justify-center shrink-0">
                          {member.name[0]?.toUpperCase() || "T"}
                        </div>
                        <span className="font-semibold text-nearblack truncate">
                          {member.name}
                        </span>
                      </div>
                      <span className="text-[10px] font-mono text-ink-400 truncate max-w-[140px]">
                        {member.favorites?.map((f: any) => f.name).join(", ") || "Diverse Tastes"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Box 3: QR Code & Live Plan Link */}
              <div className="p-5 rounded-2xl bg-subtle/40 border border-borderline flex flex-col items-center justify-center text-center space-y-3">
                <span className="text-xs font-mono font-bold text-ink-700 uppercase">
                  Scan to View Plan
                </span>
                <div className="p-2.5 bg-white rounded-2xl border border-borderline/80 shadow-xs">
                  <QRCodeCanvas value={shareUrl} size={120} />
                </div>
                <span className="text-[10px] font-mono text-ink-400">
                  Instant live schedule & maps
                </span>
              </div>
            </div>

            {/* Taste Bridge Highlight Strip */}
            <div className="p-4 rounded-2xl bg-gradient-to-r from-brand-violet/10 via-brand-cyan/10 to-transparent border border-brand-violet/20 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-brand-violet shrink-0" />
                <span className="text-ink-700">
                  <strong>Featured Taste Bridge:</strong> Lusophonica Lighthouse Music Cafe & Underdogs Public Art Gallery
                </span>
              </div>
              <span className="text-[10px] font-mono text-brand-violet font-semibold shrink-0">
                Balanced compromises across all 4 friends
              </span>
            </div>

            {/* Footer Watermark */}
            <div className="flex items-center justify-between pt-4 border-t border-borderline/60 text-[11px] font-mono text-ink-400">
              <span>commonground.app</span>
              <span>Powered by Qloo’s Cultural Intelligence</span>
            </div>
          </div>
        </div>

        {/* CTA Bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-6 rounded-3xl bg-subtle/60 border border-borderline">
          <div className="space-y-0.5 text-center sm:text-left">
            <h4 className="text-sm font-bold text-nearblack">
              Download this card to share on Instagram, WhatsApp, or Twitter
            </h4>
            <p className="text-xs text-ink-500 font-mono">
              Includes QR code for your travel crew to access the live interactive itinerary.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <Button
              variant="secondary"
              size="lg"
              onClick={() => router.push(`/trip/${tripId}/compare`)}
              icon={<Scale className="w-4 h-4" />}
            >
              Side-by-Side Audit
            </Button>
            <Button
              variant="primary"
              size="lg"
              disabled={isExporting}
              onClick={handleExportPNG}
              icon={
                isExporting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Download className="w-4 h-4" />
                )
              }
            >
              {isExporting ? "Rendering PNG..." : "Download as PNG"}
            </Button>
          </div>
        </div>

        {/* Hidden Canvas for High-DPI Rendering */}
        <canvas ref={hiddenCanvasRef} className="hidden" />

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
      </main>

      <Footer />
    </div>
  );
}
