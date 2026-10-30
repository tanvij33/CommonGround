import React from "react";
import { Button } from "@/components/ui/Button";
import { Compass, Sparkles, Github } from "lucide-react";

export interface NavbarProps {
  onOpenDemo?: () => void;
  onOpenCreateTrip?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenDemo, onOpenCreateTrip }) => {
  return (
    <header className="sticky top-0 z-40 w-full bg-offwhite/85 backdrop-blur-md border-b border-borderline/60">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Logo */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-nearblack flex items-center justify-center text-white shadow-soft">
            <Compass className="w-4 h-4 text-brand-violet" />
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="font-bold tracking-tight text-base text-nearblack">
              Common Ground
            </span>
            <span className="hidden sm:inline-block text-[11px] font-mono font-medium text-ink-400">
              / cultural.ai
            </span>
          </div>
        </div>

        {/* Desktop Navigation Links */}
        <nav className="hidden md:flex items-center gap-7 text-xs font-medium tracking-tight text-ink-700">
          <a href="#taste-graph" className="hover:text-nearblack transition-colors">
            Taste Graph
          </a>
          <a href="#fairness" className="hover:text-nearblack transition-colors">
            Fairness Engine
          </a>
          <a href="#features" className="hover:text-nearblack transition-colors">
            Features
          </a>
          <a href="#comparison" className="hover:text-nearblack transition-colors">
            vs Plain LLM
          </a>
        </nav>

        {/* CTA Buttons */}
        <div className="flex items-center gap-2.5">
          <Button
            variant="primary"
            size="sm"
            onClick={onOpenCreateTrip}
          >
            Create Trip
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={onOpenDemo}
            icon={<Sparkles className="w-3.5 h-3.5 text-brand-violet" />}
          >
            Live Demo
          </Button>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden sm:inline-block"
          >
            <Button variant="ghost" size="sm">
              API Docs
            </Button>
          </a>
        </div>
      </div>
    </header>
  );
};

