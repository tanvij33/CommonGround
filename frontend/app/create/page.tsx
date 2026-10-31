"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Navbar } from "@/components/landing/Navbar";
import { Footer } from "@/components/landing/Footer";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Chip } from "@/components/ui/Chip";
import { QRCodeCanvas } from "@/components/ui/QRCodeCanvas";
import { Toast } from "@/components/ui/Toast";
import {
  api,
  Trip,
  CulturalFavorite,
  AutocompleteEntity,
  DestinationResult,
} from "@/lib/api";
import { DestinationAutocomplete } from "@/components/ui/DestinationAutocomplete";
import {
  Compass,
  MapPin,
  Calendar,
  Users,
  Copy,
  Check,
  QrCode,
  ArrowRight,
  Sparkles,
  Loader2,
  RefreshCw,
  PlusCircle,
  AlertCircle,
  Search,
  Music,
  Film,
  ShoppingBag,
  X,
} from "lucide-react";

export default function CreateTripPage() {
  const router = useRouter();

  // Basic Form State
  const [tripName, setTripName] = useState("Lisbon Cultural Tour");
  const [destination, setDestination] = useState<DestinationResult | null>({
    id: "default-lisbon",
    name: "Lisbon",
    label: "Lisbon, Portugal",
    query: "Lisbon",
  });
  const [days, setDays] = useState(2);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Organizer Cultural Favorites State
  const [includeOrganizerTaste, setIncludeOrganizerTaste] = useState(true);
  const [organizerName, setOrganizerName] = useState("");
  const [favSearchQuery, setFavSearchQuery] = useState("");
  const [favTypeFilter, setFavTypeFilter] = useState("all");
  const [favSearchResults, setFavSearchResults] = useState<AutocompleteEntity[]>([]);
  const [isSearchingFavs, setIsSearchingFavs] = useState(false);
  const [isFavDropdownOpen, setIsFavDropdownOpen] = useState(false);
  const favDropdownRef = useRef<HTMLDivElement>(null);
  const [organizerFavorites, setOrganizerFavorites] = useState<CulturalFavorite[]>([
    { name: "Burial", type: "artist" },
    { name: "Aesop", type: "brand" },
    { name: "Specialty Coffee", type: "place" },
  ]);

  // Created Trip State
  const [createdTrip, setCreatedTrip] = useState<Trip | null>(null);
  const [inviteUrl, setInviteUrl] = useState<string>("");
  const [copied, setCopied] = useState(false);
  const [showQr, setShowQr] = useState(false);
  const [isPolling, setIsPolling] = useState(false);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const quickCities = ["Lisbon", "Tokyo", "Delhi", "Berlin", "Paris", "New York", "Barcelona", "Kyoto"];

  const quickInspirations = [
    { name: "Radiohead", type: "artist" },
    { name: "Wes Anderson", type: "movie" },
    { name: "Studio Ghibli", type: "movie" },
    { name: "Daft Punk", type: "artist" },
    { name: "Natural Wine Bars", type: "place" },
    { name: "Acne Studios", type: "brand" },
  ];

  // Close dropdowns when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (favDropdownRef.current && !favDropdownRef.current.contains(e.target as Node)) {
        setIsFavDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Responsive search for cultural favorites
  useEffect(() => {
    let isMounted = true;
    setIsSearchingFavs(true);

    const timer = setTimeout(async () => {
      try {
        const results = await api.searchEntities(favSearchQuery.trim(), favTypeFilter);
        if (isMounted) setFavSearchResults(results);
      } catch {
        if (isMounted) setFavSearchResults([]);
      } finally {
        if (isMounted) setIsSearchingFavs(false);
      }
    }, 50);

    return () => {
      isMounted = false;
      clearTimeout(timer);
    };
  }, [favSearchQuery, favTypeFilter]);

  // Poll for joined members every 3.5 seconds once trip is created
  useEffect(() => {
    if (!createdTrip?.id) return;

    let isMounted = true;
    const interval = setInterval(async () => {
      try {
        setIsPolling(true);
        const updated = await api.getTrip(createdTrip.id);
        if (isMounted) {
          setCreatedTrip(updated);
        }
      } catch {
        // Silent catch
      } finally {
        if (isMounted) setIsPolling(false);
      }
    }, 3500);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [createdTrip?.id]);

  const selectDestination = (city: DestinationResult | null) => {
    setDestination(city);
    if (!city) return;
    if (tripName === "Lisbon Cultural Tour" || tripName.endsWith("Cultural Tour")) {
      setTripName(`${city.name} Cultural Tour`);
    }
  };

  const addOrganizerFavorite = (entity: { name: string; type?: string; qloo_id?: string }) => {
    if (organizerFavorites.some((f) => f.name.toLowerCase() === entity.name.toLowerCase())) return;
    if (organizerFavorites.length >= 8) {
      setToastMsg("Maximum of 8 favorites reached for balanced weighting.");
      return;
    }
    setOrganizerFavorites([
      ...organizerFavorites,
      { name: entity.name, type: entity.type, qloo_id: entity.qloo_id },
    ]);
    setFavSearchQuery("");
    setIsFavDropdownOpen(false);
  };

  const handleAddOrganizerDirect = () => {
    const clean = favSearchQuery.trim();
    if (!clean) return;
    addOrganizerFavorite({
      name: clean,
      type: favTypeFilter === "all" ? "cultural_entity" : favTypeFilter,
    });
  };

  const handleFavKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      if (favSearchResults.length > 0 && favSearchQuery.trim()) {
        const top = favSearchResults[0];
        addOrganizerFavorite({ name: top.name, type: top.type, qloo_id: top.id });
      } else if (favSearchQuery.trim()) {
        handleAddOrganizerDirect();
      }
    }
  };

  const removeOrganizerFavorite = (favName: string) => {
    setOrganizerFavorites(organizerFavorites.filter((f) => f.name !== favName));
  };

  const handleCreateTrip = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tripName.trim()) {
      setErrorMsg("Please enter a trip name.");
      return;
    }
    if (!destination) {
      setErrorMsg("Please search for and select a destination from the suggestions.");
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      const res = await api.createTrip({
        name: tripName.trim(),
        destination: destination.name,
        destination_query: destination.query,
        days: Number(days),
      });

      const fullInviteUrl = `${window.location.origin}/join/${res.id}`;
      setInviteUrl(fullInviteUrl);

      // Save organizer's profile if entered
      if (includeOrganizerTaste && organizerFavorites.length > 0) {
        try {
          await api.addProfile(res.id, {
            name: organizerName.trim() || "You (Organizer)",
            favorites: organizerFavorites,
            constraints: { budget: "$$", pace: "moderate" },
          });
        } catch {
          // Silent catch
        }
      }

      // Fetch newly created trip
      const tripData = await api.getTrip(res.id);
      setCreatedTrip(tripData);
      setToastMsg("Trip created successfully! Share the invite link with your group.");
    } catch {
      // Never fake a trip: an invite link to a trip the backend doesn't know about is useless
      setErrorMsg("Could not create the trip. Check that the backend is running and try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const copyToClipboard = () => {
    if (!inviteUrl) return;
    navigator.clipboard.writeText(inviteUrl);
    setCopied(true);
    setToastMsg("Invite link copied to clipboard!");
    setTimeout(() => setCopied(false), 2500);
  };

  const handleAddDemoFriends = async () => {
    if (!createdTrip) return;
    try {
      // Demo friends are saved to THIS trip on the backend, then the roster is re-read from it
      const res = await api.addDemoProfiles(createdTrip.id);
      const updated = await api.getTrip(createdTrip.id);
      setCreatedTrip(updated);
      setToastMsg(res.added_count > 0 ? `${res.added_count} demo friends added to this trip!` : "Demo friends are already on this trip.");
    } catch (err: any) {
      setToastMsg(`Could not add demo friends: ${err?.message || "backend unavailable"}`);
    }
  };

  const handleStartPlanning = () => {
    if (!createdTrip) return;
    router.push(`/trip/${createdTrip.id}/generating`);
  };

  return (
    <div className="min-h-screen bg-offwhite text-nearblack flex flex-col">
      <Navbar />

      <main className="flex-1 py-12 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto w-full space-y-8">
        {/* Toast Notification */}
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

        {/* Header */}
        <div className="space-y-2 text-center sm:text-left">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-pill bg-brand-violet/10 border border-brand-violet/20 text-brand-violet text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Step 1: Create Group Trip</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-nearblack">
            Plan a new group trip
          </h1>
          <p className="text-sm sm:text-base text-ink-500">
            Set your destination, add your favorites, and invite your crew to balance everyone’s taste.
          </p>
        </div>

        {/* Phase A: Create Trip Form */}
        {!createdTrip ? (
          <Card variant="elevated" padding="xl" className="space-y-6">
            <form onSubmit={handleCreateTrip} className="space-y-6">
              {/* Trip Name */}
              <div className="space-y-2">
                <label className="text-xs font-mono font-bold text-ink-700 uppercase tracking-wider block">
                  Trip Title
                </label>
                <Input
                  value={tripName}
                  onChange={(e) => setTripName(e.target.value)}
                  placeholder="e.g. Lisbon Design & Dining Tour"
                  required
                />
              </div>

              {/* Destination Input & Typeahead Dropdown */}
              <DestinationAutocomplete
                selected={destination}
                onSelect={selectDestination}
                quickCities={quickCities}
              />

              {/* Trip Duration */}
              <div className="space-y-2">
                <label className="text-xs font-mono font-bold text-ink-700 uppercase tracking-wider block">
                  Trip Duration (Days)
                </label>
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => setDays(Math.max(1, days - 1))}
                    className="w-10 h-10 rounded-full bg-subtle border border-borderline flex items-center justify-center font-bold text-base hover:bg-borderline transition-colors"
                  >
                    -
                  </button>
                  <span className="w-12 text-center font-mono font-bold text-lg text-nearblack">
                    {days}
                  </span>
                  <button
                    type="button"
                    onClick={() => setDays(Math.min(14, days + 1))}
                    className="w-10 h-10 rounded-full bg-subtle border border-borderline flex items-center justify-center font-bold text-base hover:bg-borderline transition-colors"
                  >
                    +
                  </button>
                  <span className="text-xs text-ink-500 font-mono">
                    {days === 1 ? "1 Day Quick Hit" : `${days} Days Curated Itinerary`}
                  </span>
                </div>
              </div>

              {/* Organizer Cultural Taste Section */}
              <div className="p-5 rounded-3xl bg-subtle/50 border border-borderline space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-brand-violet" />
                    <span className="text-xs font-mono font-bold text-nearblack uppercase tracking-wider">
                      Add Your Cultural Favorites (Organizer)
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setIncludeOrganizerTaste(!includeOrganizerTaste)}
                    className="text-xs font-mono text-brand-violet hover:underline font-semibold"
                  >
                    {includeOrganizerTaste ? "Enabled ✓" : "Skip"}
                  </button>
                </div>

                {includeOrganizerTaste && (
                  <div className="space-y-3.5">
                    <p className="text-xs text-ink-500 leading-relaxed">
                      Add a few musicians, directors, brands, or places you love. Qloo translates these into dining and activity affinities.
                    </p>

                    {/* Organizer Name */}
                    <div className="space-y-1">
                      <label className="text-[11px] font-mono text-ink-500 uppercase">
                        Your Name
                      </label>
                      <Input
                        value={organizerName}
                        onChange={(e) => setOrganizerName(e.target.value)}
                        placeholder="Organizer"
                      />
                    </div>

                    {/* Filter Pills */}
                    <div className="flex flex-wrap gap-1.5">
                      {[
                        { id: "all", label: "All" },
                        { id: "artist", label: "Music" },
                        { id: "movie", label: "Cinema" },
                        { id: "brand", label: "Brand" },
                        { id: "place", label: "Culture" },
                      ].map((t) => (
                        <button
                          key={t.id}
                          type="button"
                          onClick={() => setFavTypeFilter(t.id)}
                          className={`text-xs font-mono px-2.5 py-1 rounded-pill border transition-colors ${favTypeFilter === t.id
                              ? "bg-nearblack text-white border-nearblack font-semibold"
                              : "bg-white text-ink-600 border-borderline hover:bg-borderline"
                            }`}
                        >
                          {t.label}
                        </button>
                      ))}
                    </div>

                    {/* Favorites Autocomplete Search with Direct Add */}
                    <div className="relative" ref={favDropdownRef}>
                      <div className="flex items-center gap-2">
                        <div className="relative flex-1">
                          <Input
                            icon={
                              isSearchingFavs ? (
                                <Loader2 className="w-4 h-4 animate-spin text-brand-violet" />
                              ) : (
                                <Search className="w-4 h-4 text-ink-400" />
                              )
                            }
                            value={favSearchQuery}
                            onFocus={() => setIsFavDropdownOpen(true)}
                            onChange={(e) => {
                              setFavSearchQuery(e.target.value);
                              setIsFavDropdownOpen(true);
                            }}
                            onKeyDown={handleFavKeyDown}
                            placeholder="Type artist, movie, brand, place (e.g. Radiohead)..."
                          />
                        </div>
                        <Button
                          type="button"
                          variant="secondary"
                          size="md"
                          onClick={handleAddOrganizerDirect}
                          disabled={!favSearchQuery.trim()}
                          icon={<PlusCircle className="w-4 h-4 text-brand-violet" />}
                        >
                          Add
                        </Button>
                      </div>

                      {/* Autocomplete Dropdown List */}
                      {isFavDropdownOpen && favSearchResults.length > 0 && (
                        <div className="absolute top-full left-0 right-0 mt-1.5 z-50 bg-white rounded-2xl border border-borderline shadow-float max-h-64 overflow-y-auto divide-y divide-borderline/40">
                          <div className="px-3.5 py-1.5 text-[10px] font-mono text-ink-400 bg-subtle/60 flex items-center justify-between sticky top-0 z-10 backdrop-blur-sm">
                            <span>
                              {favSearchQuery.trim()
                                ? `Found ${favSearchResults.length} matches for "${favSearchQuery.trim()}"`
                                : `Popular tastes (${favTypeFilter === "all" ? "All" : favTypeFilter})`}
                            </span>
                            <span className="text-brand-violet font-semibold">Click to add</span>
                          </div>
                          {favSearchResults.map((item) => (
                            <button
                              key={item.id}
                              type="button"
                              onMouseDown={(e) => {
                                e.preventDefault();
                                addOrganizerFavorite(item);
                              }}
                              className="w-full px-4 py-2.5 text-left text-xs hover:bg-brand-violet/5 transition-colors flex items-center justify-between gap-3"
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

                    {/* Selected Favorites Chips */}
                    {organizerFavorites.length > 0 && (
                      <div className="flex flex-wrap gap-2 pt-1">
                        {organizerFavorites.map((fav) => (
                          <span
                            key={fav.name}
                            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-pill bg-brand-violet/10 border border-brand-violet/20 text-xs font-semibold text-nearblack"
                          >
                            <span>{fav.name}</span>
                            <button
                              type="button"
                              onClick={() => removeOrganizerFavorite(fav.name)}
                              className="text-ink-400 hover:text-rose-600 transition-colors ml-0.5"
                            >
                              <X className="w-3.5 h-3.5" />
                            </button>
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Quick Inspirations */}
                    <div className="space-y-1.5 pt-1">
                      <span className="text-[10px] font-mono text-ink-400 block">
                        Quick suggestions:
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {quickInspirations.map((item) => (
                          <button
                            key={item.name}
                            type="button"
                            onClick={() => addOrganizerFavorite(item)}
                            className="text-xs px-2.5 py-0.5 rounded-pill bg-white text-ink-700 border border-borderline/80 hover:bg-borderline transition-colors"
                          >
                            + {item.name}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Error Message */}
              {errorMsg && (
                <div className="p-3.5 rounded-2xl bg-rose-50 border border-rose-200 text-xs text-rose-600 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{errorMsg}</span>
                </div>
              )}

              {/* Submit CTA */}
              <Button
                type="submit"
                variant="primary"
                size="lg"
                disabled={isSubmitting}
                className="w-full"
                icon={
                  isSubmitting ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Sparkles className="w-4 h-4 text-brand-violet" />
                  )
                }
              >
                {isSubmitting ? "Creating Trip..." : "Create Trip & Get Invite Link"}
              </Button>
            </form>
          </Card>
        ) : (
          /* Phase B: Trip Created - Invite & Live Waiting Room */
          <div className="space-y-6">
            <Card variant="elevated" padding="xl" className="space-y-6">
              {/* Trip Heading */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-borderline">
                <div>
                  <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-pill bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-semibold mb-2">
                    <Check className="w-3 h-3" />
                    <span>Trip Created</span>
                  </div>
                  <h2 className="text-2xl sm:text-3xl font-bold text-nearblack tracking-tight">
                    {createdTrip.name}
                  </h2>
                  <p className="text-xs font-mono text-ink-500 mt-1">
                    Destination: {createdTrip.destination} • {createdTrip.days} Days Curated Itinerary
                  </p>
                </div>

                <Button
                  variant="primary"
                  size="md"
                  onClick={handleStartPlanning}
                  icon={<Sparkles className="w-4 h-4 text-brand-violet" />}
                >
                  Start Planning
                </Button>
              </div>

              {/* Invite Link & QR Sharing */}
              <div className="p-5 rounded-3xl bg-subtle/80 border border-borderline space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-ink-700 uppercase tracking-wider">
                    Share Invite Link with Friends
                  </span>
                  <button
                    onClick={() => setShowQr(!showQr)}
                    className="text-xs font-mono text-brand-violet hover:underline flex items-center gap-1 font-semibold"
                  >
                    <QrCode className="w-3.5 h-3.5" />
                    {showQr ? "Hide QR" : "Show QR Code"}
                  </button>
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    readOnly
                    value={inviteUrl}
                    className="flex-1 rounded-pill bg-white border border-borderline px-4 py-2.5 text-xs font-mono text-nearblack select-all"
                  />
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={copyToClipboard}
                    icon={
                      copied ? (
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )
                    }
                  >
                    {copied ? "Copied!" : "Copy Link"}
                  </Button>
                </div>

                {showQr && (
                  <div className="pt-2 flex flex-col items-center justify-center p-6 bg-white rounded-2xl border border-borderline/60">
                    <QRCodeCanvas value={inviteUrl} size={180} />
                    <p className="text-xs font-mono text-ink-400 mt-3 text-center">
                      Point phone camera at code to join in 30 seconds
                    </p>
                  </div>
                )}
              </div>

              {/* Joined Friends List */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Users className="w-4 h-4 text-brand-violet" />
                    <h3 className="text-sm font-mono font-bold text-nearblack uppercase tracking-wider">
                      Who Has Joined ({createdTrip.members?.length || 0})
                    </h3>
                    {isPolling && (
                      <RefreshCw className="w-3 h-3 text-ink-400 animate-spin" />
                    )}
                  </div>
                  <button
                    onClick={handleAddDemoFriends}
                    className="text-xs font-mono text-brand-violet hover:underline flex items-center gap-1 font-semibold"
                  >
                    <PlusCircle className="w-3.5 h-3.5" />
                    + Add 4 Demo Friends
                  </button>
                </div>

                {(!createdTrip.members || createdTrip.members.length === 0) ? (
                  <div className="p-8 rounded-3xl bg-subtle/40 border border-borderline text-center space-y-2">
                    <p className="text-sm text-ink-600 font-medium">
                      Waiting for travelers to join...
                    </p>
                    <p className="text-xs text-ink-400 font-mono">
                      Send the invite link to your friends, or click "+ Add 4 Demo Friends" to test immediately.
                    </p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {createdTrip.members.map((member, idx) => (
                      <div
                        key={member.id || member.name || idx}
                        className="p-4 rounded-2xl bg-subtle/50 border border-borderline space-y-2"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-bold text-nearblack">
                            {member.name}
                          </span>
                          <span className="text-[11px] font-mono text-ink-400">
                            {member.constraints?.budget || "$$"} • {member.constraints?.pace || "moderate"}
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {member.favorites?.slice(0, 3).map((f) => (
                            <span
                              key={f.name}
                              className="text-xs px-2.5 py-0.5 rounded-pill bg-white border border-borderline/60 text-ink-700"
                            >
                              {f.name}
                            </span>
                          ))}
                          {(member.favorites?.length || 0) > 3 && (
                            <span className="text-xs px-2 py-0.5 text-ink-400 font-mono">
                              +{member.favorites.length - 3} more
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Ready to generate banner */}
              <div className="p-5 rounded-3xl bg-gradient-to-r from-brand-violet/10 via-brand-cyan/10 to-transparent border border-brand-violet/20 flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="space-y-1 text-center sm:text-left">
                  <h4 className="text-sm font-bold text-nearblack">
                    Ready to calibrate everyone’s taste?
                  </h4>
                  <p className="text-xs text-ink-500">
                    Qloo will evaluate cultural affinities, run fairness checks, and produce a balanced schedule.
                  </p>
                </div>
                <Button
                  variant="primary"
                  size="lg"
                  onClick={handleStartPlanning}
                  icon={<ArrowRight className="w-4 h-4" />}
                >
                  Generate Taste-Fair Itinerary
                </Button>
              </div>
            </Card>
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}
