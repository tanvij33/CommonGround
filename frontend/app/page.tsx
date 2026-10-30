"use client";

import React, { useState } from "react";
import { Navbar } from "@/components/landing/Navbar";
import { Hero } from "@/components/landing/Hero";
import { ProductPreview } from "@/components/landing/ProductPreview";
import { TasteGraphStrip } from "@/components/landing/TasteGraphStrip";
import { PastelCards } from "@/components/landing/PastelCards";
import { FairnessShowcase } from "@/components/landing/FairnessShowcase";
import { FeatureGrid } from "@/components/landing/FeatureGrid";
import { AppCards } from "@/components/landing/AppCards";
import { LlmComparisonTeaser } from "@/components/landing/LlmComparisonTeaser";
import { FinalCta } from "@/components/landing/FinalCta";
import { Footer } from "@/components/landing/Footer";
import { PlanModal } from "@/components/landing/PlanModal";
import { CreateTripModal } from "@/components/landing/CreateTripModal";

export default function LandingPage() {
  const [isDemoModalOpen, setIsDemoModalOpen] = useState(false);
  const [isCreateTripOpen, setIsCreateTripOpen] = useState(false);

  const scrollToFeatures = () => {
    const el = document.getElementById("features");
    if (el) el.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="min-h-screen bg-offwhite text-nearblack flex flex-col">
      {/* 1. Compact Navigation */}
      <Navbar
        onOpenDemo={() => setIsDemoModalOpen(true)}
        onOpenCreateTrip={() => setIsCreateTripOpen(true)}
      />

      {/* Main Page Flow */}
      <main className="flex-1">
        {/* 2. Hero Section: "Everyone's taste. One trip." */}
        <Hero
          onOpenDemo={() => setIsDemoModalOpen(true)}
          onOpenCreateTrip={() => setIsCreateTripOpen(true)}
          onScrollToFeatures={scrollToFeatures}
        />

        {/* 3. Large Gradient Product-Preview Card with Floating Score Chips */}
        <ProductPreview />

        {/* 4. Subtle "Powered by Qloo's taste graph" Strip */}
        <TasteGraphStrip />

        {/* 5. "Many tastes, one shared taste graph" with Two Pastel Cards */}
        <PastelCards />

        {/* 6. Large Gradient Showcase with Floating Fairness-Dashboard Window */}
        <FairnessShowcase />

        {/* 7. Feature Grid (6 Core Innovations) */}
        <FeatureGrid />

        {/* 8. Two App-UI Cards (Live Agent Timeline & Under-the-Hood Panel) */}
        <AppCards />

        {/* 9. Plain-LLM vs. Common Ground Teaser */}
        <LlmComparisonTeaser />

        {/* 10. Final CTA */}
        <FinalCta
          onOpenDemo={() => setIsDemoModalOpen(true)}
          onOpenCreateTrip={() => setIsCreateTripOpen(true)}
        />
      </main>

      {/* 11. Compact Footer */}
      <Footer />

      {/* Inline Trip Creator Modal (No separate URL required!) */}
      <CreateTripModal
        isOpen={isCreateTripOpen}
        onClose={() => setIsCreateTripOpen(false)}
      />

      {/* Interactive 4-Friend Live Plan Modal */}
      <PlanModal
        isOpen={isDemoModalOpen}
        onClose={() => setIsDemoModalOpen(false)}
      />
    </div>
  );
}

