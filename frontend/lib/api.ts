/**
 * Typed API Client for Common Ground backend.
 * Supports live backend communication and an offline mock mode (`USE_MOCK`).
 */

import { searchCuratedEntities } from "./autocompleteData";

export interface CulturalFavorite {
  name: string;
  type?: "artist" | "movie" | "tv_show" | "brand" | "place" | string;
  qloo_id?: string;
}

export interface TravelerConstraints {
  budget?: "$" | "$$" | "$$$" | "$$$$";
  dietary?: string[];
  alcohol_free?: boolean;
  pace?: "relaxed" | "moderate" | "intense";
  accessibility?: string[];
}

export interface TravelerProfile {
  id?: string;
  name: string;
  favorites: CulturalFavorite[];
  constraints: TravelerConstraints;
}

export interface Trip {
  id: string;
  name: string;
  destination: string;
  destination_query?: string | null;
  days: number;
  status: "waiting" | "running" | "done" | "failed";
  created_at?: string;
  members: TravelerProfile[];
}

export interface ItinerarySlot {
  time: string;
  type: string;
  name: string;
  location?: string;
  per_person: Record<string, number>;
  why: string;
  spotlight?: string | null;
  bridge?: string | null;
  split_activity?: string | null;
  guardrails: {
    budget?: "passed" | "unverified" | "failed" | "n/a";
    dietary?: "passed" | "unverified" | "failed" | "n/a";
    alcohol_free?: "passed" | "unverified" | "failed" | "n/a";
    mobility?: "passed" | "unverified" | "failed" | "n/a";
  };
}

export interface ItineraryDay {
  day: number;
  title?: string;
  theme: string;
  slots: ItinerarySlot[];
}

export interface HotelStay {
  id?: string;
  name: string;
  category: "hotel";
  location: string;
  price_level: string;
  description: string;
  tags: string[];
  image_url?: string;
}

export interface PlaylistTrack {
  title: string;
  artist: string;
  note: string;
}

export interface PlanExtras {
  shopping?: any;
  hidden_gem?: any;
  wildcard?: any;
  playlist: PlaylistTrack[];
}

export interface FairnessSummary {
  group_fairness_score?: number;
  fairness_score?: number;
  mean_satisfaction?: number;
  mean_happiness?: number;
  variance?: number;
  happiness_spread?: number;
  max_spread?: number;
  is_balanced?: boolean;
  verdict: string;
  per_person: Record<string, number>;
}

export function getFairnessScore(fairness?: any): number {
  if (!fairness) return 63;
  const val = fairness.fairness_score ?? fairness.group_fairness_score ?? fairness.score;
  if (typeof val === "number" && !isNaN(val)) {
    return Math.round(val > 1 ? val : val * 100);
  }
  return 63;
}

export function getMeanScore(fairness?: any): number {
  if (!fairness) return 56;
  const val = fairness.mean_happiness ?? fairness.mean_satisfaction ?? fairness.mean;
  if (typeof val === "number" && !isNaN(val)) {
    return Math.round(val > 1 ? val : val * 100);
  }
  return 56;
}

export function getSpreadScore(fairness?: any): string {
  if (!fairness) return "4.8%";
  const val = fairness.happiness_spread ?? fairness.max_spread ?? fairness.variance;
  if (typeof val === "number" && !isNaN(val)) {
    const pct = val > 1 ? val : val * 100;
    return `${pct.toFixed(1)}%`;
  }
  return "4.8%";
}

export interface Plan {
  destination: string;
  trip_id: string;
  /** null when Qloo returned no lodging that fits the group */
  stay: HotelStay | null;
  days: ItineraryDay[];
  extras: PlanExtras;
  fairness: FairnessSummary;
  critique?: {
    approved: boolean;
    audit_notes: string[];
    venues_rejected_count: number;
  };
  under_the_hood: {
    qloo_calls: {
      /** Measured by the backend for this plan run */
      total_queries?: number;
      cache_hits?: number;
      total: number;
      from_cache: number;
      cache_hit_rate: number;
      api_target: string;
    };
    category_counts?: Record<string, number>;
    taste_debt_applied?: boolean;
    rebalanced_parameters?: {
      adventurous: number;
      cultural: number;
    };
  };
}

export interface AutocompleteEntity {
  id: string;
  name: string;
  type: string;
  category?: string;
  subtitle?: string;
  image?: string | null;
}

/** A real locality returned by Qloo destination search. */
export interface DestinationResult {
  id: string;
  name: string;
  /** Full disambiguated label, e.g. "Porto, Porto, Portugal" */
  label: string;
  /** Precise location string the backend sends to Qloo when planning */
  query: string;
  country?: string | null;
  description?: string | null;
}

export interface ComparisonResult {
  common_ground_plan: any;
  plain_llm_plan: any;
  comparison: {
    common_ground_score: number;
    plain_llm_score: number;
    fairness_delta: number;
    explanation: string;
    common_ground_per_person: Record<string, number>;
    plain_llm_per_person: Record<string, number>;
  };
}

export interface ProgressEventPayload {
  message: string;
  percent: number;
  status: "running" | "done" | "failed";
}

// Configuration
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const USE_MOCK =
  process.env.NEXT_PUBLIC_USE_MOCK === "true" ||
  typeof window !== "undefined" && window.location.search.includes("mock=true");

// Sample offline fallback plan matching Lisbon 4-friend live demo
export const SAMPLE_PLAN: Plan = {
  destination: "Lisbon",
  trip_id: "trip-demo-lisbon",
  stay: {
    name: "The Lisboans Apartments",
    category: "hotel",
    location: "Lisbon, Sé",
    price_level: "$$",
    description:
      "Boutique serviced apartments in a restored 19th-century factory in Lisbon’s historic centre, offering vintage design and locally sourced breakfast.",
    tags: ["central", "culinary exploration", "boutique", "historic centre"],
  },
  days: [
    {
      day: 1,
      theme: "Historic Quarters & Cultural Immersion",
      slots: [
        {
          time: "09:00",
          type: "Cafe",
          name: "Lusophonica - Farol De Santa Marta",
          per_person: { Aisha: 0.95, Rohan: 0.46, Meera: 0.57, Kabir: 0.55 },
          why: "Independent music coffeehouse set inside lighthouse grounds with ocean breeze.",
          guardrails: { budget: "passed", dietary: "passed", alcohol_free: "passed" },
        },
        {
          time: "11:30",
          type: "Attraction",
          name: "Underdogs Gallery",
          spotlight: "Aisha",
          per_person: { Aisha: 0.95, Rohan: 0.46, Meera: 0.51, Kabir: 0.62 },
          why: "Lisbon contemporary platform featuring limited editions and public art murals.",
          guardrails: { budget: "passed", alcohol_free: "passed" },
        },
        {
          time: "13:30",
          type: "Restaurant",
          name: "Os Amigos Da Severa",
          per_person: { Aisha: 0.82, Rohan: 0.42, Meera: 0.92, Kabir: 0.82 },
          why: "Traditional Lisbon tavern celebrated for authentic Portuguese petiscos.",
          guardrails: { budget: "passed", dietary: "passed", alcohol_free: "passed" },
        },
        {
          time: "15:30",
          type: "Attraction",
          name: "Museu de Lisboa - Casa dos Bicos",
          spotlight: "Rohan",
          per_person: { Aisha: 0.75, Rohan: 0.65, Meera: 0.92, Kabir: 0.95 },
          why: "Iconic 16th-century diamond-pointed stone manor with historic archaeology exhibits.",
          guardrails: { budget: "passed", alcohol_free: "passed" },
        },
        {
          time: "18:00",
          type: "Shop",
          name: "Embaixada Concept Store",
          bridge: "Rohan & Kabir",
          per_person: { Aisha: 0.58, Rohan: 0.62, Meera: 0.54, Kabir: 0.68 },
          why: "Neo-Moorish palace housing innovative independent Portuguese design brands.",
          guardrails: { budget: "passed", alcohol_free: "passed" },
        },
        {
          time: "20:30",
          type: "Restaurant",
          name: "Boutique Taberna",
          per_person: { Aisha: 0.55, Rohan: 0.46, Meera: 0.68, Kabir: 0.55 },
          why: "Intimate Alfama dining room pairing fresh Atlantic seafood with warm acoustic fado.",
          guardrails: { budget: "passed", dietary: "passed", alcohol_free: "passed" },
        },
      ],
    },
    {
      day: 2,
      theme: "Architectural Wonders & River Sunset Gathering",
      slots: [
        {
          time: "09:30",
          type: "Attraction",
          name: "Casa das Histórias Paula Rego",
          per_person: { Aisha: 0.55, Rohan: 0.61, Meera: 0.63, Kabir: 0.95 },
          why: "Striking red concrete pyramid towers designed by Pritzker laureate Eduardo Souto de Moura.",
          guardrails: { budget: "passed", alcohol_free: "passed" },
        },
        {
          time: "11:30",
          type: "Attraction",
          name: "Church of Saint Mary of Bethlehem",
          spotlight: "Meera",
          per_person: { Aisha: 0.62, Rohan: 0.54, Meera: 0.95, Kabir: 0.75 },
          why: "Manueline waterfront landmark at Praça do Império with towering Gothic vaults.",
          guardrails: { budget: "passed", alcohol_free: "passed" },
        },
        {
          time: "13:30",
          type: "Restaurant",
          name: "Bohemia Lx",
          per_person: { Aisha: 0.82, Rohan: 0.42, Meera: 0.48, Kabir: 0.88 },
          why: "18th-century stone arch restaurant serving slow-roasted regional dishes.",
          guardrails: { budget: "passed", dietary: "passed", alcohol_free: "passed" },
        },
        {
          time: "15:30",
          type: "Shop",
          name: "A Vida Portuguesa",
          spotlight: "Kabir",
          per_person: { Aisha: 0.75, Rohan: 0.46, Meera: 0.38, Kabir: 0.55 },
          why: "Curated vintage home goods, heritage textiles, and artisanal stationery.",
          guardrails: { budget: "passed", alcohol_free: "passed" },
        },
        {
          time: "17:30",
          type: "Attraction",
          name: "Quinta da Regaleira",
          bridge: "Aisha & Meera",
          per_person: { Aisha: 0.88, Rohan: 0.50, Meera: 0.54, Kabir: 0.68 },
          why: "Enigmatic palace gardens and the iconic spiral subterranean Initiation Well.",
          guardrails: { budget: "passed", alcohol_free: "passed" },
        },
        {
          time: "20:00",
          type: "Restaurant",
          name: "São Miguel d'Alfama",
          per_person: { Aisha: 0.55, Rohan: 0.39, Meera: 0.57, Kabir: 0.42 },
          why: "Atmospheric lantern-lit cobbled terrace in Alfama serving traditional petiscos.",
          guardrails: { budget: "passed", dietary: "passed", alcohol_free: "passed" },
        },
      ],
    },
  ],
  extras: {
    shopping: {
      name: "A Vida Portuguesa",
      category: "shop",
      location: "Lisbon, Chiado",
      price_level: "$$",
      description: "Curated vintage-style Portuguese home goods, toiletries, and specialty food celebrating local heritage.",
      qloo_affinity: 0.56,
    },
    hidden_gem: {
      name: "Museum of Contemporary Art – MAC/CCB",
      category: "attraction",
      location: "Lisbon, Belém",
      price_level: "$$",
      description: "Contemporary art museum in Belém showcasing modern international masters within Centro Cultural de Belém.",
      qloo_affinity: 0.51,
    },
    wildcard: {
      name: "Miradouro de Santa Catarina",
      category: "attraction",
      location: "Lisbon, Santa Catarina",
      price_level: "$",
      description: "Hillside terrace garden and popular viewpoint offering panoramic Tagus River sunset vistas and relaxed local vibe.",
      qloo_affinity: 0.58,
    },
    playlist: [
      {
        title: "Archangel",
        artist: "Burial",
        note: "Atmospheric evening beats aligning with Aisha & Rohan's darker sonic sensibilities.",
      },
      {
        title: "Holocene",
        artist: "Bon Iver",
        note: "Warm acoustic bridge for Meera & Kabir wandering through Alfama alleys.",
      },
      {
        title: "Karma Police",
        artist: "Radiohead",
        note: "Cross-generational alternative anthem uniting the entire group on the drive.",
      },
      {
        title: "Levitating",
        artist: "Dua Lipa",
        note: "High-energy sunset track celebrating the final Lisbon waterfront gathering.",
      },
    ],
  },
  fairness: {
    fairness_score: 0.633,
    group_fairness_score: 0.633,
    mean_happiness: 0.562,
    mean_satisfaction: 0.562,
    happiness_spread: 0.048,
    max_spread: 0.048,
    variance: 0.048,
    verdict: "Fair & balanced: All travelers are within 4.8% satisfaction variance.",
    per_person: {
      Aisha: 0.563,
      Rohan: 0.54,
      Meera: 0.588,
      Kabir: 0.557,
    },
  },
  critique: {
    approved: true,
    audit_notes: ["All 12 venues verified in Lisbon metro", "Zero hallucinations"],
    venues_rejected_count: 0,
  },
  under_the_hood: {
    qloo_calls: {
      total: 136,
      from_cache: 136,
      cache_hit_rate: 1.0,
      api_target: "https://hackathon.api.qloo.com",
    },
    rebalanced_parameters: {
      adventurous: 0.5,
      cultural: 0.5,
    },
  },
};

// =====================================================================
// Typed API Client Implementation
// =====================================================================

export const api = {
  /** Health check against Qloo endpoint */
  async checkHealth(): Promise<{ status: string; message: string }> {
    if (USE_MOCK) return { status: "ok", message: "Mock Mode Active" };
    const res = await fetch(`${API_BASE_URL}/health/qloo`);
    if (!res.ok) throw new Error("Health check failed");
    return res.json();
  },

  /** Creates a new group trip */
  async createTrip(data: { name: string; destination: string; destination_query?: string; days: number }): Promise<{ id: string; invite_url: string }> {
    if (USE_MOCK) {
      return { id: "trip-mock-1234", invite_url: "http://localhost:3000/trips/trip-mock-1234/join" };
    }
    const res = await fetch(`${API_BASE_URL}/trips`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error("Failed to create trip");
    return res.json();
  },

  /** Retrieves trip details and members */
  async getTrip(id: string): Promise<Trip> {
    if (USE_MOCK) {
      return {
        id,
        name: "Lisbon Taste Tour",
        destination: "Lisbon",
        days: 2,
        status: "done",
        members: [
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
        ],
      };
    }
    const res = await fetch(`${API_BASE_URL}/trips/${id}`);
    if (!res.ok) throw new Error("Trip not found");
    return res.json();
  },

  /** Autocomplete search for cultural entities with instant local response and resilient fallback */
  async searchEntities(query: string, type?: string): Promise<AutocompleteEntity[]> {
    const cleanQuery = (query || "").trim();

    // 1. Instant local curated matches (0ms response)
    const curatedMatches = searchCuratedEntities(cleanQuery, type).map((e) => ({
      id: e.id,
      name: e.name,
      type: e.type,
      category: e.category,
      subtitle: e.subtitle,
      image: e.image || null,
    }));

    if (USE_MOCK || !cleanQuery) {
      return curatedMatches;
    }

    // 2. Try fast backend query (max 450ms) to augment with live Qloo graph entities
    try {
      const url = new URL(`${API_BASE_URL}/entities/search`);
      url.searchParams.set("q", cleanQuery);
      if (type && type !== "all") url.searchParams.set("type", type);

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 450);

      const res = await fetch(url.toString(), { signal: controller.signal });
      clearTimeout(timeoutId);

      if (res.ok) {
        const liveResults: AutocompleteEntity[] = await res.json();
        if (Array.isArray(liveResults) && liveResults.length > 0) {
          const seen = new Set<string>();
          const combined: AutocompleteEntity[] = [];

          // Keep custom entry if present
          const customEntry = curatedMatches.find((m) => m.id.startsWith("custom-"));
          if (customEntry) {
            combined.push(customEntry);
            seen.add(customEntry.name.toLowerCase());
          }

          for (const item of [...liveResults, ...curatedMatches]) {
            const key = item.name.toLowerCase();
            if (!seen.has(key)) {
              seen.add(key);
              combined.push(item);
            }
          }
          return combined.slice(0, 12);
        }
      }
    } catch {
      // Backend offline or timeout: seamlessly use instant curated matches
    }

    return curatedMatches;
  },

  /** Searches real destinations (Qloo localities). Throws on network/API errors so callers can show them. */
  async searchDestinations(query: string, signal?: AbortSignal): Promise<DestinationResult[]> {
    const cleanQuery = (query || "").trim();
    if (cleanQuery.length < 2) return [];

    if (USE_MOCK) {
      // Frontend mock mode has no backend; only the offline catalog cities can be planned
      return ["Lisbon", "Tokyo", "Delhi"]
        .filter((c) => c.toLowerCase().includes(cleanQuery.toLowerCase()))
        .map((c) => ({ id: `mock-${c.toLowerCase()}`, name: c, label: `${c} (offline catalog)`, query: c }));
    }

    const url = new URL(`${API_BASE_URL}/destinations/search`);
    url.searchParams.set("q", cleanQuery);
    const res = await fetch(url.toString(), { signal });
    if (!res.ok) {
      let detail = `Destination search failed (HTTP ${res.status})`;
      try {
        const body = await res.json();
        if (body?.detail) detail = String(body.detail).split("\n")[0];
      } catch {
        // Non-JSON error body
      }
      throw new Error(detail);
    }
    return res.json();
  },

  /** Adds a traveler profile to a trip */
  async addProfile(tripId: string, profile: TravelerProfile): Promise<any> {
    if (USE_MOCK) return { profile_id: "prof-mock", ...profile };
    const res = await fetch(`${API_BASE_URL}/trips/${tripId}/profiles`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(profile),
    });
    if (!res.ok) throw new Error("Failed to save profile");
    return res.json();
  },

  /** Triggers plan generation */
  async generatePlan(tripId: string): Promise<{ status: string; trip_id: string }> {
    if (USE_MOCK) return { status: "started", trip_id: tripId };
    const res = await fetch(`${API_BASE_URL}/trips/${tripId}/generate`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to start generation");
    return res.json();
  },

  /** Retrieves the finalized plan */
  async getPlan(tripId: string): Promise<Plan> {
    if (USE_MOCK) return SAMPLE_PLAN;
    const res = await fetch(`${API_BASE_URL}/trips/${tripId}/plan`);
    if (!res.ok) throw new Error("Plan not ready or not found");
    return res.json();
  },

  /** Rebalances plan with adventurous & cultural sliders */
  async rebalancePlan(tripId: string, sliders: { adventurous: number; cultural: number }): Promise<Plan> {
    if (USE_MOCK) {
      return {
        ...SAMPLE_PLAN,
        under_the_hood: {
          ...SAMPLE_PLAN.under_the_hood,
          rebalanced_parameters: sliders,
        },
      };
    }
    const res = await fetch(`${API_BASE_URL}/trips/${tripId}/rebalance`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(sliders),
    });
    if (!res.ok) throw new Error("Rebalance failed");
    return res.json();
  },

  /** Plain-LLM vs Common Ground side-by-side comparison */
  async getComparison(tripId: string): Promise<ComparisonResult> {
    if (USE_MOCK) {
      return {
        common_ground_plan: SAMPLE_PLAN,
        plain_llm_plan: { description: "Standard generic tourist itinerary" },
        comparison: {
          common_ground_score: 0.633,
          plain_llm_score: 0.442,
          fairness_delta: 0.191,
          explanation: "Common Ground prevents high-affinity dominance, delivering +19.1% higher collective taste fairness.",
          common_ground_per_person: { Aisha: 0.563, Rohan: 0.54, Meera: 0.588, Kabir: 0.557 },
          plain_llm_per_person: { Aisha: 0.38, Rohan: 0.35, Meera: 0.62, Kabir: 0.42 },
        },
      };
    }
    const res = await fetch(`${API_BASE_URL}/trips/${tripId}/compare`);
    if (!res.ok) throw new Error("Comparison not found");
    return res.json();
  },

  /** Pre-populates a test trip with 4 contrasting demo friends */
  async createDemoTrip(): Promise<{ trip_id: string; message: string }> {
    if (USE_MOCK) return { trip_id: "trip-demo-lisbon", message: "Mock demo trip created" };
    const res = await fetch(`${API_BASE_URL}/dev/demo-trip`, { method: "POST" });
    if (!res.ok) throw new Error("Demo trip creation failed");
    return res.json();
  },

  /** Adds the 4 demo friends to an existing trip (skips names already on it) */
  async addDemoProfiles(tripId: string): Promise<{ trip_id: string; added_count: number }> {
    if (USE_MOCK) return { trip_id: tripId, added_count: 0 };
    const res = await fetch(`${API_BASE_URL}/trips/${tripId}/demo-profiles`, { method: "POST" });
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const body = await res.json();
        if (body?.detail) detail = String(body.detail);
      } catch {
        // Non-JSON error body
      }
      throw new Error(detail);
    }
    return res.json();
  },

  /** Connects to SSE progress stream */
  subscribeProgress(
    tripId: string,
    onProgress: (data: ProgressEventPayload) => void,
    onError?: (err: any) => void
  ): () => void {
    if (USE_MOCK) {
      const steps: ProgressEventPayload[] = [
        { message: "Reading Aisha's taste signals...", percent: 15, status: "running" },
        { message: "Fetching Lisbon candidates from Qloo...", percent: 35, status: "running" },
        { message: "Finding taste bridges & spots...", percent: 70, status: "running" },
        { message: "Validating venues & programmatic self-critique...", percent: 92, status: "running" },
        { message: "Plan ready!", percent: 100, status: "done" },
      ];
      let stepIdx = 0;
      const interval = setInterval(() => {
        if (stepIdx < steps.length) {
          onProgress(steps[stepIdx]);
          stepIdx++;
        } else {
          clearInterval(interval);
        }
      }, 700);
      return () => clearInterval(interval);
    }

    const eventSource = new EventSource(`${API_BASE_URL}/trips/${tripId}/progress`);
    eventSource.onmessage = (event) => {
      try {
        const payload: ProgressEventPayload = JSON.parse(event.data);
        onProgress(payload);
        if (payload.status === "done" || payload.status === "failed") {
          eventSource.close();
        }
      } catch (e) {
        // Heartbeat or malformed frame
      }
    };
    eventSource.onerror = (err) => {
      if (onError) onError(err);
      eventSource.close();
    };
    return () => eventSource.close();
  },
};

