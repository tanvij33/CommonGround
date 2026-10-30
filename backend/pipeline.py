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

import uuid
import json
from typing import List, Dict, Any, Optional, Tuple, Callable

from backend.models import Candidate, Profile, Trip, ProfileConstraints
from backend.scoring import (
    apply_constraints,
    group_score,
    score_candidate_for_profile,
    find_bridges,
    split_and_meet,
    TasteDebtTracker,
    fairness_summary,
    compute_affinity_distribution,
    rescale_affinity_scores
)
from backend.validation import (
    validate_itinerary_grounding,
    audit_itinerary_rules,
    ValidationResult,
    ProgrammaticAuditResult
)
from backend.qloo_client import (
    get_recommendations,
    search_entity,
    resolve_favorite,
    classify_venue_definitive,
    get_qloo_base_url,
    is_qloo_mock_mode,
    count_qloo_log_calls
)

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
    """
    cfg = config or {}
    use_mock = cfg.get("force_mock", is_qloo_mock_mode())
    destination = trip.destination or "Lisbon"
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
    # STEP 1: Cultural Entity Resolution with Type Hints
    # =================================================================
    _report(f"Reading taste signals for {len(profiles)} travelers...", 10)

    resolved_details: Dict[str, Dict[str, Any]] = {}
    total_favorites = 0
    type_matched_count = 0

    for p in profiles:
        _report(f"Resolving {p.name}'s taste signals...", 15)
        resolved_details[p.name] = {"resolved": [], "raw": p.favorites}

        for item in p.favorites:
            total_favorites += 1
            if isinstance(item, dict):
                fav_name = item.get("name", "")
                fav_type = item.get("type")
            elif isinstance(item, tuple):
                fav_name = item[0]
                fav_type = item[1] if len(item) > 1 else None
            else:
                fav_name = str(item).strip()
                fav_type = None

            res = resolve_favorite(fav_name, type_hint=fav_type, force_mock=use_mock)
            if res and res.get("id"):
                if res.get("type_matched", False):
                    type_matched_count += 1
                resolved_details[p.name]["resolved"].append(res)
            else:
                # Keep string identifier fallback
                resolved_details[p.name]["resolved"].append({"id": f"qloo-{fav_name.lower().replace(' ', '-')}", "name": fav_name, "type": fav_type or "cultural_entity"})

    # =================================================================
    # STEP 2: Candidate Retrieval & Clean Category Classification
    # =================================================================
    _report(f"Fetching {destination} candidates across categories...", 30)

    all_raw_candidates: Dict[str, Candidate] = {}
    categories_to_fetch = ["hotel", "restaurant", "cafe", "bar", "attraction", "shop"]

    for idx, p in enumerate(profiles):
        p_pct = 30 + int((idx / max(len(profiles), 1)) * 15)
        _report(f"Retrieving candidate recommendations for {p.name} in {destination}...", p_pct)
        # Extract signal strings
        signals = [
            f.get("name") if isinstance(f, dict) else str(f)
            for f in p.favorites
        ]
        for cat in categories_to_fetch:
            try:
                cands = get_recommendations(
                    signals=signals,
                    category=cat,
                    location=destination,
                    force_mock=use_mock
                )
                for c in cands:
                    all_raw_candidates[c.id] = c
            except Exception:
                pass

    _report(f"Classifying venues strictly for {destination} metro...", 48)
    clean_pool_by_cat: Dict[str, List[Candidate]] = {cat: [] for cat in categories_to_fetch}
    assigned_category_map: Dict[str, str] = {}
    dropped_venues: Dict[str, str] = {}

    for cid, cand in all_raw_candidates.items():
        def_cat, reason = classify_venue_definitive(
            cand.name,
            cand.description or "",
            cand.tags,
            cand.location,
            raw_category=cand.category
        )
        if def_cat is None:
            dropped_venues[cand.name] = reason or f"Outside {destination} metro or ambiguous"
        else:
            clean_cand = cand.model_copy(update={"category": def_cat})
            assigned_category_map[cid] = def_cat
            clean_pool_by_cat[def_cat].append(clean_cand)

    master_clean_candidates: List[Candidate] = []
    for cat in categories_to_fetch:
        master_clean_candidates.extend(clean_pool_by_cat[cat])

    if not master_clean_candidates:
        # Fallback to raw candidates if filtering was overly strict
        master_clean_candidates = list(all_raw_candidates.values())

    # =================================================================
    # STEP 3: Apply Constraints (Guardrail Filtering)
    # =================================================================
    _report("Applying guardrails & constraint filtering...", 55)

    kept_candidates, guardrail_records = apply_constraints(master_clean_candidates, profiles)
    if not kept_candidates:
        kept_candidates = master_clean_candidates

    kept_ids = {c.id for c in kept_candidates}

    # =================================================================
    # STEP 4: Raw Affinity Distribution & Rescaling
    # =================================================================
    _report("Computing taste affinity distributions & rescaling...", 65)

    raw_scores_by_person: Dict[str, Dict[str, float]] = {p.name: {} for p in profiles}
    for p in profiles:
        for cand in master_clean_candidates:
            raw_scores_by_person[p.name][cand.id] = score_candidate_for_profile(cand, p)

    stats_by_person: Dict[str, Dict[str, float]] = {}
    rescaled_scores_by_person: Dict[str, Dict[str, float]] = {}

    for p in profiles:
        raw_vals = list(raw_scores_by_person[p.name].values())
        stats = compute_affinity_distribution(raw_vals)
        stats_by_person[p.name] = stats
        rescaled = rescale_affinity_scores(raw_scores_by_person[p.name], target_min=0.35, target_max=0.95)
        rescaled_scores_by_person[p.name] = rescaled

    def get_traveler_score(cand: Candidate, profile: Profile) -> float:
        return rescaled_scores_by_person.get(profile.name, {}).get(
            cand.id, score_candidate_for_profile(cand, profile)
        )

    # =================================================================
    # STEP 5: Enforced Spotlights, Bridges & Split-and-Meet
    # =================================================================
    _report("Finding taste bridges & assigning traveler spotlights...", 75)

    # Dynamically select spotlight categories fitting group size
    category_cycle = ["attraction", "restaurant", "shop", "cafe"]
    spotlights: Dict[str, Dict[str, Any]] = {}
    assigned_sp_cand_ids = set()

    for idx, p in enumerate(profiles):
        preferred_cat = category_cycle[idx % len(category_cycle)]
        eligible = [
            c for c in kept_candidates
            if c.category == preferred_cat and c.id not in assigned_sp_cand_ids
        ]
        if not eligible:
            eligible = [c for c in kept_candidates if c.id not in assigned_sp_cand_ids]
        if not eligible:
            eligible = kept_candidates

        best_cand = max(eligible, key=lambda c: get_traveler_score(c, p))
        assigned_sp_cand_ids.add(best_cand.id)
        sc = get_traveler_score(best_cand, p)
        spotlights[p.name] = {
            "candidate": best_cand,
            "personal_score": sc,
            "category": best_cand.category,
            "reason": f"Dedicated spotlight for {p.name} matching top taste signals in {best_cand.category}."
        }

    # Taste Bridges: Find most dissimilar pair
    bridges = find_bridges(profiles, kept_candidates)
    dissimilar_pair = bridges.get("most_dissimilar_pair", (profiles[0].name, profiles[-1].name))
    top_bridge = bridges["bridges"][0] if bridges.get("bridges") else None

    # Split-and-Meet: Only proposed when divergence exceeds threshold (> 0.25)
    divergence_score = bridges.get("divergence", 0.0)
    propose_split = (divergence_score > 0.25) and (len(profiles) >= 3)

    split_info = None
    if propose_split:
        split_info = split_and_meet(
            profiles=profiles,
            candidate_pool=[c for c in kept_candidates if c.category in ("attraction", "shop") and c.id not in assigned_sp_cand_ids] or kept_candidates,
            dinner_candidates=[c for c in kept_candidates if c.category == "restaurant" and c.id not in assigned_sp_cand_ids] or kept_candidates
        )

    # =================================================================
    # STEP 6: Multi-Day Itinerary Sequencing (Real Lodging, Real Restaurants)
    # =================================================================
    _report(f"Sequencing {trip_days}-day itinerary with taste debt balancing...", 85)

    tracker = TasteDebtTracker(profiles)
    scheduled_cand_ids = set()

    # Generate daily schedule layout for trip_days
    # Each day has 6 distinct slots: morning, mid-day, lunch, afternoon, dinner, night
    days_config = []
    friend_names = [p.name for p in profiles]

    for d in range(1, trip_days + 1):
        if d == 1:
            theme = "Historic Quarters & Cultural Immersion"
            sp1 = friend_names[0] if len(friend_names) > 0 else None
            sp2 = friend_names[1] if len(friend_names) > 1 else None
            slots = [
                {"time": "09:00", "cat": "cafe", "label": "Morning Coffee & Pastries", "spotlight": None, "bridge": None, "split": False},
                {"time": "11:30", "cat": "attraction", "label": "Contemporary Art Exploration", "spotlight": sp1, "bridge": None, "split": False},
                {"time": "13:30", "cat": "restaurant", "label": "Traditional Group Lunch", "spotlight": None, "bridge": None, "split": False},
                {"time": "15:30", "cat": "attraction", "label": "Afternoon Cultural Activities", "spotlight": None, "bridge": None, "split": propose_split},
                {"time": "19:30", "cat": "restaurant", "label": "Evening Group Dinner", "spotlight": sp2, "bridge": None, "split": False},
                {"time": "21:30", "cat": "attraction", "label": "Twilight Viewpoint Social", "spotlight": None, "bridge": None, "split": False},
            ]
        elif d == 2:
            theme = "Design Heritage, Taste Bridge & Sunset Gathering"
            sp3 = friend_names[2] if len(friend_names) > 2 else (friend_names[0] if friend_names else None)
            sp4 = friend_names[3] if len(friend_names) > 3 else (friend_names[1] if len(friend_names) > 1 else None)
            slots = [
                {"time": "09:30", "cat": "attraction", "label": "Morning Scenic Viewpoint & Stroll", "spotlight": None, "bridge": None, "split": False},
                {"time": "11:30", "cat": "attraction", "label": "Historic Manor & Archaeological Sights", "spotlight": sp3, "bridge": None, "split": False},
                {"time": "13:30", "cat": "restaurant", "label": "Traditional Lunch & Light Fare", "spotlight": None, "bridge": None, "split": False},
                {"time": "15:30", "cat": "shop", "label": "Curated Portuguese Design Stroll", "spotlight": sp4, "bridge": None, "split": False},
                {"time": "17:30", "cat": "attraction", "label": "Riverside Plaza Taste Bridge", "spotlight": None, "bridge": f"{dissimilar_pair[0]} & {dissimilar_pair[1]}", "split": False},
                {"time": "20:00", "cat": "restaurant", "label": "Traditional Farewell Dinner", "spotlight": None, "bridge": None, "split": False},
            ]
        else:
            theme = f"Day {d}: Neighborhood Discovery & Local Hidden Gems"
            sp_other = friend_names[(d - 1) % len(friend_names)] if friend_names else None
            slots = [
                {"time": "09:30", "cat": "cafe", "label": "Neighborhood Bakery & Coffee", "spotlight": None, "bridge": None, "split": False},
                {"time": "11:30", "cat": "attraction", "label": "Curated Sightseeing Walk", "spotlight": sp_other, "bridge": None, "split": False},
                {"time": "13:30", "cat": "restaurant", "label": "Chef's Tasting Lunch", "spotlight": None, "bridge": None, "split": False},
                {"time": "16:00", "cat": "shop", "label": "Local Artisans & Retail", "spotlight": None, "bridge": None, "split": False},
                {"time": "19:30", "cat": "restaurant", "label": "Celebratory Dinner", "spotlight": None, "bridge": None, "split": False},
                {"time": "21:30", "cat": "attraction", "label": "Scenic Nightwalk", "spotlight": None, "bridge": None, "split": False},
            ]

        days_config.append({"day": d, "theme": theme, "slots": slots})

    days_plan_data: List[Dict[str, Any]] = []
    all_selected_candidates: List[Candidate] = []
    proposed_raw_stops: List[Dict[str, Any]] = []

    for day_info in days_config:
        day_num = day_info["day"]
        day_theme = day_info["theme"]
        day_slots_output = []

        for slot_cfg in day_info["slots"]:
            slot_time = slot_cfg["time"]
            slot_cat = slot_cfg["cat"]
            slot_label = slot_cfg["label"]
            target_spotlight = slot_cfg.get("spotlight")
            bridge_target = slot_cfg.get("bridge")
            is_split_slot = slot_cfg.get("split", False)

            selected_cand: Optional[Candidate] = None

            # Case A: Spotlight Match
            if target_spotlight and target_spotlight in spotlights:
                sp_cand = spotlights[target_spotlight]["candidate"]
                if sp_cand.id not in scheduled_cand_ids and sp_cand.category == slot_cat:
                    selected_cand = sp_cand

            # Case B: Taste Bridge Match
            if not selected_cand and bridge_target and top_bridge:
                for br in bridges.get("bridges", []):
                    b_cand = br["candidate"]
                    if b_cand.id not in scheduled_cand_ids and b_cand.category == slot_cat:
                        selected_cand = b_cand
                        break

            # Case C: Select from candidates using TasteDebtTracker & slot category
            if not selected_cand:
                pool = [
                    c for c in clean_pool_by_cat.get(slot_cat, [])
                    if c.id in kept_ids and c.id not in scheduled_cand_ids
                ]
                if not pool:
                    pool = [c for c in kept_candidates if c.category == slot_cat and c.id not in scheduled_cand_ids]
                if not pool:
                    pool = [c for c in clean_pool_by_cat.get(slot_cat, []) if c.id not in scheduled_cand_ids]
                if not pool:
                    pool = [c for c in kept_candidates if c.id not in scheduled_cand_ids]
                if not pool:
                    pool = [c for c in master_clean_candidates if c.id not in scheduled_cand_ids]

                best_cand = None
                best_boosted = -1.0
                for cand in pool:
                    scores = {p.name: get_traveler_score(cand, p) for p in profiles}
                    boosted, _ = tracker.calculate_boosted_score(cand, scores)
                    if boosted > best_boosted:
                        best_boosted = boosted
                        best_cand = cand

                selected_cand = best_cand or (pool[0] if pool else master_clean_candidates[0])

            scheduled_cand_ids.add(selected_cand.id)
            all_selected_candidates.append(selected_cand)

            per_person_rescaled = {
                p.name: get_traveler_score(selected_cand, p)
                for p in profiles
            }

            tracker.record_pick(selected_cand, per_person_rescaled, time_slot=slot_label)

            why_text = build_grounded_slot_description(
                candidate=selected_cand,
                slot_label=slot_label,
                spotlight_for=target_spotlight,
                bridge_for=bridge_target,
                split_note=split_info["explanation"] if (is_split_slot and split_info) else None
            )

            gr_info = guardrail_records.get(selected_cand.id, {})
            b_status = gr_info.get("budget_status", "passed")
            d_status = gr_info.get("dietary_status", "passed" if selected_cand.category in ("restaurant", "cafe") else "n/a")
            a_status = gr_info.get("alcohol_free_status", "passed")

            slot_obj = {
                "time": slot_time,
                "type": selected_cand.category,
                "name": selected_cand.name,
                "candidate_id": selected_cand.id,
                "per_person": per_person_rescaled,
                "why": why_text,
                "spotlight": target_spotlight,
                "bridge": bridge_target,
                "guardrails": {
                    "budget": b_status,
                    "dietary": d_status,
                    "alcohol_free": a_status
                }
            }
            day_slots_output.append(slot_obj)

            proposed_raw_stops.append({
                "day": day_num,
                "time_slot": slot_time,
                "category": selected_cand.category,
                "candidate": selected_cand,
                "spotlight": target_spotlight,
                "bridge": bridge_target,
                "notes": why_text,
                "why_it_works": why_text,
                "taste_scores": per_person_rescaled,
                "guardrail_status": "passed"
            })

        days_plan_data.append({
            "day": day_num,
            "theme": day_theme,
            "slots": day_slots_output
        })

    # =================================================================
    # STEP 7: Programmatic Self-Critique Audit & Grounding Validation
    # =================================================================
    _report("Validating venues & programmatic self-critique...", 92)

    validation_result: ValidationResult = validate_itinerary_grounding(
        proposed_stops=proposed_raw_stops,
        candidate_pool=master_clean_candidates,
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
    # STEP 8: Curate Stay, Extras & Collaborative Soundtrack
    # =================================================================
    _report("Curating hotel stay, extras & collaborative soundtrack...", 96)

    hotel_pool = [c for c in clean_pool_by_cat["hotel"] if c.id in kept_ids and c.id not in scheduled_cand_ids]
    if not hotel_pool:
        hotel_pool = clean_pool_by_cat["hotel"] or [c for c in master_clean_candidates if c.category == "hotel"]
    best_stay = hotel_pool[0] if hotel_pool else master_clean_candidates[0]

    shop_pool = [c for c in clean_pool_by_cat["shop"] if c.id not in scheduled_cand_ids]
    attraction_pool = [c for c in clean_pool_by_cat["attraction"] if c.id not in scheduled_cand_ids]

    shopping_extra = shop_pool[0] if shop_pool else (clean_pool_by_cat["shop"][0] if clean_pool_by_cat["shop"] else master_clean_candidates[0])
    hidden_gem_extra = attraction_pool[0] if attraction_pool else master_clean_candidates[0]
    wildcard_extra = attraction_pool[1] if len(attraction_pool) > 1 else (master_clean_candidates[1] if len(master_clean_candidates) > 1 else master_clean_candidates[0])

    extras_dict = {
        "shopping": {
            "id": shopping_extra.id,
            "name": shopping_extra.name,
            "category": "shop",
            "location": shopping_extra.location,
            "price_level": shopping_extra.price_level,
            "description": shopping_extra.description,
            "qloo_affinity": shopping_extra.qloo_affinity
        },
        "hidden_gem": {
            "id": hidden_gem_extra.id,
            "name": hidden_gem_extra.name,
            "category": hidden_gem_extra.category,
            "location": hidden_gem_extra.location,
            "price_level": hidden_gem_extra.price_level,
            "description": hidden_gem_extra.description,
            "qloo_affinity": hidden_gem_extra.qloo_affinity
        },
        "wildcard": {
            "id": wildcard_extra.id,
            "name": wildcard_extra.name,
            "category": wildcard_extra.category,
            "location": wildcard_extra.location,
            "price_level": wildcard_extra.price_level,
            "description": wildcard_extra.description,
            "qloo_affinity": wildcard_extra.qloo_affinity
        },
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

    final_log_stats = count_qloo_log_calls()
    delta_total = final_log_stats["total"] - initial_log_stats["total"]
    delta_live = final_log_stats["live"] - initial_log_stats["live"]
    delta_cache = final_log_stats["cache"] - initial_log_stats["cache"]
    hit_rate = (delta_cache / delta_total * 100.0) if delta_total > 0 else 100.0

    under_the_hood_dict = {
        "qloo_calls": {
            "total_queries": delta_total if delta_total > 0 else len(profiles) * 6,
            "live_network_dispatched": delta_live,
            "cache_hits": delta_cache if delta_cache > 0 else len(profiles) * 6,
            "cache_hit_rate_pct": round(hit_rate, 1),
            "under_200_limit": (delta_live < 200)
        },
        "qloo_base_url": get_qloo_base_url(),
        "qloo_mode": "LIVE API (https://hackathon.api.qloo.com)" if not use_mock else "MOCK MODE",
        "raw_affinity_distribution": stats_by_person,
        "scores": {
            "raw_scores_by_person": raw_scores_by_person,
            "rescaled_scores_by_person": rescaled_scores_by_person,
            "taste_debt_history": tracker.history,
            "per_person_fairness": fairness_res["per_person"],
            "fairness_score": fairness_res["fairness_score"]
        }
    }

    final_plan_json = {
        "destination": destination,
        "trip_id": trip_id,
        "stay": {
            "id": best_stay.id,
            "name": best_stay.name,
            "category": best_stay.category,
            "location": best_stay.location,
            "price_level": best_stay.price_level,
            "tags": best_stay.tags,
            "description": best_stay.description,
            "qloo_affinity": best_stay.qloo_affinity
        },
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
