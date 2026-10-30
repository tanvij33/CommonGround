"""Command-Line Interface (CLI) for Common Ground.

Demonstrates:
1. Full autonomous agent pipeline (--agent, default):
   - 8-step pipeline with live streaming progress events
   - Real-time Qloo candidate pulling across categories
   - Constraint guardrails (budget, dietary, mobility, alcohol)
   - Taste-debt sequencing across 7 daily slots
   - Grounding validation (hallucination rejection & safe fallback)
   - Self-critique audit (fairness, pacing, grounding)
   - Per-stop 'why it works' notes & collaborative Group Playlist
   - Complete serialized Plan JSON output
2. 4-person taste fairness walkthrough (--demo)
3. Single-person cultural query (--single)

Usage:
    # Run the full agent pipeline for 4 demo friends with LIVE Qloo API:
    python3 -m backend.run_cli --agent --city Delhi
    python3 -m backend.run_cli --agent --city Lisbon
    python3 -m backend.run_cli --agent --city Tokyo

    # Run explicitly in offline mock mode:
    python3 -m backend.run_cli --agent --mock --city Delhi

    # Run 4-person taste scoring breakdown:
    python3 -m backend.run_cli --demo --city Delhi

    # Run single-person taste query:
    python3 -m backend.run_cli --single --city Delhi --favorites "specialty coffee, natural wine"
"""

import os
import sys
import json
import argparse
import traceback
from typing import List, Dict, Any

from backend.db import init_db
from backend.models import Candidate, Profile, ProfileConstraints, Plan
from backend.qloo_client import (
    get_recommendations,
    search_entity,
    resolve_favorite,
    resolve_signal_entities,
    get_qloo_base_url,
    get_qloo_api_key,
    is_qloo_mock_mode,
    LOG_FILE_PATH,
    QlooError,
    QlooMissingApiKeyError,
    QlooAuthError,
    QlooNetworkError,
    QlooNoCandidatesError,
    QlooCityNotFoundError,
    QlooNoSignalsResolvedError
)
from backend.scoring import (
    score_candidate_for_profile,
    group_score,
    apply_constraints,
    TasteDebtTracker,
    spotlight_selection,
    find_bridges,
    split_and_meet,
    fairness_summary
)
from backend.agent import plan_trip
from backend.llm import LLM_PROVIDER, LLM_MODEL


CATEGORIES = ["hotel", "restaurant", "cafe", "bar", "attraction", "shop"]


def get_demo_profiles() -> List[Profile]:
    """Returns 4 realistic traveler profiles with deliberately contrasting tastes and constraints."""
    return [
        Profile(
            name="Maya",
            favorites=["specialty coffee", "pour-over", "natural wine", "scandinavian", "brutalism"],
            constraints=ProfileConstraints(budget="$$$", pace="relaxed")
        ),
        Profile(
            name="Liam",
            favorites=["cocktail craft", "speakeasy", "electronic", "techno", "seafood"],
            constraints=ProfileConstraints(budget="$$$", pace="intense")
        ),
        Profile(
            name="Chloe",
            favorites=["contemporary art", "architecture", "art books", "vegan", "vegetarian"],
            constraints=ProfileConstraints(budget="$$", dietary=["vegetarian"])
        ),
        Profile(
            name="Kenji",
            favorites=["traditional", "heritage goods", "vinyl records", "ambient", "classic"],
            constraints=ProfileConstraints(budget="$$$", accessibility=["step-free"])
        ),
    ]


def format_category_title(category: str) -> str:
    icons = {
        "hotel": "🏨 HOTELS",
        "restaurant": "🍽️  RESTAURANTS",
        "cafe": "☕ CAFES",
        "bar": "🍷 BARS & NIGHTLIFE",
        "attraction": "🏛️  CULTURE & ATTRACTIONS",
        "shop": "🛍️  DESIGN & SHOPS",
    }
    return icons.get(category, category.upper())


def get_mode_banner() -> str:
    """Returns a clear display banner indicating Live vs Mock Qloo mode."""
    if is_qloo_mock_mode():
        return "🟡 MOCK / OFFLINE MODE (Local catalog: Lisbon, Tokyo, Delhi)"
    else:
        return f"🟢 LIVE QLOO API MODE (Target: {get_qloo_base_url()})"


def print_qloo_error(err: QlooError):
    """Prints a styled, actionable diagnostic error block for Qloo failures."""
    print("\n" + "=" * 80)
    print("  ❌ QLOO CONFIGURATION / EXECUTION ERROR")
    print("=" * 80)
    print(f"\n{err}\n")
    print("=" * 80 + "\n")


# =====================================================================
# Full Agent Pipeline Runner with Streaming Progress & Plan JSON
# =====================================================================

def run_agent_pipeline(city: str, dump_json: bool = True):
    """Executes the full agent pipeline for 4 demo travelers and prints final Plan JSON."""
    init_db()
    profiles = get_demo_profiles()

    print("\n" + "=" * 80)
    print("      COMMON GROUND — AUTONOMOUS MULTI-AGENT TRIP PLANNER (PHASE 3)")
    print("=" * 80)
    print(f"Destination:   {city.title()}")
    print(f"Group:         {', '.join(p.name for p in profiles)} (4 travelers)")
    print(f"Qloo Mode:     {get_mode_banner()}")
    print(f"LLM Provider:  {LLM_PROVIDER} (Model: {LLM_MODEL})")
    print(f"Audit Log:     {LOG_FILE_PATH}")
    print("-" * 80)

    print("\n👥 RESOLVING CULTURAL FAVORITES PER TRAVELER:")
    for p in profiles:
        print(f"  • {p.name}:")
        p_ids, p_resolved, p_skipped = resolve_signal_entities(p.favorites)
        for fav in p.favorites:
            matched = next((r for r in p_resolved if r.get("query", "").lower() == fav.lower().strip()), None)
            if matched:
                print(f"      - {fav:<22} -> RESOLVED: {matched['name']} [{matched['subtype']}] (ID: {matched['id']})")
            else:
                print(f"      - {fav:<22} -> NOT FOUND (SKIPPED)")
        if p_skipped:
            print(f"      ⚠️  Skipped {len(p_skipped)} unresolved: {', '.join(p_skipped)}")

    print("\n📡 STREAMING AGENT PROGRESS EVENTS:")

    def on_progress(event: Dict[str, Any]):
        pct = event.get("percent", 0)
        step = event.get("step", "").ljust(18)
        msg = event.get("message", "")
        bar_len = int(pct / 4) # 25 chars max
        bar = "█" * bar_len + "░" * (25 - bar_len)
        print(f"  [{bar}] {pct:>3}% | {step} | {msg}")

    try:
        # Run full planning pipeline
        plan: Plan = plan_trip(
            trip_id=f"trip-{city.lower()}-4friends",
            destination=city,
            profiles=profiles,
            on_progress=on_progress
        )
    except QlooError as e:
        print_qloo_error(e)
        sys.exit(1)

    print("\n" + "=" * 80)
    print(f"  📋 FINAL ASSEMBLED ITINERARY FOR {city.upper()} (7 DAILY STOPS + STAY & EXTRAS)")
    print("=" * 80)

    if plan.stay:
        print(f"\n🏨 Recommended Stay: {plan.stay.name} [{plan.stay.price_level}] - {plan.stay.location}")
        print(f"   Tags: {', '.join(plan.stay.tags[:4])}")

    for idx, stop in enumerate(plan.itinerary, 1):
        cand = stop.candidate
        scores_str = " | ".join(f"{name}: {int(score*100)}%" for name, score in stop.taste_scores.items())
        print(f"\n  Stop {idx}: {stop.time_slot.upper()} -> {cand.name} [{cand.price_level}]")
        print(f"  Category:    {cand.category.title()} | Location: {cand.location}")
        print(f"  Match Fit:   {scores_str}")
        print(f"  Why it works: {stop.why_it_works}")
        if stop.guardrail_status != "passed":
            print(f"  Guardrail:   ⚠️ {stop.guardrail_status}")

    if plan.extras:
        print(f"\n🛍️  Curated Extras & Neighborhood Strolls in {city.title()}:")
        for ex in plan.extras:
            print(f"  • {ex.name} ({ex.category}) - {ex.description or ', '.join(ex.tags[:3])}")

    print("\n" + "=" * 80)
    print("  🎵 COLLABORATIVE GROUP PLAYLIST")
    print("=" * 80)
    for track in plan.playlist:
        print(f"  ▶ \"{track.title}\" by {track.artist} [{track.vibe}]")
        print(f"    Inspired by: {track.contributed_for} — {track.reason}\n")

    print("=" * 80)
    print("  🧐 SELF-CRITIQUE AUDIT REPORT")
    print("=" * 80)
    if plan.critique:
        c = plan.critique
        print(f"  Fairness Audit:   {'✓ PASSED' if c.get('fairness_passed') else '⚠️ ATTENTION'} ({int(c.get('fairness_score', 0)*100)}% score)")
        print(f"  Fairness Notes:   {c.get('fairness_notes')}")
        print(f"  Pacing Audit:     {'✓ PASSED' if c.get('pacing_passed') else '⚠️ ATTENTION'}")
        print(f"  Pacing Notes:     {c.get('pacing_notes')}")
        print(f"  Grounding Audit:  {'✓ PASSED' if c.get('grounding_passed') else '⚠️ ATTENTION'}")
        print(f"  Grounding Notes:  {c.get('grounding_notes')}")
        if c.get("adjustments_made"):
            print("  Adjustments Made:")
            for adj in c.get("adjustments_made", []):
                print(f"    • {adj}")
        print(f"  Assessment:       {c.get('overall_assessment')}")

    if dump_json:
        print("\n" + "=" * 80)
        print(f"  💾 FINAL COMPLETE PLAN JSON FOR {city.upper()} (VALIDATED PYDANTIC MODEL)")
        print("=" * 80)
        plan_dict = plan.model_dump()
        print(json.dumps(plan_dict, indent=2))
        print("=" * 80)
        print("  ✅ Plan JSON successfully generated and validated against Pydantic schema!")
        print("=" * 80 + "\n")


# =====================================================================
# Walkthrough Demo Runner (Scoring breakdown)
# =====================================================================

def run_group_demo(city: str):
    """Executes a 4-person taste-fairness simulation with mathematical breakdowns."""
    init_db()
    profiles = get_demo_profiles()

    print("\n" + "=" * 78)
    print("        COMMON GROUND — 4-PERSON TASTE-FAIR GROUP PLANNER")
    print("=" * 78)
    print(f"Destination:  {city.title()}")
    print(f"Qloo Mode:    {get_mode_banner()}")
    print(f"Audit Log:    {LOG_FILE_PATH}")
    print("-" * 78)

    print("\n👥 TRAVELER PROFILES:")
    for p in profiles:
        budget_str = f"Max: {p.constraints.budget}" if p.constraints.budget else "Any"
        diet_str = f"Diet: {', '.join(p.constraints.dietary)}" if p.constraints.dietary else "None"
        access_str = f"Access: {', '.join(p.constraints.accessibility)}" if p.constraints.accessibility else "Standard"
        print(f"  • {p.name:<7} | Tastes: {', '.join(p.favorites[:4])}")
        print(f"            | Constraints: [{budget_str} | {diet_str} | {access_str}]")

    print("\n" + "=" * 78)
    print(f"  PHASE A: FETCHING CANDIDATES FOR {city.upper()} & APPLYING HARD CONSTRAINTS")
    print("=" * 78)

    all_raw_candidates: List[Candidate] = []
    category_candidates: Dict[str, List[Candidate]] = {}

    try:
        for cat in CATEGORIES:
            pool = get_recommendations(
                signals=[fav for p in profiles for fav in p.favorites],
                category=cat,
                location=city
            )
            all_raw_candidates.extend(pool)
            category_candidates[cat] = pool
    except QlooError as e:
        print_qloo_error(e)
        sys.exit(1)

    kept_candidates, guardrail_records = apply_constraints(all_raw_candidates, profiles)

    print(f"Total candidates evaluated: {len(all_raw_candidates)}")
    print(f"Passed all group guardrails: {len(kept_candidates)}")
    print(f"Filtered out by guardrails:  {len(all_raw_candidates) - len(kept_candidates)}")

    print("\n" + "=" * 78)
    print("  PHASE B: CANDIDATE RANKINGS USING GROUP SCORE (0.6*mean + 0.4*min)")
    print("=" * 78)

    kept_ids = {c.id for c in kept_candidates}
    for cat in CATEGORIES:
        pool = [c for c in category_candidates[cat] if c.id in kept_ids] or category_candidates[cat][:2]
        scored_pool = []
        for cand in pool:
            p_scores = {p.name: score_candidate_for_profile(cand, p) for p in profiles}
            g_score = group_score(p_scores)
            scored_pool.append((cand, g_score, p_scores))

        scored_pool.sort(key=lambda x: x[1], reverse=True)

        print(f"\n--- {format_category_title(cat)} ---")
        for idx, (cand, g_score, p_scores) in enumerate(scored_pool[:2], 1):
            scores_str = " | ".join(f"{name}: {int(score*100)}%" for name, score in p_scores.items())
            print(f"  {idx}. [{int(g_score*100)}% Group Score] {cand.name} [{cand.price_level}]")
            print(f"     Location:   {cand.location}")
            print(f"     Individual: {scores_str}")
            print(f"     Tags:       {', '.join(cand.tags[:4])}")

    print("\n" + "=" * 78)
    print("  PHASE C: TASTE BRIDGES (Connecting the Most Dissimilar Pair)")
    print("=" * 78)

    bridge_data = find_bridges(profiles, kept_candidates)
    p1_name, p2_name = bridge_data["most_dissimilar_pair"]
    print(f"Most dissimilar travelers identified: {p1_name} & {p2_name}")
    print(f"Divergence score across candidates:    {bridge_data['divergence']:.2f}\n")

    print(f"Top venue bridges that satisfy BOTH {p1_name} and {p2_name}:")
    for b in bridge_data["bridges"][:2]:
        cand = b["candidate"]
        print(f"  🌉 [{int(b['bridge_score']*100)}% Harmonic Bridge] {cand.name} ({cand.category})")
        print(f"     Location: {cand.location}")
        print(f"     {p1_name}: {int(b['p1_score']*100)}% | {p2_name}: {int(b['p2_score']*100)}%")
        print(f"     Why it works: {b['explanation']}")

    print("\n" + "=" * 78)
    print("  PHASE D: SPOTLIGHT SELECTION (Guaranteed Highlight for Each Traveler)")
    print("=" * 78)

    spotlights = spotlight_selection(profiles, all_raw_candidates)
    for name, data in spotlights.items():
        cand = data["candidate"]
        print(f"  ⭐ {name:<7} Spotlight -> {cand.name} ({cand.category})")
        print(f"     Location: {cand.location}")
        print(f"     Match:    {int(data['personal_score']*100)}% personal affinity")
        print(f"     Reason:   {data['reason']}\n")


def run_single(city: str, favorites: List[str]):
    """Queries recommendations for each category and prints ranked results for a single profile."""
    init_db()

    print("\n" + "=" * 65)
    print("      COMMON GROUND — TASTE-FAIR TRIP PLANNER (QLOO)")
    print("=" * 65)
    print(f"Target City:       {city.title()}")
    print(f"Qloo Mode:         {get_mode_banner()}")
    print(f"Taste Signals:     {', '.join(favorites) if favorites else 'None provided'}")
    print("=" * 65 + "\n")

    # 1. Resolve and verify every favorite
    print("🔍 RESOLVING CULTURAL FAVORITES:")
    resolved_ids, resolved_entities, skipped = resolve_signal_entities(favorites)
    for fav in favorites:
        matched = next((r for r in resolved_entities if r.get("query", "").lower() == fav.lower().strip()), None)
        if matched:
            print(f"  • {fav:<22} -> RESOLVED: {matched['name']} [{matched['subtype']}] (ID: {matched['id']})")
        else:
            print(f"  • {fav:<22} -> NOT FOUND (SKIPPED)")

    if skipped:
        print(f"\n⚠️  Skipped unresolved favorites ({len(skipped)}): {', '.join(skipped)}")

    if favorites and not resolved_ids:
        print("\n❌ ERROR: None of the provided favorites could be resolved to known entities in Qloo.")
        print("Please verify artist/brand spelling or try other cultural references.")
        sys.exit(1)

    print()
    for cat in CATEGORIES:
        print(f"\n--- {format_category_title(cat)} ---")
        try:
            candidates = get_recommendations(signals=favorites, category=cat, location=city)
            if not candidates:
                print("   (No matching candidates found)")
                continue

            for idx, cand in enumerate(candidates, 1):
                pct = int(cand.qloo_affinity * 100)
                tags_str = ", ".join(cand.tags[:4]) if cand.tags else "general"
                price_str = f" [{cand.price_level}]" if cand.price_level else ""

                print(f"  {idx}. [{pct}% Match] {cand.name}{price_str}")
                print(f"     Location: {cand.location}")
                print(f"     Tags:     {tags_str}")
                if cand.description:
                    print(f"     Note:     {cand.description}")
                print()

        except QlooError as e:
            print_qloo_error(e)
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ UNEXPECTED ERROR retrieving {cat}: {e}")
            traceback.print_exc()
            sys.exit(1)

    print("=" * 65)
    print("  Done! Recommendations ranked by cultural affinity.")
    print("=" * 65 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Common Ground CLI: Autonomous multi-agent trip planner & Qloo recommendation engine."
    )
    parser.add_argument(
        "--agent",
        action="store_true",
        default=False,
        help="Run the complete autonomous agent pipeline and print the final Plan JSON."
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        default=False,
        help="Run 4-person taste fairness mathematical walkthrough."
    )
    parser.add_argument(
        "--single",
        action="store_true",
        help="Run single-person query instead of group planner."
    )
    parser.add_argument(
        "--city",
        type=str,
        default="Lisbon",
        help="Destination city (e.g. 'Delhi', 'Lisbon', 'Tokyo'). Default: Lisbon"
    )
    parser.add_argument(
        "--favorites",
        type=str,
        default=None,
        help="Comma-separated cultural favorites for single-person mode."
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Force offline mock mode even if QLOO_API_KEY is present."
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Force LIVE Qloo API mode (requires QLOO_API_KEY)."
    )

    args = parser.parse_args()

    # Handle explicit mode overrides
    if args.mock:
        os.environ["QLOO_MOCK"] = "true"
    elif args.live:
        os.environ["QLOO_MOCK"] = "false"

    if args.single or args.favorites is not None:
        fav_list = [f.strip() for f in (args.favorites or "specialty coffee, natural wine, contemporary art").split(",") if f.strip()]
        run_single(city=args.city, favorites=fav_list)
    elif args.demo:
        run_group_demo(city=args.city)
    else:
        # Default to full agent pipeline!
        run_agent_pipeline(city=args.city, dump_json=True)


if __name__ == "__main__":
    main()
