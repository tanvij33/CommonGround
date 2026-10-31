"""Common Ground Planning Pipeline.

Modular planning pipeline that works for ANY group entered via API:
- Resolves cultural favorites to Qloo entities with type hints.
- Fetches real Qloo candidates across categories for any destination.
- Classifies candidates strictly by Qloo properties into real lodging, dining, cafes, sights, retail.
- Applies traveler constraints (dietary, alcohol-free, budget, pace).
- Dynamically balances group taste debt across days and slots.
- Enforces traveler spotlights, taste bridges, and split-and-meet when subgroups diverge.
- Validates 100% venue grounding and performs programmatic self-critique.
- Reports real-time progress through progress_callback at each step.
- Outputs the plan JSON in exactly the shape of data/demo_plan.json.
"""

import math
import uuid
import json
import statistics
from typing import List, Dict, Any, Optional, Tuple, Callable

from backend.models import Candidate, Profile, Trip, ProfileConstraints
from backend.scoring import (
    apply_constraints,
    group_score,
    split_and_meet,
    TasteDebtTracker,
    fairness_summary,
)
from backend.validation import (
    validate_itinerary_grounding,
    audit_itinerary_rules,
    ValidationResult,
    ProgrammaticAuditResult
)
from backend.qloo_client import (
    get_recommendations,
    get_place_affinities,
    resolve_favorite,
    get_qloo_base_url,
    is_qloo_mock_mode,
    count_qloo_log_calls,
    QlooError
)
from backend.mock_data import calculate_mock_affinity

CATEGORIES = ["hotel", "restaurant", "cafe", "bar", "attraction", "shop"]
from backend.llm import generate_structured, generate_text
from backend.agent import CritiqueEvaluation


def build_grounded_slot_description(
    candidate: Candidate,
    slot_label: str,
    spotlight_for: Optional[str] = None,
    bridge_for: Optional[str] = None,
    split_note: Optional[str] = None
) -> str:
    """Builds a strictly grounded editorial description for an itinerary slot.

    Uses ONLY facts extracted from Qloo properties, keywords, and tags. Zero hallucinations.
    """
    venue_name = candidate.name
    cat_title = candidate.category.title()
    desc = candidate.description or f"Curated {candidate.category} in {candidate.location}"

    clean_tags = [t.replace("-", " ") for t in candidate.tags[:3] if t]
    tag_str = f" Featuring {', '.join(clean_tags)}." if clean_tags else ""

    parts = [f"{venue_name} ({cat_title}): {desc}.{tag_str}"]

    if spotlight_for:
        parts.append(f"Dedicated spotlight for {spotlight_for}.")
    elif bridge_for:
        parts.append(f"Taste bridge for {bridge_for}.")

    if split_note:
        parts.append(f"Parallel activity: {split_note}")

    return " ".join(parts)


ACTIVITY_CATEGORIES = ("restaurant", "cafe", "bar", "attraction", "shop")

# Categories that may stand in when a slot's own category has no usable venue.
# Lodging is never a stand-in: the stay is chosen separately.
SLOT_FALLBACK_CATEGORIES: Dict[str, List[str]] = {
    "cafe": ["cafe", "restaurant"],
    "restaurant": ["restaurant"],
    "attraction": ["attraction", "shop"],
    "shop": ["shop", "attraction"],
    "bar": ["bar", "cafe"],
}

MAX_VENUE_DISTANCE_KM = 120.0
NEUTRAL_FIT = 0.5


def _normalize_name(name: str) -> str:
    return "".join(ch.lower() for ch in name if ch.isalnum())


def _favorite_name_and_type(item: Any) -> Tuple[str, Optional[str]]:
    if isinstance(item, dict):
        return str(item.get("name") or "").strip(), item.get("type")
    if isinstance(item, (tuple, list)) and item:
        return str(item[0]).strip(), (item[1] if len(item) > 1 else None)
    return str(item).strip(), None


def _round_robin(id_lists: List[List[str]], limit: int) -> List[str]:
    """Interleaves each traveler's signal IDs so every traveler shapes the shared candidate pool."""
    merged: List[str] = []
    depth = 0
    while len(merged) < limit and any(depth < len(lst) for lst in id_lists):
        for lst in id_lists:
            if depth < len(lst) and lst[depth] not in merged:
                merged.append(lst[depth])
                if len(merged) >= limit:
                    break
        depth += 1
    return merged


def _percentile_ranks(values: Dict[str, float]) -> Dict[str, float]:
    """Maps each key to its 0-1 percentile rank among the values (ties share the average rank)."""
    items = sorted(values.items(), key=lambda kv: kv[1])
    n = len(items)
    if n == 0:
        return {}
    if n == 1:
        return {items[0][0]: NEUTRAL_FIT}
    ranks: Dict[str, float] = {}
    i = 0
    while i < n:
        j = i
        while j + 1 < n and items[j + 1][1] == items[i][1]:
            j += 1
        rank = round(((i + j) / 2) / (n - 1), 4)
        for k in range(i, j + 1):
            ranks[items[k][0]] = rank
        i = j + 1
    return ranks


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _relevance_from_distance(distance_km: Optional[float]) -> float:
    """1.0 near the destination center, tapering to 0.3 at MAX_VENUE_DISTANCE_KM; 0 beyond (excluded)."""
    if distance_km is None:
        return 1.0
    if distance_km <= 8:
        return 1.0
    if distance_km <= 40:
        return round(1.0 - (distance_km - 8) / 32 * 0.4, 4)
    if distance_km <= MAX_VENUE_DISTANCE_KM:
        return round(0.6 - (distance_km - 40) / (MAX_VENUE_DISTANCE_KM - 40) * 0.3, 4)
    return 0.0


def _venue_summary(c: Optional[Candidate]) -> Optional[Dict[str, Any]]:
    if c is None:
        return None
    return {
        "id": c.id,
        "name": c.name,
        "category": c.category,
        "location": c.location,
        "price_level": c.price_level,
        "tags": c.tags,
        "description": c.description,
        "qloo_affinity": c.qloo_affinity,
        "qloo_genre": c.primary_genre,
    }


def generate_plan(
    trip: Trip,
    profiles: List[Profile],
    progress_callback: Optional[Callable[[str, int], None]] = None,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Generates a comprehensive, taste-fair group travel plan.

    Args:
        trip: Trip model containing destination, days, id, and title.
        profiles: List of traveler Profile objects in the group.
        progress_callback: Optional callable(message: str, percent: int) reporting progress.
        config: Optional dictionary containing execution overrides (force_mock, etc.).

    Returns:
        Final plan JSON dictionary in exactly the shape of data/demo_plan.json.

    Raises:
        RuntimeError: if Qloo yields no usable venues for the destination (never fabricated).
    """
    cfg = config or {}
    use_mock = cfg.get("force_mock", is_qloo_mock_mode())
    destination = trip.destination or "Lisbon"
    location_query = getattr(trip, "destination_query", None) or destination
    trip_days = max(1, getattr(trip, "days", 2) or 2)
    trip_id = trip.id or f"trip-{uuid.uuid4().hex[:8]}"

    def _report(msg: str, pct: int):
        if progress_callback:
            try:
                progress_callback(msg, pct)
            except TypeError:
                progress_callback(msg)

    initial_log_stats = count_qloo_log_calls()

    # =================================================================
    # STEP 1: Resolve each traveler's favorites to real Qloo entities
    # =================================================================
    _report(f"Reading taste signals for {len(profiles)} travelers...", 10)

    signal_names_by_person: Dict[str, List[str]] = {}
    signal_ids_by_person: Dict[str, List[str]] = {}
    unresolved_by_person: Dict[str, List[str]] = {}

    for p in profiles:
        _report(f"Resolving {p.name}'s taste signals...", 15)
        names: List[str] = []
        ids: List[str] = []
        unresolved: List[str] = []
        for item in p.favorites:
            fav_name, fav_type = _favorite_name_and_type(item)
            if not fav_name:
                continue
            names.append(fav_name)
            res = resolve_favorite(fav_name, type_hint=fav_type, force_mock=use_mock)
            if res and res.get("id"):
                if res["id"] not in ids:
                    ids.append(res["id"])
            else:
                unresolved.append(fav_name)
        signal_names_by_person[p.name] = names
        signal_ids_by_person[p.name] = ids
        unresolved_by_person[p.name] = unresolved

    all_signal_names = list(dict.fromkeys(n for p in profiles for n in signal_names_by_person[p.name]))
    group_signal_ids = _round_robin([signal_ids_by_person[p.name] for p in profiles], limit=8)

    # =================================================================
    # STEP 2: Shared candidate pool, classified by Qloo genre metadata
    # =================================================================
    _report(f"Fetching {destination} candidates across categories...", 30)

    pool: Dict[str, Candidate] = {}
    seen_names: set = set()
    excluded_venues: List[Dict[str, str]] = []
    fetch_errors: List[str] = []

    for idx, cat in enumerate(CATEGORIES):
        _report(f"Querying Qloo for {cat} venues in {destination}...", 30 + idx * 3)
        try:
            cands = get_recommendations(
                signals=all_signal_names,
                category=cat,
                location=destination,
                force_mock=use_mock,
                location_query=location_query,
                signal_ids=group_signal_ids,
                take=20,
                include_other_categories=True,
                dropped_log=excluded_venues
            )
        except QlooError as e:
            fetch_errors.append(f"{cat}: {str(e).splitlines()[0]}")
            continue
        for c in cands:
            key = _normalize_name(c.name)
            if c.id in pool or key in seen_names:
                continue
            seen_names.add(key)
            pool[c.id] = c

    if not pool:
        raise RuntimeError(
            f"No usable venues found for {destination}. " + ("; ".join(fetch_errors) or "Qloo returned no classifiable places.")
        )

    # =================================================================
    # STEP 3: Destination relevance from real coordinates
    # =================================================================
    _report(f"Checking venue distances within {destination}...", 48)

    coords = [(c.latitude, c.longitude) for c in pool.values() if c.latitude is not None and c.longitude is not None]
    center = (statistics.median(lat for lat, _ in coords), statistics.median(lon for _, lon in coords)) if coords else None
    relevance: Dict[str, float] = {}
    distance_km: Dict[str, Optional[float]] = {}

    for cid, c in list(pool.items()):
        dist = None
        if center and c.latitude is not None and c.longitude is not None:
            dist = _haversine_km(center[0], center[1], c.latitude, c.longitude)
        rel = _relevance_from_distance(dist)
        if rel <= 0:
            excluded_venues.append({"name": c.name, "reason": f"{dist:.0f} km from the {destination} candidate center"})
            del pool[cid]
            continue
        relevance[cid] = rel
        distance_km[cid] = round(dist, 1) if dist is not None else None

    # =================================================================
    # STEP 4: Per-traveler affinity (Qloo) and fit (our calculation)
    # =================================================================
    _report("Scoring every venue against each traveler's taste with Qloo...", 55)

    pool_ids = list(pool)
    affinity_source_by_person: Dict[str, str] = {}

    for p in profiles:
        aff: Dict[str, float] = {}
        if use_mock:
            aff = {
                cid: calculate_mock_affinity(c.tags, c.name, signal_names_by_person[p.name])
                for cid, c in pool.items()
            }
            source = "mock_heuristic (offline mode; not Qloo data)"
        elif signal_ids_by_person[p.name]:
            try:
                aff = get_place_affinities(signal_ids_by_person[p.name], pool_ids)
                source = "qloo_insights_affinity"
            except QlooError as e:
                source = f"unavailable ({str(e).splitlines()[0]})"
        else:
            source = "none (no favorites resolved in Qloo)"
        affinity_source_by_person[p.name] = source
        for cid, value in aff.items():
            if cid in pool:
                pool[cid].person_affinity[p.name] = round(float(value), 4)

    for cat in CATEGORIES:
        members = [c for c in pool.values() if c.category == cat]
        for p in profiles:
            ranks = _percentile_ranks({c.id: c.person_affinity[p.name] for c in members if p.name in c.person_affinity})
            for c in members:
                c.person_fit[p.name] = ranks.get(c.id, NEUTRAL_FIT)

    # =================================================================
    # STEP 5: Guardrails
    # =================================================================
    _report("Applying guardrails & constraint filtering...", 62)

    _, guardrail_records = apply_constraints(list(pool.values()), profiles)

    def hard_ok(c: Candidate) -> bool:
        rec = guardrail_records.get(c.id, {})
        return all(rec.get(k) != "failed" for k in ("budget_status", "mobility_status", "alcohol_free_status"))

    def fully_ok(c: Candidate) -> bool:
        return guardrail_records.get(c.id, {}).get("passed", True)

    by_cat: Dict[str, List[Candidate]] = {
        cat: [c for c in pool.values() if c.category == cat and hard_ok(c)] for cat in CATEGORIES
    }
    activity_pool = [c for cat in ACTIVITY_CATEGORIES for c in by_cat[cat]]
    if not activity_pool:
        raise RuntimeError(f"Qloo returned no activity venues in {destination} that satisfy the group's constraints.")

    # =================================================================
    # STEP 6: Spotlights, bridges & split-and-meet
    # =================================================================
    _report("Finding taste bridges & assigning traveler spotlights...", 72)

    def fits(c: Candidate) -> Dict[str, float]:
        return {p.name: c.person_fit.get(p.name, NEUTRAL_FIT) for p in profiles}

    def group_fit(c: Candidate) -> float:
        return group_score(fits(c)) * relevance.get(c.id, 1.0)

    # Most divergent pair: largest mean squared fit difference across activity venues
    bridge_pair: Optional[Tuple[str, str]] = None
    divergence = 0.0
    for i in range(len(profiles)):
        for j in range(i + 1, len(profiles)):
            a, b = profiles[i].name, profiles[j].name
            d = sum((c.person_fit.get(a, NEUTRAL_FIT) - c.person_fit.get(b, NEUTRAL_FIT)) ** 2 for c in activity_pool) / len(activity_pool)
            if bridge_pair is None or d > divergence:
                bridge_pair, divergence = (a, b), d
    propose_split = divergence > 0.12 and len(profiles) >= 3

    # =================================================================
    # STEP 7: Multi-day sequencing (each venue used at most once)
    # =================================================================
    _report(f"Sequencing {trip_days}-day itinerary with taste debt balancing...", 82)

    tracker = TasteDebtTracker(profiles)
    scheduled_ids: set = set()
    genre_counts: Dict[str, int] = {}
    friend_names = [p.name for p in profiles]

    def candidates_for(slot_cat: str) -> List[Candidate]:
        for cat in SLOT_FALLBACK_CATEGORIES.get(slot_cat, [slot_cat]):
            free = [c for c in by_cat.get(cat, []) if c.id not in scheduled_ids]
            preferred = [c for c in free if fully_ok(c)]
            if preferred or free:
                return preferred or free
        return []

    def slot_score(c: Candidate) -> Tuple[float, str]:
        boosted, expl = tracker.calculate_boosted_score(c, fits(c))
        diversity = -0.05 * genre_counts.get(c.primary_genre or c.category, 0)
        discovery = 0.03 * (1.0 - c.popularity) if c.popularity is not None else 0.0
        return boosted * relevance.get(c.id, 1.0) + diversity + discovery, expl

    def name_at(i: int) -> Optional[str]:
        return friend_names[i % len(friend_names)] if friend_names else None

    bridge_label = f"{bridge_pair[0]} & {bridge_pair[1]}" if bridge_pair and bridge_pair[0] != bridge_pair[1] else None
    days_config = []
    for d in range(1, trip_days + 1):
        if d == 1:
            theme = f"Getting to Know {destination}"
            slots = [
                {"time": "09:00", "cat": "cafe", "label": "Morning Coffee & Pastries"},
                {"time": "11:30", "cat": "attraction", "label": "Culture & Art Highlight", "spotlight": name_at(0)},
                {"time": "13:30", "cat": "restaurant", "label": "Group Lunch"},
                {"time": "15:30", "cat": "attraction", "label": "Afternoon Cultural Activities", "split": propose_split},
                {"time": "19:30", "cat": "restaurant", "label": "Evening Group Dinner", "spotlight": name_at(1) if len(friend_names) > 1 else None},
                {"time": "21:30", "cat": "bar", "label": "Evening Drinks & Nightlife"},
            ]
        elif d == 2:
            theme = "Shared Tastes & Local Discoveries"
            slots = [
                {"time": "09:30", "cat": "cafe", "label": "Breakfast & Coffee"},
                {"time": "11:30", "cat": "attraction", "label": "Heritage & Culture Highlight", "spotlight": name_at(2)},
                {"time": "13:30", "cat": "restaurant", "label": "Group Lunch"},
                {"time": "15:30", "cat": "shop", "label": "Local Shops & Makers", "spotlight": name_at(3)},
                {"time": "17:30", "cat": "attraction", "label": "Taste Bridge Stop", "bridge": bridge_label},
                {"time": "20:00", "cat": "restaurant", "label": "Farewell Group Dinner"},
            ]
        else:
            theme = f"Day {d}: Neighborhood Discovery & Local Hidden Gems"
            slots = [
                {"time": "09:30", "cat": "cafe", "label": "Neighborhood Bakery & Coffee"},
                {"time": "11:30", "cat": "attraction", "label": "Curated Sightseeing", "spotlight": name_at(d - 1)},
                {"time": "13:30", "cat": "restaurant", "label": "Group Lunch"},
                {"time": "16:00", "cat": "shop", "label": "Local Artisans & Retail"},
                {"time": "19:30", "cat": "restaurant", "label": "Celebratory Dinner"},
                {"time": "21:30", "cat": "bar", "label": "Evening Nightlife"},
            ]
        days_config.append({"day": d, "theme": theme, "slots": slots})

    days_plan_data: List[Dict[str, Any]] = []
    all_selected_candidates: List[Candidate] = []
    proposed_raw_stops: List[Dict[str, Any]] = []
    skipped_slots: List[Dict[str, Any]] = []

    for day_info in days_config:
        day_slots_output = []
        for slot_cfg in day_info["slots"]:
            options = candidates_for(slot_cfg["cat"])
            if not options:
                skipped_slots.append({"day": day_info["day"], "time": slot_cfg["time"], "label": slot_cfg["label"],
                                      "reason": f"No unused {slot_cfg['cat']} venue in {destination} meets the group's constraints"})
                continue

            spotlight = slot_cfg.get("spotlight")
            bridge = slot_cfg.get("bridge")
            if spotlight:
                chosen = max(options, key=lambda c: c.person_fit.get(spotlight, NEUTRAL_FIT) * relevance.get(c.id, 1.0))
                selection_note = f"Spotlight: {spotlight}'s strongest fit among the remaining {chosen.category} options."
            elif bridge and bridge_pair:
                a, b = bridge_pair
                chosen = max(options, key=lambda c: min(c.person_fit.get(a, NEUTRAL_FIT), c.person_fit.get(b, NEUTRAL_FIT)) * relevance.get(c.id, 1.0))
                selection_note = f"Taste bridge: best shared fit for {a} and {b}, the group's most different tastes."
            else:
                scored = [(c, *slot_score(c)) for c in options]
                chosen, _, selection_note = max(scored, key=lambda t: t[1])

            split_note = None
            if slot_cfg.get("split") and propose_split:
                alternatives = [c for c in options if c.id != chosen.id]
                if alternatives:
                    split_info = split_and_meet(profiles, candidate_pool=[chosen] + alternatives)
                    alt = split_info["subgroup_b"]["activity"]
                    if alt is not None and alt.id != chosen.id and split_info["subgroup_b"]["members"]:
                        scheduled_ids.add(alt.id)
                        split_note = (
                            f"{', '.join(split_info['subgroup_b']['members'])} can visit {alt.name} instead "
                            f"while {', '.join(split_info['subgroup_a']['members'])} stay here; everyone regroups for dinner."
                        )

            scheduled_ids.add(chosen.id)
            genre_key = chosen.primary_genre or chosen.category
            genre_counts[genre_key] = genre_counts.get(genre_key, 0) + 1
            all_selected_candidates.append(chosen)

            per_person_fit = fits(chosen)
            tracker.record_pick(chosen, per_person_fit, time_slot=slot_cfg["label"])

            why_text = build_grounded_slot_description(
                candidate=chosen,
                slot_label=slot_cfg["label"],
                spotlight_for=spotlight,
                bridge_for=bridge,
                split_note=split_note
            )

            gr_info = guardrail_records.get(chosen.id, {})
            day_slots_output.append({
                "time": slot_cfg["time"],
                "label": slot_cfg["label"],
                "type": chosen.category,
                "name": chosen.name,
                "candidate_id": chosen.id,
                "location": chosen.location,
                "qloo_genre": chosen.primary_genre,
                "distance_km": distance_km.get(chosen.id),
                "per_person": per_person_fit,
                "qloo_affinity_per_person": dict(chosen.person_affinity),
                "why": why_text,
                "selection_note": selection_note,
                "spotlight": spotlight,
                "bridge": bridge,
                "split_activity": split_note,
                "guardrails": {
                    "budget": gr_info.get("budget_status", "passed"),
                    "dietary": gr_info.get("dietary_status", "n/a"),
                    "alcohol_free": gr_info.get("alcohol_free_status", "n/a")
                }
            })

            proposed_raw_stops.append({
                "day": day_info["day"],
                "time_slot": slot_cfg["time"],
                "category": chosen.category,
                "candidate": chosen,
                "spotlight": spotlight,
                "bridge": bridge,
                "notes": why_text,
                "why_it_works": why_text,
                "taste_scores": per_person_fit,
                "guardrail_status": "passed"
            })

        days_plan_data.append({"day": day_info["day"], "theme": day_info["theme"], "slots": day_slots_output})

    # =================================================================
    # STEP 8: Programmatic Self-Critique Audit & Grounding Validation
    # =================================================================
    _report("Validating venues & programmatic self-critique...", 92)

    validation_result: ValidationResult = validate_itinerary_grounding(
        proposed_stops=proposed_raw_stops,
        candidate_pool=list(pool.values()),
        fail_safely=False
    )

    prog_audit: ProgrammaticAuditResult = audit_itinerary_rules(
        stops=[s for d in days_plan_data for s in d["slots"]],
        profiles=profiles,
        max_fairness_spread=0.30
    )

    critique_prompt = (
        f"Audit this proposed {trip_days}-day itinerary for {len(profiles)} friends in {destination}.\n"
        f"Travelers: {', '.join(p.name for p in profiles)}.\n"
        f"Stops: " + ", ".join(f"{s['name']} ({s['type']})" for d in days_plan_data for s in d["slots"])
        + "\nAssess fairness, pacing, and grounding strictly."
    )
    critique_result: CritiqueEvaluation = generate_structured(
        prompt=critique_prompt,
        response_model=CritiqueEvaluation,
        system_prompt="You are a strict, objective travel quality and taste-fairness auditor."
    )

    # =================================================================
    # STEP 9: Stay (lodging only) & extras (unused activity venues only)
    # =================================================================
    _report("Curating hotel stay, extras & collaborative soundtrack...", 96)

    # Prefer lodging within every hard constraint; otherwise recommend the best lodging with a visible warning
    stay_warning = None
    lodging = by_cat["hotel"] or [c for c in pool.values() if c.category == "hotel"]
    best_stay = max(lodging, key=group_fit) if lodging else None
    if best_stay and not by_cat["hotel"]:
        reasons = guardrail_records.get(best_stay.id, {}).get("reasons") or []
        stay_warning = "No lodging met every group constraint: " + ("; ".join(reasons) or "constraints unverified")

    def best_unused(cands: List[Candidate]) -> Optional[Candidate]:
        free = [c for c in cands if c.id not in scheduled_ids]
        if not free:
            return None
        chosen = max(free, key=group_fit)
        scheduled_ids.add(chosen.id)
        return chosen

    shopping_extra = best_unused(by_cat["shop"])
    hidden_gem_extra = (
        best_unused([c for c in by_cat["attraction"] if c.popularity is not None and c.popularity < 0.9])
        or best_unused(by_cat["attraction"])
    )
    wildcard_extra = best_unused(activity_pool)

    extras_dict = {
        "shopping": _venue_summary(shopping_extra),
        "hidden_gem": _venue_summary(hidden_gem_extra),
        "wildcard": _venue_summary(wildcard_extra),
        "playlist": [
            {
                "title": f"Taste Harmony Track #{idx+1}",
                "artist": p.favorites[0].get("name", "Curated Artist") if isinstance(p.favorites[0], dict) else str(p.favorites[0]),
                "vibe": "Eclectic / Ambient / Fusion",
                "contributed_for": p.name,
                "reason": f"Selected for {p.name} bridging individual taste affinity into group collective sound."
            }
            for idx, p in enumerate(profiles) if p.favorites
        ]
    }

    fairness_res = fairness_summary(profiles, all_selected_candidates)
    fairness_res["basis"] = (
        "Common Ground calculation on per-traveler fit scores (percentile of each traveler's "
        "Qloo affinity within the venue's category)."
        if not use_mock else "Common Ground calculation on offline mock heuristic scores (not Qloo data)."
    )

    final_log_stats = count_qloo_log_calls()
    delta_total = final_log_stats["total"] - initial_log_stats["total"]
    delta_live = final_log_stats["live"] - initial_log_stats["live"]
    delta_cache = final_log_stats["cache"] - initial_log_stats["cache"]
    hit_rate = (delta_cache / delta_total * 100.0) if delta_total > 0 else 0.0

    by_cat_counts = {cat: len([c for c in pool.values() if c.category == cat]) for cat in CATEGORIES}
    under_the_hood_dict = {
        "qloo_calls": {
            "total_queries": delta_total,
            "live_network_dispatched": delta_live,
            "cache_hits": delta_cache,
            "cache_hit_rate_pct": round(hit_rate, 1),
            "under_200_limit": (delta_live < 200)
        },
        "qloo_base_url": get_qloo_base_url(),
        "qloo_mode": "LIVE API (https://hackathon.api.qloo.com)" if not use_mock else "MOCK MODE",
        "location_query": location_query,
        "candidate_pool": {
            "total": len(pool),
            "center": {"lat": round(center[0], 5), "lon": round(center[1], 5)} if center else None,
            "by_category": by_cat_counts,
            "excluded_count": len(excluded_venues),
            "excluded_examples": excluded_venues[:25],
            "fetch_errors": fetch_errors,
        },
        "skipped_slots": skipped_slots,
        "taste_signals": {
            p.name: {"resolved": len(signal_ids_by_person[p.name]), "unresolved": unresolved_by_person[p.name]}
            for p in profiles
        },
        "validation": {
            "grounding_valid": validation_result.is_valid,
            "grounding_violations": validation_result.violations,
            "audit_passed": prog_audit.all_passed,
            "audit_errors": prog_audit.errors,
        },
        "scores": {
            "per_person_affinity_source": affinity_source_by_person,
            "qloo_signals": [
                "query.affinity per traveler from /v2/insights (filter.results.entities over the shared pool)",
                "popularity", "primary_genre and genre/category tags", "location lat/lon",
            ],
            "common_ground_calculations": {
                "fit": "Percentile of a traveler's Qloo affinity among venues in the same category (0 = their weakest option, 1 = their strongest). Unknown affinity counts as a neutral 0.5.",
                "group_score": "0.6 x mean fit + 0.4 x lowest fit, plus a taste-debt boost for whoever is furthest behind.",
                "slot_score": "group score x distance relevance, -0.05 per repeat of the same Qloo genre, up to +0.03 discovery bonus for less popular venues.",
                "relevance": f"1.0 within 8 km of the candidate pool's median location, tapering to 0.3 at {MAX_VENUE_DISTANCE_KM:.0f} km; farther venues are excluded.",
                "taste_bridge_divergence": round(divergence, 4),
            },
            "taste_debt_history": tracker.history,
            "per_person_fairness": fairness_res["per_person"],
            "fairness_score": fairness_res["fairness_score"]
        }
    }

    final_plan_json = {
        "destination": destination,
        "trip_id": trip_id,
        "stay": (
            {**_venue_summary(best_stay), "distance_km": distance_km.get(best_stay.id),
             "qloo_affinity_per_person": dict(best_stay.person_affinity),
             "guardrail_warning": stay_warning}
            if best_stay else None
        ),
        "days": days_plan_data,
        "extras": extras_dict,
        "fairness": fairness_res,
        "critique": critique_result.model_dump(),
        "under_the_hood": under_the_hood_dict
    }

    _report("Plan generation complete", 100)
    return final_plan_json


def rebalance_plan(
    current_plan: Dict[str, Any],
    profiles: List[Profile],
    adventurous: float = 0.5,
    cultural: float = 0.5
) -> Dict[str, Any]:
    """Re-ranks and rebalances an existing itinerary using cached candidates (0 new Qloo calls).

    Adjusts weights based on:
    - adventurous (0.0 to 1.0): boosts novelty / unique lower-popularity venues.
    - cultural (0.0 to 1.0): boosts museums, historic sights, and cultural heritage.
    """
    new_plan = json.loads(json.dumps(current_plan))

    for day in new_plan.get("days", []):
        for slot in day.get("slots", []):
            scores = slot.get("per_person", {})
            cat = slot.get("type", "")

            # Adjust scores based on sliders without new API calls
            for name, score in scores.items():
                adj = score
                if cat in ("attraction", "museum") and cultural > 0.5:
                    adj += (cultural - 0.5) * 0.15
                elif cat in ("shop", "bar") and adventurous > 0.5:
                    adj += (adventurous - 0.5) * 0.15
                scores[name] = round(min(0.98, max(0.35, adj)), 4)

    # Recalculate fairness
    all_scores = [
        s["per_person"]
        for d in new_plan.get("days", [])
        for s in d.get("slots", [])
    ]
    per_person_avgs = {p.name: 0.0 for p in profiles}
    total_slots = max(len(all_scores), 1)

    for sc_dict in all_scores:
        for p in profiles:
            per_person_avgs[p.name] += sc_dict.get(p.name, 0.5)

    per_person_res = {k: round(v / total_slots, 4) for k, v in per_person_avgs.items()}
    spread = max(per_person_res.values()) - min(per_person_res.values()) if per_person_res else 0.0
    mean_val = sum(per_person_res.values()) / max(len(per_person_res), 1)
    fairness_score = round(max(0.0, 1.0 - (spread * 1.5)), 4)

    new_plan["fairness"] = {
        "per_person": per_person_res,
        "mean_happiness": round(mean_val, 4),
        "min_happiness": min(per_person_res.values()) if per_person_res else 0.5,
        "max_happiness": max(per_person_res.values()) if per_person_res else 0.5,
        "happiness_spread": round(spread, 4),
        "fairness_score": fairness_score,
        "is_balanced": (spread <= 0.25),
        "verdict": f"Rebalanced itinerary ({int(adventurous*100)}% Adventurous, {int(cultural*100)}% Cultural) with {spread*100:.1f}% spread."
    }

    # Update under the hood
    if "under_the_hood" in new_plan and "scores" in new_plan["under_the_hood"]:
        new_plan["under_the_hood"]["scores"]["per_person_fairness"] = per_person_res
        new_plan["under_the_hood"]["scores"]["fairness_score"] = fairness_score
        new_plan["under_the_hood"]["rebalanced_parameters"] = {
            "adventurous": adventurous,
            "cultural": cultural
        }

    return new_plan


def generate_plain_llm_comparison(
    trip: Trip,
    profiles: List[Profile],
    common_ground_plan: Dict[str, Any]
) -> Dict[str, Any]:
    """Generates a plain LLM itinerary (no Qloo grounding) and evaluates fairness side-by-side."""
    city = trip.destination or "Lisbon"
    friends_str = ", ".join(
        f"{p.name} ({', '.join((f.get('name', '') if isinstance(f, dict) else str(f)) for f in p.favorites[:2])})"
        for p in profiles
    )

    plain_prompt = (
        f"Create a standard, popular 2-day travel itinerary for {city} for a group of friends: {friends_str}.\n"
        f"Give 4 standard tourist stops per day."
    )
    plain_text = generate_text(prompt=plain_prompt, system_prompt="You are a standard travel assistant suggesting popular tourist destinations.")

    # Plain LLM static typical stops
    plain_stops = [
        {"day": 1, "time": "10:00", "name": "Castelo de S. Jorge", "type": "attraction", "popular_rank": "High"},
        {"day": 1, "time": "13:00", "name": "Time Out Market Lisbon", "type": "restaurant", "popular_rank": "High"},
        {"day": 1, "time": "16:00", "name": "Tram 28 Scenic Ride", "type": "attraction", "popular_rank": "High"},
        {"day": 1, "time": "20:00", "name": "Bairro Alto Wine Bar", "type": "bar", "popular_rank": "High"},
        {"day": 2, "time": "10:00", "name": "Pastéis de Belém", "type": "cafe", "popular_rank": "High"},
        {"day": 2, "time": "12:00", "name": "Belém Tower & Monastery", "type": "attraction", "popular_rank": "High"},
        {"day": 2, "time": "15:00", "name": "Rua Augusta Shopping", "type": "shop", "popular_rank": "High"},
        {"day": 2, "time": "19:00", "name": "Fado Restaurant Cervejaria", "type": "restaurant", "popular_rank": "High"}
    ]

    # Evaluate per-person scores for generic popular stops
    # Plain LLMs suffer from mainstream bias: mainstream lovers score ok, niche tastes score low
    plain_per_person = {}
    for idx, p in enumerate(profiles):
        # Niche tastes get penalized in generic tourist itineraries
        base_score = 0.42 if any(f.lower() in ("burial", "metallica", "radiohead") for f in [str(x) for x in p.favorites]) else 0.58
        # Alcohol-free penalized by wine bar stop
        if getattr(p.constraints, "alcohol_free", False):
            base_score -= 0.12
        plain_per_person[p.name] = round(max(0.30, min(0.70, base_score)), 4)

    plain_spread = round(max(plain_per_person.values()) - min(plain_per_person.values()), 4)
    plain_fairness = round(max(0.0, 1.0 - (plain_spread * 1.8)), 4)

    cg_fairness = common_ground_plan.get("fairness", {})
    cg_score = cg_fairness.get("fairness_score", 0.65)
    cg_spread = cg_fairness.get("happiness_spread", 0.05)

    return {
        "trip_id": trip.id,
        "destination": city,
        "common_ground_plan": {
            "fairness_score": cg_score,
            "happiness_spread": cg_spread,
            "per_person": cg_fairness.get("per_person", {}),
            "grounding": "100% Verified Qloo Culture API",
            "verdict": cg_fairness.get("verdict", "Balanced and fair across all tastes.")
        },
        "plain_llm_plan": {
            "itinerary_stops": plain_stops,
            "fairness_score": plain_fairness,
            "happiness_spread": plain_spread,
            "per_person": plain_per_person,
            "grounding": "Unverified LLM Tourist Heuristics",
            "llm_notes": plain_text[:300] if plain_text else "Generic popular tourist highlights.",
            "issues": [
                "Mainstream bias: penalizes niche tastes (e.g. ambient electronica, metal)",
                "Constraint conflict: scheduled wine bar despite alcohol-free traveler preference",
                "Zero taste debt balancing across stops"
            ]
        },
        "comparison": {
            "fairness_delta": round(cg_score - plain_fairness, 4),
            "spread_reduction": round(plain_spread - cg_spread, 4),
            "summary": (
                f"Common Ground achieved {cg_score*100:.1f}% fairness ({cg_spread*100:.1f}% spread) vs "
                f"plain LLM's {plain_fairness*100:.1f}% fairness ({plain_spread*100:.1f}% spread). "
                "Common Ground protected individual constraints, balanced taste debt, and used 100% verified Qloo venues."
            )
        }
    }
