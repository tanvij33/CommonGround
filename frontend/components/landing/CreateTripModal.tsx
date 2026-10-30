"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
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
  TravelerConstraints,
} from "@/lib/api";
import {
  searchDestinations,
  DestinationCity,
} from "@/lib/autocompleteData";
import {
  X,
  Sparkles,
  MapPin,
  Calendar,
  Users,
  Copy,
  Check,
  QrCode,
  ArrowRight,
  Loader2,
  RefreshCw,
  PlusCircle,
  AlertCircle,
  Search,
  Music,
  Film,
  ShoppingBag,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

export interface CreateTripModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CreateTripModal: React.FC<CreateTripModalProps> = ({ isOpen, onClose }) => {
  const router = useRouter();

  // Basic Form State
  const [tripName, setTripName] = useState("Lisbon Cultural Tour");
  const [destination, setDestination] = useState("Lisbon");
  const [days, setDays] = useState(2);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Destination Autocomplete State
  const [showDestDropdown, setShowDestDropdown] = useState(false);
  const [destMatches, setDestMatches] = useState<DestinationCity[]>([]);
  const destDropdownRef = useRef<HTMLDivElement>(null);

  // Organizer Taste Profile State (Inline Cultural Favorites)
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

  // Update destination typeahead matches
  useEffect(() => {
    const results = searchDestinations(destination);
    setDestMatches(results);
  }, [destination]);

  // Close dropdowns when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (destDropdownRef.current && !destDropdownRef.current.contains(e.target as Node)) {
        setShowDestDropdown(false);
      }
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

  // Poll for joined members every 3.5s once created
  useEffect(() => {
    if (!isOpen || !createdTrip?.id) return;

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
  }, [isOpen, createdTrip?.id]);

  const selectDestination = (city: DestinationCity) => {
    setDestination(city.name);
    setShowDestDropdown(false);
    // Auto-update trip title if user kept standard default
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
    if (!tripName.trim() || !destination.trim()) {
      setErrorMsg("Please enter both a trip name and a destination.");
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      // 1. Create the Trip
      const res = await api.createTrip({
        name: tripName.trim(),
        destination: destination.trim(),
        days: Number(days),
      });

      const fullInviteUrl = `${window.location.origin}/join/${res.id}`;
      setInviteUrl(fullInviteUrl);

      // 2. If organizer included taste favorites, save their profile immediately
      if (includeOrganizerTaste && organizerFavorites.length > 0) {
        try {
          await api.addProfile(res.id, {
            name: organizerName.trim() || "You (Organizer)",
            favorites: organizerFavorites,
            constraints: { budget: "$$", pace: "moderate" },
          });
        } catch {
          // Profile save fallback
        }
      }

      // 3. Fetch latest trip state
      const tripData = await api.getTrip(res.id);
      setCreatedTrip(tripData);
      setToastMsg("Trip created! Share the invite link with your crew.");
    } catch {
      // Fallback for offline / mock mode
      const mockId = `trip-${Math.random().toString(36).substring(2, 9)}`;
      const fullInviteUrl = `${window.location.origin}/join/${mockId}`;
      setInviteUrl(fullInviteUrl);
      const members: any[] = [];
      if (includeOrganizerTaste && organizerFavorites.length > 0) {
        members.push({
          id: "prof-creator",
          name: organizerName.trim() || "You (Organizer)",
          favorites: organizerFavorites,
          constraints: { budget: "$$", pace: "moderate" },
        });
      }
      setCreatedTrip({
        id: mockId,
        name: tripName,
        destination,
        days,
        status: "waiting",
        members,
      });
      setToastMsg("Created in offline/mock mode.");
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
      const demoRes = await api.createDemoTrip();
      const demoData = await api.getTrip(demoRes.trip_id);
      setCreatedTrip({
        ...createdTrip,
        members: [...(createdTrip.members || []), ...demoData.members],
      });
      setToastMsg("4 demo friends added!");
    } catch {
      // Offline fallback
      setCreatedTrip({
        ...createdTrip,
        members: [
          ...(createdTrip.members || []),
          {
            name: "Aisha",
            favorites: [{ name: "Burial", type: "artist" }, { name: "Aesop", type: "brand" }],
            constraints: { budget: "$$", dietary: ["vegetarian"], pace: "moderate" },
          },
          {
            name: "Rohan",
            favorites: [{ name: "Metallica", type: "artist" }, { name: "Nike", type: "brand" }],
            constraints: { budget: "$$$", pace: "intense" },
          },
          {
            name: "Meera",
            favorites: [{ name: "Norah Jones", type: "artist" }],
            constraints: { budget: "$$", alcohol_free: true, pace: "relaxed" },
          },
          {
            name: "Kabir",
            favorites: [{ name: "Taylor Swift", type: "artist" }],
            constraints: { budget: "$$", pace: "moderate" },
          },
        ],
      });
      setToastMsg("4 demo friends added in offline mode!");
    }
  };

  const handleStartPlanning = () => {
    if (!createdTrip) return;
    router.push(`/trip/${createdTrip.id}/generating`);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-nearblack/60 backdrop-blur-md overflow-y-auto select-none">
      <div className="relative w-full max-w-2xl rounded-3xl bg-white border border-borderline shadow-float my-8 flex flex-col max-h-[92vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-borderline bg-subtle/50">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-brand-violet" />
            <h3 className="text-base font-bold text-nearblack tracking-tight">
              {createdTrip ? "Trip Ready • Invite Friends" : "Create New Trip"}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-full hover:bg-subtle text-ink-400 hover:text-nearblack transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto space-y-6">
          {!createdTrip ? (
            <form onSubmit={handleCreateTrip} className="space-y-5">
              {/* Trip Name */}
              <div className="space-y-1.5">
                <label className="text-xs font-mono font-bold text-ink-700 uppercase tracking-wider block">
                  Trip Name
                </label>
                <Input
                  value={tripName}
                  onChange={(e) => setTripName(e.target.value)}
                  placeholder="e.g. Lisbon Architecture & Dining"
                  required
                />
              </div>

              {/* Destination City with Autocomplete Suggestions */}
              <div className="space-y-1.5 relative" ref={destDropdownRef}>
                <div className="flex items-center justify-between">
                  <label className="text-xs font-mono font-bold text-ink-700 uppercase tracking-wider block">
                    Destination City
                  </label>
                  <span className="text-[11px] font-mono text-ink-400">
                    Type for autocomplete
                  </span>
                </div>

                <Input
                  icon={<MapPin className="w-4 h-4 text-brand-violet" />}
                  value={destination}
                  onFocus={() => setShowDestDropdown(true)}
                  onChange={(e) => {
                    setDestination(e.target.value);
                    setShowDestDropdown(true);
                  }}
                  placeholder="e.g. Lisbon, Tokyo, Berlin, Paris, New York..."
                  required
                />

                {/* Destination Dropdown Options */}
                {showDestDropdown && destMatches.length > 0 && (
                  <div className="absolute top-full left-0 right-0 mt-1.5 z-40 bg-white/95 backdrop-blur-md rounded-2xl border border-borderline shadow-float max-h-56 overflow-y-auto divide-y divide-borderline/40">
                    {destMatches.map((city) => (
                      <button
                        key={`${city.name}-${city.country}`}
                        type="button"
                        onClick={() => selectDestination(city)}
                        className="w-full px-4 py-2.5 text-left text-xs hover:bg-brand-violet/5 transition-colors flex items-center justify-between gap-2"
                      >
                        <div className="space-y-0.5 min-w-0">
                          <div className="flex items-center gap-1.5">
                            <span className="font-semibold text-nearblack">
                              {city.name}
                            </span>
                            <span className="text-ink-400 text-[11px]">
                              • {city.country}
                            </span>
                          </div>
                          <div className="text-[10px] text-ink-400 font-mono truncate">
                            {city.vibes.slice(0, 3).join(" • ")}
                          </div>
                        </div>
                        <span className="text-[10px] font-mono text-brand-violet px-2 py-0.5 rounded-pill bg-brand-violet/10 shrink-0">
                          Select
                        </span>
                      </button>
                    ))}
                  </div>
                )}

                {/* Popular Pills */}
                <div className="flex flex-wrap items-center gap-1.5 pt-1">
                  <span className="text-[10px] font-mono text-ink-400 mr-1">Popular:</span>
                  {quickCities.map((c) => (
                    <button
                      key={c}
                      type="button"
                      onClick={() => {
                        setDestination(c);
                        if (tripName === "Lisbon Cultural Tour" || tripName.endsWith("Cultural Tour")) {
                          setTripName(`${c} Cultural Tour`);
                        }
                      }}
                      className={`text-xs px-2.5 py-0.5 rounded-pill border transition-colors ${destination.toLowerCase() === c.toLowerCase()
                        ? "bg-brand-violet text-white border-brand-violet font-semibold"
                        : "bg-subtle text-ink-700 border-borderline hover:bg-borderline"
                        }`}
                    >
                      {c}
                    </button>
                  ))}
                </div>
              </div>

              {/* Duration (Days) */}
              <div className="space-y-1.5">
                <label className="text-xs font-mono font-bold text-ink-700 uppercase tracking-wider block">
                  Duration (Days)
                </label>
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => setDays(Math.max(1, days - 1))}
                    className="w-9 h-9 rounded-full bg-subtle border border-borderline flex items-center justify-center font-bold text-base hover:bg-borderline transition-colors"
                  >
                    -
                  </button>
                  <span className="w-10 text-center font-mono font-bold text-base text-nearblack">
                    {days}
                  </span>
                  <button
                    type="button"
                    onClick={() => setDays(Math.min(14, days + 1))}
                    className="w-9 h-9 rounded-full bg-subtle border border-borderline flex items-center justify-center font-bold text-base hover:bg-borderline transition-colors"
                  >
                    +
                  </button>
                  <span className="text-xs text-ink-500 font-mono">
                    {days === 1 ? "1 Day Quick Trip" : `${days} Days Itinerary`}
                  </span>
                </div>
              </div>

              {/* Inline Cultural Favorites for Trip Organizer */}
              <div className="p-4 rounded-2xl bg-subtle/50 border border-borderline space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-brand-violet" />
                    <span className="text-xs font-mono font-bold text-nearblack uppercase tracking-wider">
                      Your Cultural Favorites (Organizer)
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setIncludeOrganizerTaste(!includeOrganizerTaste)}
                    className="text-xs font-mono text-brand-violet hover:underline flex items-center gap-1 font-semibold"
                  >
                    {includeOrganizerTaste ? "Enabled ✓" : "Skip"}
                  </button>
                </div>

                {includeOrganizerTaste && (
                  <div className="space-y-3 pt-1">
                    <p className="text-xs text-ink-500 leading-relaxed">
                      Add artists, movies, brands, or places you love so Qloo balances your taste with your friends’.
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

                    {/* Category Filter Pills */}
                    <div className="flex flex-wrap gap-1">
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
                          className={`text-[10px] font-mono px-2 py-0.5 rounded-pill border transition-colors ${favTypeFilter === t.id
                            ? "bg-nearblack text-white border-nearblack font-semibold"
                            : "bg-white text-ink-600 border-borderline hover:bg-borderline"
                            }`}
                        >
                          {t.label}
                        </button>
                      ))}
                    </div>

                    {/* Live Autocomplete Search Input with Direct Add */}
                    <div className="relative" ref={favDropdownRef}>
                      <div className="flex items-center gap-2">
                        <div className="relative flex-1">
                          <Input
                            icon={
                              isSearchingFavs ? (
                                <Loader2 className="w-3.5 h-3.5 animate-spin text-brand-violet" />
                              ) : (
                                <Search className="w-3.5 h-3.5 text-ink-400" />
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
                          icon={<PlusCircle className="w-3.5 h-3.5 text-brand-violet" />}
                        >
                          Add
                        </Button>
                      </div>

                      {/* Dropdown Options List */}
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

                    {/* Selected Cultural Favorites Chips */}
                    {organizerFavorites.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {organizerFavorites.map((fav) => (
                          <span
                            key={fav.name}
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-pill bg-brand-violet/10 border border-brand-violet/20 text-xs font-semibold text-nearblack"
                          >
                            <span>{fav.name}</span>
                            <button
                              type="button"
                              onClick={() => removeOrganizerFavorite(fav.name)}
                              className="text-ink-400 hover:text-rose-600 transition-colors"
                            >
                              <X className="w-3 h-3" />
                            </button>
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Quick Inspiration Suggestions */}
                    <div className="space-y-1 pt-1">
                      <span className="text-[10px] font-mono text-ink-400 block">
                        Quick suggestions:
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {quickInspirations.map((item) => (
                          <button
                            key={item.name}
                            type="button"
                            onClick={() => addOrganizerFavorite(item)}
                            className="text-[11px] px-2 py-0.5 rounded-pill bg-white text-ink-700 border border-borderline/80 hover:bg-borderline transition-colors"
                          >
                            + {item.name}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {errorMsg && (
                <div className="p-3 rounded-2xl bg-rose-50 border border-rose-200 text-xs text-rose-600 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{errorMsg}</span>
                </div>
              )}

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
          ) : (
            <div className="space-y-5">
              {/* Invite link card */}
              <div className="p-4 rounded-2xl bg-subtle/80 border border-borderline space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-base font-bold text-nearblack tracking-tight">
                      {createdTrip.name}
                    </h4>
                    <p className="text-xs text-ink-500 font-mono">
                      {createdTrip.destination} • {createdTrip.days} Days
                    </p>
                  </div>
                  <button
                    onClick={() => setShowQr(!showQr)}
                    className="text-xs font-mono text-brand-violet hover:underline flex items-center gap-1 font-semibold"
                  >
                    <QrCode className="w-3.5 h-3.5" />
                    {showQr ? "Hide QR" : "Show QR"}
                  </button>
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    readOnly
                    value={inviteUrl}
                    className="flex-1 rounded-pill bg-white border border-borderline px-3.5 py-2 text-xs font-mono text-nearblack select-all"
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
                    {copied ? "Copied" : "Copy"}
                  </Button>
                </div>

                {showQr && (
                  <div className="pt-2 flex flex-col items-center justify-center p-4 bg-white rounded-2xl border border-borderline/60">
                    <QRCodeCanvas value={inviteUrl} size={150} />
                    <p className="text-[11px] font-mono text-ink-400 mt-2">
                      Scan on mobile to join in 30 seconds
                    </p>
                  </div>
                )}
              </div>

              {/* Joined Friends List */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Users className="w-4 h-4 text-brand-violet" />
                    <h5 className="text-xs font-mono font-bold text-nearblack uppercase tracking-wider">
                      Who Has Joined ({createdTrip.members?.length || 0})
                    </h5>
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
                  <div className="p-4 rounded-2xl bg-subtle/40 border border-borderline text-center space-y-1">
                    <p className="text-xs text-ink-600 font-medium">
                      Waiting for travelers to join...
                    </p>
                    <p className="text-[11px] text-ink-400 font-mono">
                      Share the invite link above, or click "+ Add 4 Demo Friends" to test immediately.
                    </p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {createdTrip.members.map((member, idx) => (
                      <div
                        key={member.id || member.name || idx}
                        className="p-3 rounded-2xl bg-subtle/50 border border-borderline space-y-1.5"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-nearblack">
                            {member.name}
                          </span>
                          <span className="text-[10px] font-mono text-ink-400">
                            {member.constraints?.budget || "$$"} • {member.constraints?.pace || "moderate"}
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {member.favorites?.slice(0, 3).map((f) => (
                            <span
                              key={f.name}
                              className="text-[10px] px-2 py-0.5 rounded-pill bg-white border border-borderline/60 text-ink-700"
                            >
                              {f.name}
                            </span>
                          ))}
                          {(member.favorites?.length || 0) > 3 && (
                            <span className="text-[10px] px-1.5 py-0.5 text-ink-400 font-mono">
                              +{member.favorites.length - 3} more
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="pt-2 flex flex-col sm:flex-row gap-2">
                <Button
                  variant="primary"
                  size="lg"
                  className="flex-1"
                  onClick={handleStartPlanning}
                  icon={<Sparkles className="w-4 h-4 text-brand-violet" />}
                >
                  Generate Taste-Fair Itinerary
                </Button>
                <Button
                  variant="secondary"
                  size="lg"
                  onClick={onClose}
                >
                  Done
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Toast */}
        {toastMsg && (
          <div className="fixed bottom-6 right-6 z-50 animate-bounce">
            <Toast
              title="Common Ground"
              message={toastMsg}
              type="info"
              onClose={() => setToastMsg(null)}
            />
          </div>
        )}
      </div>
    </div>
  );
};
