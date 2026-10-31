"use client";

import React, { useEffect, useRef, useState } from "react";
import { MapPin, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import { Input } from "@/components/ui/Input";
import { api, DestinationResult } from "@/lib/api";

// Shared across instances so repeated queries never hit the backend twice per page session
const resultCache = new Map<string, DestinationResult[]>();

const MIN_QUERY_LENGTH = 2;
const DEBOUNCE_MS = 350;

export interface DestinationAutocompleteProps {
  selected: DestinationResult | null;
  onSelect: (destination: DestinationResult | null) => void;
  quickCities?: string[];
  hint?: string;
}

export const DestinationAutocomplete: React.FC<DestinationAutocompleteProps> = ({
  selected,
  onSelect,
  quickCities = [],
  hint = "Search cities worldwide",
}) => {
  const [text, setText] = useState(selected?.name ?? "");
  // Only user input (typing or a quick pick) triggers a search; showing a selection does not
  const [searchTerm, setSearchTerm] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [results, setResults] = useState<DestinationResult[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [errorText, setErrorText] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    const term = searchTerm.trim().toLowerCase().replace(/\s+/g, " ");
    if (term.length < MIN_QUERY_LENGTH) {
      setResults([]);
      setStatus("idle");
      return;
    }

    const cached = resultCache.get(term);
    if (cached) {
      setResults(cached);
      setStatus("done");
      return;
    }

    setStatus("loading");
    setErrorText(null);
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const found = await api.searchDestinations(term, controller.signal);
        resultCache.set(term, found);
        setResults(found);
        setStatus("done");
      } catch (err: any) {
        if (controller.signal.aborted) return;
        setResults([]);
        setErrorText(err?.message || "Destination search failed");
        setStatus("error");
      }
    }, DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [searchTerm, retryCount]);

  const startSearch = (value: string) => {
    setText(value);
    setSearchTerm(value);
    setIsOpen(true);
    if (selected && value.trim() !== selected.name) onSelect(null);
  };

  const choose = (dest: DestinationResult) => {
    setText(dest.name);
    setIsOpen(false);
    onSelect(dest);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      // Never submit the form with an unselected destination
      e.preventDefault();
      if (status === "done" && results.length > 0) choose(results[0]);
    } else if (e.key === "Escape") {
      setIsOpen(false);
    }
  };

  const trimmedTerm = searchTerm.trim();

  return (
    <div className="space-y-2 relative" ref={containerRef}>
      <div className="flex items-center justify-between">
        <label className="text-xs font-mono font-bold text-ink-700 uppercase tracking-wider block">
          Destination City
        </label>
        <span className="text-[11px] font-mono text-ink-400">{hint}</span>
      </div>

      <Input
        icon={<MapPin className="w-4 h-4 text-brand-violet" />}
        value={text}
        onFocus={() => setIsOpen(true)}
        onChange={(e) => startSearch(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="e.g. Porto, Kyoto, Buenos Aires, Seoul..."
        autoComplete="off"
        role="combobox"
        aria-expanded={isOpen}
        aria-autocomplete="list"
      />

      {isOpen && trimmedTerm.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-1.5 z-40 bg-white/95 backdrop-blur-md rounded-2xl border border-borderline shadow-float max-h-64 overflow-y-auto divide-y divide-borderline/40">
          {trimmedTerm.length < MIN_QUERY_LENGTH ? (
            <p className="px-4 py-3 text-xs text-ink-500">Type at least {MIN_QUERY_LENGTH} letters to search.</p>
          ) : status === "loading" ? (
            <p className="px-4 py-3 text-xs text-ink-500 flex items-center gap-2">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-brand-violet" />
              Searching destinations…
            </p>
          ) : status === "error" ? (
            <div className="px-4 py-3 text-xs text-rose-600 flex items-start justify-between gap-3">
              <span className="flex items-start gap-2">
                <AlertCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                {errorText}
              </span>
              <button
                type="button"
                onClick={() => setRetryCount((n) => n + 1)}
                className="font-mono text-[11px] text-brand-violet shrink-0 hover:underline"
              >
                Retry
              </button>
            </div>
          ) : status === "done" && results.length === 0 ? (
            <p className="px-4 py-3 text-xs text-ink-500">
              No destinations found for “{trimmedTerm}”. Try the full official name (e.g. “City of Cape Town”).
            </p>
          ) : (
            results.map((dest) => (
              <button
                key={dest.id}
                type="button"
                onClick={() => choose(dest)}
                className="w-full px-4 py-2.5 text-left text-xs hover:bg-brand-violet/5 transition-colors flex items-center justify-between gap-2"
              >
                <div className="space-y-0.5 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="font-semibold text-nearblack">{dest.name}</span>
                    {dest.country && <span className="text-ink-400 text-[11px]">• {dest.country}</span>}
                  </div>
                  <div className="text-[10px] text-ink-400 font-mono truncate">{dest.label}</div>
                </div>
                <span className="text-[10px] font-mono text-brand-violet px-2 py-0.5 rounded-pill bg-brand-violet/10 shrink-0">
                  Select
                </span>
              </button>
            ))
          )}
        </div>
      )}

      {selected ? (
        <p className="text-[11px] font-mono text-emerald-700 flex items-center gap-1.5 px-1">
          <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
          <span className="truncate">{selected.label}</span>
        </p>
      ) : (
        text.trim() && (
          <p className="text-[11px] font-mono text-amber-700 px-1">Choose a destination from the suggestions.</p>
        )
      )}

      {quickCities.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 pt-1">
          <span className="text-[11px] font-mono text-ink-400 mr-1">Popular:</span>
          {quickCities.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => startSearch(c)}
              className={`text-xs px-2.5 py-0.5 rounded-pill border transition-colors ${
                selected?.name.toLowerCase() === c.toLowerCase()
                  ? "bg-brand-violet text-white border-brand-violet font-semibold"
                  : "bg-subtle text-ink-700 border-borderline hover:bg-borderline"
              }`}
            >
              {c}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
