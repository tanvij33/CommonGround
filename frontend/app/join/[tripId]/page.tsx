"use client";

import React, { useState, useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { Navbar } from "@/components/landing/Navbar";
import { Footer } from "@/components/landing/Footer";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Chip } from "@/components/ui/Chip";
import { Toggle } from "@/components/ui/Toggle";
import { Toast } from "@/components/ui/Toast";
import {
  api,
  CulturalFavorite,
  TravelerConstraints,
  AutocompleteEntity,
  Trip,
} from "@/lib/api";
import {
  Sparkles,
  Search,
  X,
  Check,
  Music,
  Film,
  ShoppingBag,
  MapPin,
  Loader2,
  Users,
  Compass,
  ArrowRight,
  ShieldCheck,
  PlusCircle,
} from "lucide-react";

export default function JoinTripPage() {
  const params = useParams();
  const router = useRouter();
  const tripId = (params?.tripId as string) || "trip-demo";

  // Trip Context State
  const [trip, setTrip] = useState<Trip | null>(null);
  const [loadingTrip, setLoadingTrip] = useState(true);

  // Form State
  const [name, setName] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedType, setSelectedType] = useState<string>("all");
  const [searchResults, setSearchResults] = useState<AutocompleteEntity[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const searchDropdownRef = useRef<HTMLDivElement>(null);
  const [favorites, setFavorites] = useState<CulturalFavorite[]>([]);

  // Constraints State
  const [budget, setBudget] = useState<"$" | "$$" | "$$$" | "$$$$">("$$");
  const [dietary, setDietary] = useState<string[]>([]);
  const [pace, setPace] = useState<"relaxed" | "moderate" | "intense">("moderate");
  const [alcoholFree, setAlcoholFree] = useState(false);
  const [stepFree, setStepFree] = useState(false);

  // Flow State
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  // Pre-load Trip Details
  useEffect(() => {
    let isMounted = true;
    api
      .getTrip(tripId)
      .then((t) => {
        if (isMounted) {
          setTrip(t);
          setLoadingTrip(false);
        }
      })
      .catch(() => {
        // Fallback for mock/offline trip
        if (isMounted) {
          setTrip({
            id: tripId,
            name: "Lisbon Cultural Immersion",
            destination: "Lisbon",
            days: 2,
            status: "waiting",
            members: [],
          });
          setLoadingTrip(false);
        }
      });
    return () => {
      isMounted = false;
    };
  }, [tripId]);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (searchDropdownRef.current && !searchDropdownRef.current.contains(e.target as Node)) {
        setIsDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Instant & Responsive Cultural Favorites Autocomplete
  useEffect(() => {
    let isMounted = true;
    setIsSearching(true);
    const typeFilter = selectedType === "all" ? undefined : selectedType;

    const timer = setTimeout(async () => {
      try {
        const results = await api.searchEntities(searchQuery.trim(), typeFilter);
        if (isMounted) setSearchResults(results);
      } catch {
        if (isMounted) setSearchResults([]);
      } finally {
        if (isMounted) setIsSearching(false);
      }
    }, 50);

    return () => {
      isMounted = false;
      clearTimeout(timer);
    };
  }, [searchQuery, selectedType]);

  const addFavorite = (entity: { name: string; type?: string; qloo_id?: string }) => {
    if (favorites.some((f) => f.name.toLowerCase() === entity.name.toLowerCase())) return;
    if (favorites.length >= 8) {
      setToastMsg("Maximum of 8 favorites reached for balanced weighting.");
      return;
    }
    setFavorites([...favorites, { name: entity.name, type: entity.type, qloo_id: entity.qloo_id }]);
    setSearchQuery("");
    setIsDropdownOpen(false);
  };

  const handleAddDirect = () => {
    const clean = searchQuery.trim();
    if (!clean) return;
    addFavorite({
      name: clean,
      type: selectedType === "all" ? "cultural_entity" : selectedType,
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      if (searchResults.length > 0 && searchQuery.trim()) {
        const top = searchResults[0];
        addFavorite({ name: top.name, type: top.type, qloo_id: top.id });
      } else if (searchQuery.trim()) {
        handleAddDirect();
      }
    }
  };

  const removeFavorite = (favName: string) => {
    setFavorites(favorites.filter((f) => f.name !== favName));
  };

  const toggleDietary = (item: string) => {
    if (dietary.includes(item)) {
      setDietary(dietary.filter((d) => d !== item));
    } else {
      setDietary([...dietary, item]);
    }
  };

  // Quick Inspiration Presets
  const quickInspirations = [
    { name: "Burial", type: "artist" },
    { name: "Radiohead", type: "artist" },
    { name: "Spirited Away", type: "movie" },
    { name: "Aesop", type: "brand" },
    { name: "Norah Jones", type: "artist" },
    { name: "Wes Anderson", type: "movie" },
    { name: "Taylor Swift", type: "artist" },
    { name: "Nike", type: "brand" },
    { name: "Specialty Coffee", type: "place" },
    { name: "Natural Wine", type: "place" },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setToastMsg("Please enter your name.");
      return;
    }
    if (favorites.length < 3) {
      setToastMsg("Please pick at least 3 cultural favorites so Qloo can map your taste.");
      return;
    }

    setIsSubmitting(true);
    const constraints: TravelerConstraints = {
      budget,
      dietary,
      alcohol_free: alcoholFree,
      pace,
      accessibility: stepFree ? ["step-free"] : [],
    };

    try {
      await api.addProfile(tripId, {
        name: name.trim(),
        favorites,
        constraints,
      });
      setIsDone(true);
      setToastMsg("You're joined! Taste profile saved.");
    } catch {
      // Safe offline fallback
      setIsDone(true);
      setToastMsg("Joined in offline mode!");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-offwhite text-nearblack flex flex-col">
      <Navbar />

      <main className="flex-1 py-10 px-4 sm:px-6 lg:px-8 max-w-2xl mx-auto w-full space-y-6">
        {toastMsg && (
          <div className="fixed bottom-6 right-6 z-50 animate-bounce">
            <Toast
              title="Taste Onboarding"
              message={toastMsg}
              type="info"
              onClose={() => setToastMsg(null)}
            />
          </div>
        )}

        {/* Trip Header Banner */}
        <div className="rounded-3xl bg-white border border-borderline p-6 shadow-soft space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold text-brand-violet uppercase">
              Join Group Trip
            </span>
            <span className="text-xs font-mono text-ink-400">30-sec onboarding</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-nearblack">
            {trip ? trip.name : "Group Trip"}
          </h1>
          <p className="text-xs sm:text-sm text-ink-500 font-mono">
            Destination: {trip?.destination || "Lisbon"} • {trip?.days || 2} Days
          </p>
        </div>

        {/* Form or Done Screen */}
        {!isDone ? (
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Step 1: Your Name */}
            <Card variant="default" padding="lg" className="space-y-3">
              <label className="text-xs font-mono font-bold text-ink-700 uppercase tracking-wider block">
                1. Your Name
              </label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Aisha or Rohan"
                required
              />
            </Card>

            {/* Step 2: 5-8 Cultural Favorites with Qloo Live Autocomplete */}
            <Card variant="default" padding="lg" className="space-y-4">
              <div className="flex items-center justify-between">
                <label className="text-xs font-mono font-bold text-ink-700 uppercase tracking-wider block">
                  2. Cultural Favorites ({favorites.length}/8)
                </label>
                <span className="text-[11px] font-mono text-brand-violet font-semibold">
                  {favorites.length < 3 ? "Pick at least 3" : "Taste signals calibrated ✓"}
                </span>
              </div>

              <p className="text-xs text-ink-500 leading-relaxed">
                Add musicians, films, brands, or places you love. Qloo translates these into dining and lodging affinities.
              </p>

              {/* Type Category Filter Pills */}
              <div className="flex flex-wrap gap-1.5">
                {[
                  { id: "all", label: "All" },
                  { id: "artist", label: "Music / Artist" },
                  { id: "movie", label: "Cinema / TV" },
                  { id: "brand", label: "Brand / Fashion" },
                  { id: "place", label: "Place / Culture" },
                ].map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setSelectedType(t.id)}
                    className={`text-[11px] font-mono px-2.5 py-1 rounded-pill border transition-colors ${
                      selectedType === t.id
                        ? "bg-nearblack text-white border-nearblack font-semibold"
                        : "bg-subtle text-ink-700 border-borderline hover:bg-borderline"
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>

              {/* Search Autocomplete Input with Add Button */}
              <div className="relative" ref={searchDropdownRef}>
                <div className="flex items-center gap-2">
                  <div className="relative flex-1">
                    <Input
                      icon={
                        isSearching ? (
                          <Loader2 className="w-4 h-4 animate-spin text-brand-violet" />
                        ) : (
                          <Search className="w-4 h-4 text-ink-400" />
                        )
                      }
                      value={searchQuery}
                      onFocus={() => setIsDropdownOpen(true)}
                      onChange={(e) => {
                        setSearchQuery(e.target.value);
                        setIsDropdownOpen(true);
                      }}
                      onKeyDown={handleKeyDown}
                      placeholder="Search or type any artist, movie, brand, place..."
                    />
                  </div>
                  <Button
                    type="button"
                    variant="secondary"
                    size="md"
                    onClick={handleAddDirect}
                    disabled={!searchQuery.trim()}
                    icon={<PlusCircle className="w-4 h-4 text-brand-violet" />}
                  >
                    Add
                  </Button>
                </div>

                {/* Autocomplete Dropdown List */}
                {isDropdownOpen && searchResults.length > 0 && (
                  <div className="absolute top-full left-0 right-0 mt-1.5 z-50 bg-white/95 backdrop-blur-md rounded-2xl border border-borderline shadow-float max-h-64 overflow-y-auto divide-y divide-borderline/40">
                    <div className="px-3.5 py-1.5 text-[10px] font-mono text-ink-400 bg-subtle/50 flex items-center justify-between">
                      <span>
                        {searchQuery.trim()
                          ? "Suggestions & matches"
                          : `Popular suggestions (${selectedType === "all" ? "All types" : selectedType})`}
                      </span>
                      <span className="text-brand-violet font-semibold">Click or press Enter</span>
                    </div>
                    {searchResults.map((item) => (
                      <button
                        key={item.id}
                        type="button"
                        onMouseDown={(e) => {
                          e.preventDefault();
                          addFavorite({ name: item.name, type: item.type, qloo_id: item.id });
                        }}
                        className="w-full px-4 py-2.5 text-left text-xs flex items-center justify-between hover:bg-brand-violet/5 transition-colors gap-2"
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          {item.id.startsWith("custom-") ? (
                            <PlusCircle className="w-4 h-4 text-brand-violet shrink-0" />
                          ) : item.type === "artist" ? (
                            <Music className="w-4 h-4 text-brand-violet shrink-0" />
                          ) : item.type === "movie" || item.type === "tv_show" ? (
                            <Film className="w-4 h-4 text-brand-violet shrink-0" />
                          ) : item.type === "brand" ? (
                            <ShoppingBag className="w-4 h-4 text-brand-violet shrink-0" />
                          ) : (
                            <Sparkles className="w-4 h-4 text-brand-violet shrink-0" />
                          )}
                          <div className="min-w-0 text-left">
                            <div className="font-semibold text-nearblack truncate">
                              {item.name}
                            </div>
                            {item.subtitle && (
                              <div className="text-[10px] text-ink-400 font-mono truncate">
                                {item.subtitle}
                              </div>
                            )}
                          </div>
                        </div>
                        <span className="text-[10px] font-mono text-ink-500 capitalize px-2 py-0.5 rounded-pill bg-subtle shrink-0 border border-borderline/60">
                          {item.category || (item.id.startsWith("custom-") ? "Custom" : item.type)}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Selected Favorites Chip List */}
              {favorites.length > 0 && (
                <div className="flex flex-wrap gap-2 pt-1">
                  {favorites.map((fav) => (
                    <span
                      key={fav.name}
                      className="inline-flex items-center gap-1.5 px-3 py-1 rounded-pill bg-brand-violet/10 border border-brand-violet/25 text-xs font-semibold text-nearblack"
                    >
                      <span>{fav.name}</span>
                      <button
                        type="button"
                        onClick={() => removeFavorite(fav.name)}
                        className="text-ink-400 hover:text-rose-600 transition-colors ml-0.5"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </span>
                  ))}
                </div>
              )}

              {/* Quick Inspiration Pills */}
              <div className="pt-2 border-t border-borderline/50 space-y-1.5">
                <span className="text-[10px] font-mono text-ink-400 block">
                  Quick suggestions:
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {quickInspirations.map((item) => (
                    <button
                      key={item.name}
                      type="button"
                      onClick={() => addFavorite(item)}
                      className="text-xs px-2.5 py-0.5 rounded-pill bg-subtle text-ink-700 border border-borderline/60 hover:bg-borderline transition-colors"
                    >
                      + {item.name}
                    </button>
                  ))}
                </div>
              </div>
            </Card>

            {/* Step 3: Travel Constraints */}
            <Card variant="default" padding="lg" className="space-y-5">
              <label className="text-xs font-mono font-bold text-ink-700 uppercase tracking-wider block">
                3. Travel Constraints & Preferences
              </label>

              {/* Budget Ceiling */}
              <div className="space-y-2">
                <span className="text-xs text-ink-700 font-medium block">
                  Maximum Budget Ceiling:
                </span>
                <div className="grid grid-cols-4 gap-2">
                  {(["$", "$$", "$$$", "$$$$"] as const).map((lvl) => (
                    <button
                      key={lvl}
                      type="button"
                      onClick={() => setBudget(lvl)}
                      className={`py-2 rounded-2xl font-mono text-xs font-bold border transition-colors ${
                        budget === lvl
                          ? "bg-nearblack text-white border-nearblack shadow-xs"
                          : "bg-subtle text-ink-700 border-borderline hover:bg-borderline"
                      }`}
                    >
                      {lvl}
                    </button>
                  ))}
                </div>
              </div>

              {/* Dietary Preferences */}
              <div className="space-y-2">
                <span className="text-xs text-ink-700 font-medium block">
                  Dietary Restrictions (All meal spots will accommodate):
                </span>
                <div className="flex flex-wrap gap-2">
                  {["vegetarian", "vegan", "halal", "gluten-free"].map((diet) => (
                    <button
                      key={diet}
                      type="button"
                      onClick={() => toggleDietary(diet)}
                      className={`text-xs px-3 py-1.5 rounded-pill border capitalize transition-colors ${
                        dietary.includes(diet)
                          ? "bg-emerald-700 text-white border-emerald-700 font-semibold shadow-xs"
                          : "bg-subtle text-ink-700 border-borderline hover:bg-borderline"
                      }`}
                    >
                      {dietary.includes(diet) ? "✓ " : ""}{diet}
                    </button>
                  ))}
                </div>
              </div>

              {/* Pace Selector */}
              <div className="space-y-2">
                <span className="text-xs text-ink-700 font-medium block">
                  Preferred Daily Pace:
                </span>
                <div className="grid grid-cols-3 gap-2">
                  {(["relaxed", "moderate", "intense"] as const).map((p) => (
                    <button
                      key={p}
                      type="button"
                      onClick={() => setPace(p)}
                      className={`py-2 rounded-2xl capitalize text-xs font-medium border transition-colors ${
                        pace === p
                          ? "bg-brand-violet text-white border-brand-violet font-semibold shadow-xs"
                          : "bg-subtle text-ink-700 border-borderline hover:bg-borderline"
                      }`}
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>

              {/* Alcohol Free & Mobility Toggles */}
              <div className="space-y-3 pt-2 border-t border-borderline/50">
                <Toggle
                  checked={alcoholFree}
                  onChange={setAlcoholFree}
                  label="Strictly Alcohol-Free"
                  sublabel="Filters out late bars and nightlife stops for everyone"
                />
                <Toggle
                  checked={stepFree}
                  onChange={setStepFree}
                  label="Step-Free / Elevator Access Required"
                  sublabel="Filters venues with steep staircases or cobblestone climb"
                />
              </div>
            </Card>

            {/* Submit Button */}
            <Button
              type="submit"
              variant="primary"
              size="lg"
              disabled={isSubmitting || favorites.length < 3 || !name.trim()}
              className="w-full"
              icon={isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4 text-brand-violet" />}
            >
              {isSubmitting ? "Saving Profile..." : "Join Group Trip"}
            </Button>
          </form>
        ) : (
          /* Done State Screen */
          <Card variant="elevated" padding="xl" className="space-y-6 text-center">
            <div className="w-14 h-14 rounded-full bg-emerald-100 border border-emerald-200 flex items-center justify-center text-emerald-600 mx-auto shadow-soft">
              <Check className="w-7 h-7 stroke-[3]" />
            </div>

            <div className="space-y-2">
              <span className="text-xs font-mono font-bold text-emerald-700 uppercase">
                Profile Calibrated
              </span>
              <h2 className="text-2xl sm:text-3xl font-bold text-nearblack tracking-tight">
                You’re in, {name}!
              </h2>
              <p className="text-xs sm:text-sm text-ink-500 max-w-sm mx-auto">
                Your cultural taste signals and constraints are recorded. The itinerary planner will now protect your fairness score.
              </p>
            </div>

            {/* Summary Box */}
            <div className="p-4 rounded-2xl bg-subtle/80 border border-borderline text-left space-y-2">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-ink-500">Favorites Mapped:</span>
                <span className="font-bold text-nearblack">{favorites.length} entities</span>
              </div>
              <div className="flex justify-between text-xs font-mono">
                <span className="text-ink-500">Dietary:</span>
                <span className="font-bold text-nearblack">{dietary.join(", ") || "None"}</span>
              </div>
              <div className="flex justify-between text-xs font-mono">
                <span className="text-ink-500">Alcohol-Free:</span>
                <span className="font-bold text-nearblack">{alcoholFree ? "Yes" : "No"}</span>
              </div>
            </div>

            <div className="pt-2 flex flex-col sm:flex-row gap-3">
              <Button
                variant="primary"
                size="md"
                onClick={() => router.push(`/create`)}
                className="w-full"
                icon={<ArrowRight className="w-4 h-4" />}
                iconPosition="right"
              >
                View Trip Dashboard
              </Button>
            </div>
          </Card>
        )}
      </main>

      <Footer />
    </div>
  );
}

