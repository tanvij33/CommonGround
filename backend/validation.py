"""Itinerary grounding validation layer for Common Ground.

Ensures that every venue proposed in an itinerary strictly originates
from the verified Qloo candidate set, rejecting hallucinations, retrying
with constructive feedback, and failing safely by substituting the best
verified candidate if needed.
"""

from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from backend.models import Candidate, PlanStop


class ValidationResult(BaseModel):
    """Encapsulates the audit result of an itinerary grounding check."""
    is_valid: bool = Field(description="True if all venues are grounded in Qloo candidates")
    violations: List[str] = Field(default_factory=list, description="List of ungrounded or invalid venue errors")
    verified_stops: List[Dict[str, Any]] = Field(default_factory=list, description="Ground-truthed stops")
    replacements_made: List[Dict[str, str]] = Field(default_factory=list, description="Substitutions made to fail safely")
    feedback_prompt: Optional[str] = Field(default=None, description="Constructive prompt for LLM retry")


class ProgrammaticAuditResult(BaseModel):
    """Detailed programmatic audit of itinerary rules."""
    all_passed: bool
    spotlight_passed: bool
    spotlights_found: Dict[str, bool]
    category_validity_passed: bool
    invalid_category_venues: List[str]
    slot_type_match_passed: bool
    slot_type_mismatches: List[str]
    fairness_spread: float
    fairness_passed: bool
    unverified_guardrails_count: int
    errors: List[str]


def audit_itinerary_rules(
    stops: List[Dict[str, Any]],
    profiles: List[Any],
    max_fairness_spread: float = 0.30
) -> ProgrammaticAuditResult:
    """Programmatically audits spotlight coverage, category validity, slot-type matches, and fairness spread."""
    errors: List[str] = []

    # 1. Spotlight Coverage
    spotlights_found = {p.name: False for p in profiles}
    for s in stops:
        sp = s.get("spotlight")
        if sp in spotlights_found:
            spotlights_found[sp] = True

    missing_spotlights = [name for name, found in spotlights_found.items() if not found]
    spotlight_passed = len(missing_spotlights) == 0
    if not spotlight_passed:
        errors.append(f"Spotlight coverage failed: Missing spotlights for {', '.join(missing_spotlights)}")

    # 2. Category Validity (every venue must be one of the 6 standard categories, 0 invalid)
    VALID_CATEGORIES = {"hotel", "restaurant", "cafe", "bar", "attraction", "shop"}
    invalid_category_venues = []
    for s in stops:
        cand = s.get("candidate")
        cat = getattr(cand, "category", None) or s.get("type") or ""
        if cat.lower() not in VALID_CATEGORIES:
            cand_name = getattr(cand, "name", "Unknown")
            invalid_category_venues.append(f"{cand_name} (Category: '{cat}')")
            errors.append(f"Invalid category venue: {cand_name} has invalid category '{cat}'")

    category_validity_passed = len(invalid_category_venues) == 0

    # 3. Slot-Type Match
    slot_type_mismatches = []
    for s in stops:
        label = s.get("label") or s.get("slot_label") or s.get("time_slot") or s.get("slot") or s.get("time") or ""
        label_lower = str(label).lower()
        cand = s.get("candidate")
        cat = (getattr(cand, "category", None) or s.get("type") or "").lower()
        cand_name = getattr(cand, "name", "Unknown")

        # Lunch and dinner must be restaurants
        if "lunch" in label_lower or "dinner" in label_lower:
            if cat != "restaurant":
                mismatch = f"Slot '{label}': {cand_name} is '{cat}', expected 'restaurant'"
                slot_type_mismatches.append(mismatch)
                errors.append(mismatch)
        # Cafe slots
        elif "cafe" in label_lower or "coffee" in label_lower or "breakfast" in label_lower:
            if cat != "cafe":
                mismatch = f"Slot '{label}': {cand_name} is '{cat}', expected 'cafe'"
                slot_type_mismatches.append(mismatch)
                errors.append(mismatch)

    slot_type_match_passed = len(slot_type_mismatches) == 0

    # 4. Fairness Spread
    per_person_totals: Dict[str, float] = {p.name: 0.0 for p in profiles}
    num_stops = max(len(stops), 1)
    for s in stops:
        scores = s.get("per_person") or s.get("taste_scores") or {}
        for p in profiles:
            per_person_totals[p.name] += scores.get(p.name, 0.5)

    per_person_avg = {k: v / num_stops for k, v in per_person_totals.items()}
    if per_person_avg:
        spread = max(per_person_avg.values()) - min(per_person_avg.values())
    else:
        spread = 0.0

    fairness_passed = spread <= max_fairness_spread
    if not fairness_passed:
        errors.append(f"Fairness spread too high: {spread*100:.1f}% exceeds maximum {max_fairness_spread*100:.1f}%")

    # 5. Count unverified guardrails
    unverified_count = 0
    for s in stops:
        gr = s.get("guardrails") or {}
        for k, v in gr.items():
            if str(v).lower() == "unverified":
                unverified_count += 1

    all_passed = (
        spotlight_passed
        and category_validity_passed
        and slot_type_match_passed
        and fairness_passed
    )

    return ProgrammaticAuditResult(
        all_passed=all_passed,
        spotlight_passed=spotlight_passed,
        spotlights_found=spotlights_found,
        category_validity_passed=category_validity_passed,
        invalid_category_venues=invalid_category_venues,
        slot_type_match_passed=slot_type_match_passed,
        slot_type_mismatches=slot_type_mismatches,
        fairness_spread=round(spread, 4),
        fairness_passed=fairness_passed,
        unverified_guardrails_count=unverified_count,
        errors=errors
    )


def _normalize_name(name: str) -> str:
    """Normalizes venue names for robust fuzzy matching."""
    return "".join(c.lower() for c in name if c.isalnum())


def validate_itinerary_grounding(
    proposed_stops: List[Dict[str, Any]],
    candidate_pool: List[Candidate],
    fail_safely: bool = True
) -> ValidationResult:
    """Audits proposed itinerary stops against the verified Qloo candidate pool.

    Args:
        proposed_stops: List of raw stop dictionaries proposed by the agent or LLM.
        candidate_pool: The verified list of Candidates returned by Qloo.
        fail_safely: If True, automatically replaces ungrounded venues with the
                     highest-scoring verified candidate in that category.

    Returns:
        ValidationResult detailing validity, violations, and verified stops.
    """
    # 1. Build lookup tables for verified candidates
    id_map: Dict[str, Candidate] = {c.id: c for c in candidate_pool}
    name_map: Dict[str, Candidate] = {_normalize_name(c.name): c for c in candidate_pool}
    category_pools: Dict[str, List[Candidate]] = {}
    for c in candidate_pool:
        category_pools.setdefault(c.category.lower(), []).append(c)

    violations: List[str] = []
    verified_stops: List[Dict[str, Any]] = []
    replacements: List[Dict[str, str]] = []

    for idx, stop in enumerate(proposed_stops):
        time_slot = stop.get("time_slot") or stop.get("slot") or f"Stop {idx+1}"
        slot_category = stop.get("category", "").lower()
        cand_data = stop.get("candidate") or stop.get("venue") or {}

        # If cand_data is already a Candidate instance
        if isinstance(cand_data, Candidate):
            cand_id = cand_data.id
            cand_name = cand_data.name
        elif isinstance(cand_data, dict):
            cand_id = cand_data.get("id") or stop.get("candidate_id") or ""
            cand_name = cand_data.get("name") or stop.get("candidate_name") or "Unknown"
        else:
            cand_id = ""
            cand_name = str(cand_data)

        # Check by ID
        matched_candidate: Optional[Candidate] = id_map.get(cand_id)

        # Check by normalized name
        if not matched_candidate and cand_name:
            matched_candidate = name_map.get(_normalize_name(cand_name))

        if matched_candidate:
            # Verified grounded stop
            stop_copy = dict(stop)
            stop_copy["candidate"] = matched_candidate
            stop_copy["guardrail_status"] = "passed"
            verified_stops.append(stop_copy)
        else:
            # Ungrounded venue detected!
            err = f"Slot '{time_slot}': Venue '{cand_name}' (ID: '{cand_id}') is NOT in the Qloo candidate set."
            violations.append(err)

            if fail_safely:
                # Infer appropriate category
                cat_target = slot_category
                if not cat_target:
                    time_lower = time_slot.lower()
                    if "cafe" in time_lower or "breakfast" in time_lower or "snack" in time_lower:
                        cat_target = "cafe"
                    elif "dinner" in time_lower or "lunch" in time_lower:
                        cat_target = "restaurant"
                    elif "night" in time_lower or "bar" in time_lower:
                        cat_target = "bar"
                    elif "culture" in time_lower or "activity" in time_lower:
                        cat_target = "attraction"
                    elif "shop" in time_lower or "afternoon" in time_lower:
                        cat_target = "shop"
                    else:
                        cat_target = "attraction"

                candidates_for_cat = category_pools.get(cat_target, candidate_pool)
                # Pick the highest-scoring candidate available
                fallback_candidate = max(candidates_for_cat, key=lambda c: c.qloo_affinity) if candidates_for_cat else candidate_pool[0]

                replacements.append({
                    "slot": time_slot,
                    "rejected_venue": cand_name,
                    "substituted_venue": fallback_candidate.name,
                    "reason": f"Ungrounded venue safely substituted with top verified {cat_target}."
                })

                stop_copy = dict(stop)
                stop_copy["candidate"] = fallback_candidate
                stop_copy["guardrail_status"] = "warning"
                stop_copy["notes"] = f"(Substituted verified venue: {fallback_candidate.name})"
                verified_stops.append(stop_copy)

    is_valid = len(violations) == 0

    # Build constructive feedback prompt in case caller wants to retry with the LLM
    feedback_prompt = None
    if not is_valid:
        verified_names = [f"'{c.name}' (ID: {c.id}, {c.category})" for c in candidate_pool]
        feedback_prompt = (
            "⚠️ GROUNDING VALIDATION FAILED:\n"
            + "\n".join(f"- {v}" for v in violations)
            + "\n\nYou MUST ONLY choose venues from this verified candidate pool:\n"
            + "\n".join(verified_names[:12])
            + "\n\nPlease correct the itinerary so every stop uses a verified candidate."
        )

    return ValidationResult(
        is_valid=is_valid,
        violations=violations,
        verified_stops=verified_stops,
        replacements_made=replacements,
        feedback_prompt=feedback_prompt
    )

