"use client";

import React from "react";
import Link from "next/link";
import { Navbar } from "@/components/landing/Navbar";
import { Footer } from "@/components/landing/Footer";
import { Button } from "@/components/ui/Button";
import { Sparkles, Compass, ArrowLeft, MapPin } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-offwhite text-nearblack flex flex-col justify-between">
      <Navbar />

      <main className="flex-1 flex items-center justify-center p-6 sm:p-12">
        <div className="relative max-w-lg w-full text-center space-y-6">
          {/* Subtle blurred orb background */}
          <div className="absolute -top-12 left-1/2 -translate-x-1/2 w-64 h-64 bg-gradient-radial from-brand-violet/15 via-brand-cyan/10 to-transparent blur-3xl pointer-events-none" />

          {/* Badge */}
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-pill bg-brand-violet/10 border border-brand-violet/20 text-brand-violet text-xs font-mono font-bold">
            <MapPin className="w-3.5 h-3.5" />
            <span>404 • Off The Beaten Path</span>
          </div>

          <div className="space-y-3">
            <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-nearblack">
              Destination Not Found
            </h1>
            <p className="text-sm sm:text-base text-ink-500 leading-relaxed max-w-md mx-auto">
              This route or itinerary hasn’t been charted on the taste graph. Let’s recalibrate your coordinates and find common ground.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
            <Link href="/" className="w-full sm:w-auto">
              <Button
                variant="primary"
                size="lg"
                className="w-full"
                icon={<ArrowLeft className="w-4 h-4" />}
              >
                Back to Dashboard
              </Button>
            </Link>
            <Link href="/trip/trip-demo-lisbon/plan" className="w-full sm:w-auto">
              <Button
                variant="outline"
                size="lg"
                className="w-full"
                icon={<Compass className="w-4 h-4" />}
              >
                View Live Demo Plan
              </Button>
            </Link>
          </div>

          <p className="text-[11px] font-mono text-ink-400 pt-6">
            Error Code: ROUTE_UNMAPPED • Qloo Cultural Intelligence
          </p>
        </div>
      </main>

      <Footer />
    </div>
  );
}

