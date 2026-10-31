"""Pydantic data models for Common Ground.

These models define the shape of data used throughout the app:
- Candidate: A recommended place (restaurant, hotel, cafe, etc.) scored by Qloo.
- Profile: A traveler's name, favorite cultural/taste signals, and constraints.
- Trip: A group trip with destination, dates, and member profiles.
- Plan: A generated itinerary balancing taste fairness across all members.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class Candidate(BaseModel):
    """Represents a potential place/venue to visit on a trip.

    Scored by Qloo's taste-affinity engine against traveler profiles.
    """
    model_config = ConfigDict(extra="allow")

    id: str = Field(description="Unique identifier for the place or venue")
    name: str = Field(description="Name of the venue or place (e.g. 'Fabrica Coffee Roasters')")
    category: str = Field(description="Category: hotel, restaurant, cafe, bar, attraction, shop")
    location: str = Field(description="City or neighborhood (e.g. 'Lisbon', 'Alfama')")
    qloo_affinity: float = Field(
        default=0.0,
        description="Affinity score (0.0 to 1.0 or 0 to 100), higher means stronger taste match"
    )
    tags: List[str] = Field(default_factory=list, description="Descriptive taste tags (e.g. ['specialty-coffee', 'minimalist'])")
    price_level: Optional[str] = Field(default="$$", description="Estimated price bracket: $, $$, $$$, $$$$")
    price_verified: bool = Field(default=True, description="False when Qloo gave no price and price_level is only a neutral placeholder")
    description: Optional[str] = Field(default=None, description="Short editorial summary of the venue")
    address: Optional[str] = Field(default=None, description="Physical street address")
    image_url: Optional[str] = Field(default=None, description="Cover image or thumbnail URL")
    latitude: Optional[float] = Field(default=None, description="Geographic latitude")
    longitude: Optional[float] = Field(default=None, description="Geographic longitude")

    # --- Real Qloo metadata (populated from live API payloads) ---
    primary_genre: Optional[str] = Field(default=None, description="Qloo primary genre tag ID, e.g. 'urn:tag:genre:place:museum'")
    qloo_genres: List[str] = Field(default_factory=list, description="Qloo genre/category place tag IDs")
    popularity: Optional[float] = Field(default=None, description="Qloo popularity (0-1)")
    affinity_source: str = Field(default="unknown", description="Where qloo_affinity came from: 'qloo', 'mock_heuristic', or 'missing'")

    # --- Per-traveler scores attached during planning ---
    person_affinity: Dict[str, float] = Field(default_factory=dict, description="Real Qloo affinity per traveler (only travelers Qloo returned a value for)")
    person_fit: Dict[str, float] = Field(default_factory=dict, description="Common Ground fit per traveler: percentile of their affinity within the venue's category")


class ProfileConstraints(BaseModel):
    """Dietary, budget, and physical constraints for a traveler."""
    model_config = ConfigDict(extra="allow")

    budget: Optional[str] = Field(default=None, description="Max budget preference: $, $$, $$$, $$$$")
    dietary: List[str] = Field(default_factory=list, description="Dietary restrictions: e.g. ['vegetarian', 'halal']")
    alcohol_free: bool = Field(default=False, description="Strictly alcohol-free travel preference")
    accessibility: List[str] = Field(default_factory=list, description="Accessibility needs: e.g. ['step-free', 'elevator']")
    pace: Optional[str] = Field(default="moderate", description="Preferred travel pace: 'relaxed', 'moderate', 'intense'")


class Profile(BaseModel):
    """A member of a group trip, including their cultural taste signals."""
    model_config = ConfigDict(extra="allow")

    id: Optional[str] = Field(default=None, description="Optional profile identifier")
    name: str = Field(description="Person's name or nickname")
    favorites: List[Any] = Field(
        default_factory=list,
        description="Favorite cultural entities / taste signals (artists, brands, places, cuisines)"
    )
    constraints: ProfileConstraints = Field(
        default_factory=ProfileConstraints,
        description="Personal travel constraints"
    )


class Trip(BaseModel):
    """A planned or active trip with one or more member profiles."""
    model_config = ConfigDict(extra="allow")

    id: Optional[str] = Field(default=None, description="Trip ID")
    title: str = Field(description="Trip title (e.g. 'Lisbon Design & Wine Week')")
    name: Optional[str] = Field(default=None, description="Trip name alias")
    destination: str = Field(description="Target destination city (e.g. 'Lisbon')")
    days: int = Field(default=2, description="Duration in days")
    status: str = Field(default="waiting", description="Status: waiting, running, done, failed")
    start_date: Optional[str] = Field(default=None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="End date (YYYY-MM-DD)")
    members: List[Profile] = Field(default_factory=list, description="List of travelers in this group")
    created_at: Optional[str] = Field(default=None, description="Creation timestamp")


class FavoriteInput(BaseModel):
    """Cultural favorite input with optional entity type hint and Qloo ID."""
    name: str = Field(..., min_length=1)
    type: Optional[str] = None
    qloo_id: Optional[str] = None


class ProfileCreateInput(BaseModel):
    """Payload to add a traveler to a trip."""
    name: str = Field(..., min_length=1)
    favorites: List[FavoriteInput] = Field(default_factory=list)
    constraints: ProfileConstraints = Field(default_factory=ProfileConstraints)


class TripCreateInput(BaseModel):
    """Payload to initialize a new group trip."""
    name: str = Field(..., min_length=1)
    destination: str = Field(..., min_length=1)
    destination_query: Optional[str] = Field(
        default=None,
        max_length=300,
        description="Precise Qloo location string from destination search (e.g. 'Porto, Porto, Portugal')"
    )
    days: int = Field(default=2, ge=1, le=14)


class TripCreateResponse(BaseModel):
    """Response returned upon trip creation."""
    id: str
    invite_url: str


class RebalanceInput(BaseModel):
    """Payload to adjust itinerary balance between novelty and cultural depth."""
    adventurous: float = Field(default=0.5, ge=0.0, le=1.0)
    cultural: float = Field(default=0.5, ge=0.0, le=1.0)


class PlanStop(BaseModel):
    """An individual scheduled stop in a trip itinerary."""
    model_config = ConfigDict(extra="allow")

    day: int = Field(description="Day number of the trip (1, 2, 3...)")
    time_slot: str = Field(description="Time slot: 'morning', 'lunch', 'afternoon', 'dinner', 'night'")
    candidate: Candidate = Field(description="The recommended venue for this stop")
    notes: Optional[str] = Field(default=None, description="Reasoning or notes about why this fits the group")
    why_it_works: Optional[str] = Field(default=None, description="Editorial explanation for why this stop works for the group")
    taste_scores: Dict[str, float] = Field(default_factory=dict, description="Per-traveler affinity scores for this stop")
    guardrail_status: str = Field(
        default="passed",
        description="Guardrail check status: 'passed', 'warning', or 'error'"
    )


class PlaylistItem(BaseModel):
    """A song or track in the group's curated cultural playlist."""
    model_config = ConfigDict(extra="allow")

    title: str = Field(description="Track title")
    artist: str = Field(description="Artist name")
    vibe: str = Field(description="Musical genre or vibe")
    contributed_for: str = Field(description="Traveler whose taste profile inspired this track")
    reason: str = Field(description="Short editorial note on why this track bridges the group")


class Plan(BaseModel):
    """A taste-fair itinerary plan generated for a trip.

    Matches the group trip planning JSON structure with fairness metrics.
    Configured with extra='allow' to accommodate additional brief fields gracefully.
    """
    model_config = ConfigDict(extra="allow")

    id: Optional[str] = Field(default=None, description="Unique plan ID")
    trip_id: str = Field(description="Associated Trip ID")
    destination: str = Field(description="Trip destination city")
    title: Optional[str] = Field(default="Balanced Group Itinerary", description="Itinerary title")
    fairness_score: float = Field(
        default=0.0,
        description="Fairness metric (0.0 to 1.0 or 0 to 100) measuring taste balance among members"
    )
    guardrails: Dict[str, Any] = Field(
        default_factory=dict,
        description="Status of budget, dietary, and accessibility guardrails"
    )
    itinerary: List[PlanStop] = Field(
        default_factory=list,
        description="Scheduled daily stops"
    )
    stay: Optional[Candidate] = Field(
        default=None,
        description="Recommended hotel/stay for the group"
    )
    extras: List[Candidate] = Field(
        default_factory=list,
        description="Supplemental curated recommendations (shops, strolls, alternative spots)"
    )
    playlist: List[PlaylistItem] = Field(
        default_factory=list,
        description="Curated group trip soundtrack bridging members' musical and cultural affinities"
    )
    critique: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Self-critique pass evaluating fairness threshold, pacing, and grounding"
    )
    candidates: List[Candidate] = Field(
        default_factory=list,
        description="All ranked venue candidates evaluated for this plan"
    )
    summary: Optional[str] = Field(
        default=None,
        description="Editorial overview explaining the group's common taste intersections"
    )
    created_at: Optional[str] = Field(default=None, description="Timestamp when plan was generated")



# =====================================================================
# Music recommendations (three-mode group playlist)
# =====================================================================

MusicMode = Literal["vibes", "favourites", "local"]


class MusicLink(BaseModel):
    """A listening link built from verified IDs (Qloo external IDs or catalogue records)."""
    label: str
    url: str
    kind: str = Field(description="'artist' or 'track'")


class MusicTrack(BaseModel):
    """A track confirmed to exist in the music catalogue under the recommended artist."""
    title: str
    album: Optional[str] = None
    artwork_url: Optional[str] = None
    preview_url: Optional[str] = Field(default=None, description="Short audio preview from the catalogue")
    listen_url: str
    provider: str = Field(description="Catalogue provider, e.g. 'apple_music'")
    basis: str = Field(description="'qloo_notable_song' (title taken from Qloo) or 'catalog_listing' (first catalogue track by this artist)")


class MusicScores(BaseModel):
    """Scores for one recommended artist. API-provided and calculated values are kept apart."""
    # --- Provided by the Qloo API ---
    qloo_affinity: Optional[float] = Field(default=None, description="Qloo affinity for this request's signals (API)")
    qloo_popularity: Optional[float] = Field(default=None, description="Qloo popularity 0-1 (API)")
    qloo_affinity_by_member: Dict[str, float] = Field(default_factory=dict, description="Qloo affinity per member's favourites (API)")
    # --- Calculated by Common Ground ---
    group_fit: Optional[float] = Field(default=None, description="Common Ground group-fit score 0-1 (calculated)")
    group_fit_basis: str = Field(default="", description="How group_fit was calculated")
    member_fit: Dict[str, float] = Field(default_factory=dict, description="Per-member fit 0-1 (calculated)")
    fit_unknown_members: List[str] = Field(default_factory=list, description="Members Qloo returned no affinity for; counted as neutral in group_fit, not shown as scores")


class MusicEntry(BaseModel):
    """One recommended artist (and a verified track when the catalogue confirms one)."""
    artist: str
    qloo_id: str
    role: str = Field(description="vibes: 'vibe_match'|'vibe_pick'; favourites: 'spotlight'|'shared'|'discovery'; local: 'local'")
    genres: List[str] = Field(default_factory=list)
    image_url: Optional[str] = None
    known_for: List[str] = Field(default_factory=list, description="Notable song titles as reported by Qloo (not verified as playable)")
    track: Optional[MusicTrack] = None
    links: List[MusicLink] = Field(default_factory=list)
    scores: MusicScores = Field(default_factory=MusicScores)
    why: str
    vibes: List[str] = Field(default_factory=list)
    local_evidence: Optional[str] = Field(default=None, description="'born_in_city'|'born_in_country'|'local_genre'|'popular_here'")


class MusicPlaylist(BaseModel):
    """A mode-specific group playlist, or an explanation of why none could be built."""
    mode: MusicMode
    mode_label: str
    status: Literal["ok", "sparse", "empty", "unavailable"]
    message: Optional[str] = None
    selection: Dict[str, Any] = Field(default_factory=dict, description="What the playlist was built from (vibes, destination)")
    entries: List[MusicEntry] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)
    sources: Dict[str, str] = Field(default_factory=dict, description="Which values come from Qloo and which are calculated")
    catalog: Dict[str, Any] = Field(default_factory=dict)
    generated_at: Optional[str] = None


class PlaylistRequest(BaseModel):
    """Payload to (re)build a trip's playlist in one of the three modes."""
    mode: MusicMode = "favourites"
    vibes: List[str] = Field(default_factory=list, max_length=4)
    size: int = Field(default=12, ge=6, le=20)


class GenerateRequest(BaseModel):
    """Optional payload for plan generation."""
    music_mode: MusicMode = "favourites"
    vibes: List[str] = Field(default_factory=list, max_length=4)
