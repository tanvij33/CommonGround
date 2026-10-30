"""Taste-fairness and group recommendation scoring engine for Common Ground.

Contains pure, robust, and unit-tested algorithms for:
1. normalize_affinity: Maps Qloo scores to [0.0, 1.0].
2. group_score: Balances collective enjoyment and minority protection (0.6 * mean + 0.4 * min).
3. apply_constraints: Hard-filters candidates for budget, dietary, mobility, and alcohol-free guardrails.
4. TasteDebtTracker: Compensates underrepresented travelers across consecutive itinerary slots.
5. spotlight_selection: Guarantees every traveler has at least one highlight venue chosen primarily for them.
6. find_bridges: Finds the two most divergent travelers and ranks venues that connect them.
7. split_and_meet: Proposes parallel activities for divergent subgroups reconvening at a shared dinner.
8. fairness_summary: Produces overall plan happiness metrics and fairness evaluations.
"""

from typing import List, Dict, Any, Tuple, Optional, Union
import math

from backend.models import Candidate, Profile, ProfileConstraints
from backend.mock_data import calculate_mock_affinity


# Price level mapping to integer scale for comparison
PRICE_SCALE: Dict[str, int] = {
    "$": 1,
    "$$": 2,
    "$$$": 3,
    "$$$$": 4,
}


def score_candidate_for_profile(candidate: Candidate, profile: Profile) -> float:
    """Computes a normalized affinity score (0.0 to 1.0) for a candidate given a profile."""
    # If candidate already has a specific affinity assigned for this profile, use it
    # Otherwise calculate dynamically from taste signals
    signals = [
        f.get("name", "") if isinstance(f, dict) else str(f)
        for f in profile.favorites
    ]
    return calculate_mock_affinity(
        candidate_tags=candidate.tags,
        candidate_name=candidate.name,
        signals=signals
    )


# =====================================================================
# 1. Normalize Affinity
# =====================================================================
def normalize_affinity(score: Union[float, int, None, str]) -> float:
    """Maps any raw affinity score to a clean float strictly bounded within [0.0, 1.0].

    Handles:
    - Standard decimal fractions (e.g. 0.85 -> 0.85)
    - Percentage scales (e.g. 85.0 -> 0.85)
    - Negative or out-of-bounds numbers (clamped)
    - None or unparseable values (defaults to 0.0)
    """
    if score is None:
        return 0.0

    try:
        val = float(score)
    except (ValueError, TypeError):
        return 0.0

    if math.isnan(val) or math.isinf(val):
        return 0.0

    # If score is represented as a percentage > 1.0 (e.g. 75.0 or 100.0)
    if val > 1.0:
        val = val / 100.0

    # Clamp strictly to [0.0, 1.0]
    clamped = max(0.0, min(1.0, val))
    return round(clamped, 4)


# =====================================================================
# 2. Group Score & Affinity Rescaling
# =====================================================================
def group_score(scores: Union[List[float], Dict[str, float]]) -> float:
    """Calculates group score using the exact formula: 0.6 * mean + 0.4 * min.

    Protects against the tyranny of the majority by heavily penalizing
    options that leave any individual member miserable.

    Edge cases:
    - Empty list: returns 0.0.
    - Single person: 0.6 * s + 0.4 * s = 1.0 * s.
    - All identical: 0.6 * s + 0.4 * s = s.
    """
    if not scores:
        return 0.0

    if isinstance(scores, dict):
        score_list = list(scores.values())
    else:
        score_list = list(scores)

    if not score_list:
        return 0.0

    normalized = [normalize_affinity(s) for s in score_list]
    mean_val = sum(normalized) / len(normalized)
    min_val = min(normalized)

    res = (0.6 * mean_val) + (0.4 * min_val)
    return round(res, 4)


def compute_affinity_distribution(scores: List[float]) -> Dict[str, float]:
    """Calculates min, max, mean, and standard deviation for raw affinity scores."""
    if not scores:
        return {"min": 0.0, "max": 0.0, "mean": 0.0, "std": 0.0}
    n = len(scores)
    mean_val = sum(scores) / n
    var_val = sum((s - mean_val) ** 2 for s in scores) / n
    std_val = math.sqrt(var_val)
    return {
        "min": round(min(scores), 4),
        "max": round(max(scores), 4),
        "mean": round(mean_val, 4),
        "std": round(std_val, 4)
    }


def rescale_affinity_scores(
    raw_scores: Dict[str, float],
    target_min: float = 0.35,
    target_max: float = 0.95
) -> Dict[str, float]:
    """Rescales a traveler's affinity scores across candidate pool using min-max normalization.

    When the raw affinity spread is tiny, differences in taste signals become imperceptible.
    Rescaling maps the minimum raw score to target_min (0.35) and maximum to target_max (0.95)
    so cultural compromises and high-affinity matches are clearly visible.
    """
    if not raw_scores:
        return {}
    vals = list(raw_scores.values())
    s_min = min(vals)
    s_max = max(vals)
    spread = s_max - s_min
    if spread < 0.01:
        # Uniform distribution
        mid = round((target_min + target_max) / 2.0, 4)
        return {cid: mid for cid in raw_scores}

    rescaled = {}
    for cid, val in raw_scores.items():
        norm = (val - s_min) / spread
        r_val = target_min + norm * (target_max - target_min)
        rescaled[cid] = round(r_val, 4)
    return rescaled


# =====================================================================
# 3. Apply Constraints (Guardrail Filtering)
# =====================================================================
def apply_constraints(
    candidates: List[Candidate],
    profiles: List[Profile]
) -> Tuple[List[Candidate], Dict[str, Dict[str, Any]]]:
    """Filters candidates for dietary, budget, mobility, and alcohol-free guardrails.

    Runs BEFORE scoring.
    Only shows a guardrail as passed if it can be verified from Qloo data (tags or description);
    otherwise marks it 'unverified'.
    Does NOT show dietary checks on non-food venues (marked 'n/a').
    Stores alcohol-free as its own first-class constraint.

    Returns:
    - kept_candidates: List of Candidate objects that passed all active guardrails.
    - guardrail_records: Per-candidate audit dict for UI badge display:
      {candidate_id: {'passed': bool, 'budget': str, 'dietary': str, 'mobility': str, 'alcohol_free': str, 'reasons': List[str]}}
    """
    # 1. Determine group-wide strictest constraints
    max_budget_level = 4
    group_dietary_needs: List[str] = []
    group_accessibility_needs: List[str] = []
    alcohol_free_required = False

    for p in profiles:
        c = p.constraints
        if not c:
            continue

        # Budget constraint: group is constrained by the lowest budget member
        if c.budget and c.budget in PRICE_SCALE:
            level = PRICE_SCALE[c.budget]
            if level < max_budget_level:
                max_budget_level = level

        # Dietary restrictions (e.g. vegetarian, vegan, halal, gluten-free)
        if c.dietary:
            for d in c.dietary:
                d_clean = d.lower().strip()
                if d_clean and d_clean not in group_dietary_needs:
                    group_dietary_needs.append(d_clean)

        # Accessibility needs (e.g. step-free, wheelchair, elevator)
        if c.accessibility:
            for a in c.accessibility:
                a_clean = a.lower().strip()
                if a_clean and a_clean not in group_accessibility_needs:
                    group_accessibility_needs.append(a_clean)

        # Alcohol-free check (supports first-class alcohol_free field + dietary fallback for backwards compatibility)
        if (
            getattr(c, "alcohol_free", False) is True
            or "alcohol-free" in [d.lower() for d in (c.dietary or [])]
            or (getattr(c, "extra", {}) or {}).get("alcohol_free") is True
        ):
            alcohol_free_required = True

    kept: List[Candidate] = []
    records: Dict[str, Dict[str, Any]] = {}

    for cand in candidates:
        passed_budget_status = "passed"
        passed_dietary_status = "passed" if group_dietary_needs and cand.category in ("restaurant", "cafe", "bar") else "n/a"
        passed_mobility_status = "passed" if group_accessibility_needs else "n/a"
        passed_alcohol_free_status = "passed" if alcohol_free_required else "n/a"
        reasons: List[str] = []

        cand_tags_lower = [t.lower() for t in cand.tags]
        desc_lower = (cand.description or "").lower()
        name_lower = cand.name.lower()
        text_full = f"{name_lower} {desc_lower} {' '.join(cand_tags_lower)}"

        # 1. Check Budget
        cand_price_level = PRICE_SCALE.get(cand.price_level, 2)
        if cand.price_level is None:
            passed_budget = True
            passed_budget_status = "unverified"
        elif cand_price_level > max_budget_level:
            passed_budget = False
            passed_budget_status = "failed"
            reasons.append(f"Price level ({cand.price_level}) exceeds group budget limit")
        else:
            passed_budget = True
            passed_budget_status = "passed"

        # 2. Check Dietary (ONLY applies to food/drink venues; non-food venues get 'n/a')
        passed_dietary = True
        if group_dietary_needs:
            if cand.category in ("restaurant", "cafe", "bar"):
                for need in group_dietary_needs:
                    if need == "vegetarian":
                        has_veg_verified = (
                            cand.category == "cafe"
                            or any(t in cand_tags_lower for t in ("vegetarian", "vegan", "plant-based", "plant", "veg", "bakery", "cafe", "coffee", "pastry", "breakfast", "organic"))
                            or any(w in desc_lower for w in ("vegetarian", "vegan", "plant-based", "plant", "veg", "cafe", "coffee", "pastry", "bakery", "breakfast", "yoga", "organic", "thali"))
                            or any(w in name_lower for w in ("cafe", "coffee", "bakery", "pastry", "yoga", "buddha", "tea"))
                        )
                        if has_veg_verified:
                            passed_dietary_status = "passed"
                        else:
                            passed_dietary = False
                            passed_dietary_status = "unverified"
                            reasons.append("Vegetarian options unverified in Qloo metadata")
                    else:
                        has_dietary = any(
                            need in t or (need == "vegan" and "plant-based" in t)
                            for t in cand_tags_lower
                        ) or (
                            need in desc_lower
                        )
                        if has_dietary:
                            passed_dietary_status = "passed"
                        else:
                            passed_dietary = False
                            passed_dietary_status = "unverified"
                            reasons.append(f"Accommodation for {need} unverified in Qloo metadata")
            else:
                passed_dietary = True
                passed_dietary_status = "n/a"

        # 3. Check Mobility / Accessibility
        passed_mobility = True
        if group_accessibility_needs:
            has_barrier = any(
                b in t for b in ("stairs-only", "steep-climb", "inaccessible", "no-elevator", "uneven-cobblestones")
                for t in cand_tags_lower
            )
            if has_barrier:
                passed_mobility = False
                passed_mobility_status = "failed"
                reasons.append("Venue has steep stairs or mobility barriers")
            else:
                has_access = any(
                    a in t for a in ("wheelchair", "step-free", "elevator", "accessible")
                    for t in cand_tags_lower
                )
                passed_mobility = True
                passed_mobility_status = "passed" if has_access else "unverified"

        # 4. Check Alcohol-Free (Exclude bars/nightlife and flag alcohol-centric venues)
        passed_alcohol_free = True
        if alcohol_free_required:
            if cand.category == "bar":
                passed_alcohol_free = False
                passed_alcohol_free_status = "failed"
                reasons.append("Alcohol-centric bar/nightlife venue excluded for alcohol-free traveler")
            else:
                alcohol_centric = any(
                    m in t for m in ("wine bar", "pub", "cocktail bar", "nightclub", "brewery")
                    for t in cand_tags_lower
                )
                if alcohol_centric:
                    passed_alcohol_free = False
                    passed_alcohol_free_status = "failed"
                    reasons.append("Venue is alcohol-centric without non-alcoholic focus")
                else:
                    passed_alcohol_free = True
                    passed_alcohol_free_status = "passed"

        all_passed = (
            passed_budget
            and passed_dietary
            and passed_mobility
            and passed_alcohol_free
        )

        records[cand.id] = {
            "passed": all_passed,
            "budget": passed_budget,
            "budget_status": passed_budget_status,
            "dietary": passed_dietary,
            "dietary_status": passed_dietary_status,
            "mobility": passed_mobility,
            "mobility_status": passed_mobility_status,
            "alcohol_free": passed_alcohol_free,
            "alcohol_free_status": passed_alcohol_free_status,
            "reasons": reasons
        }

        if all_passed:
            kept.append(cand)

    return kept, records


# =====================================================================
# 4. Taste Debt Tracker
# =====================================================================
class TasteDebtTracker:
    """Tracks cumulative satisfaction across itinerary slots to prevent taste starvation.

    When someone's preferences were compromised in slot N-1, their taste debt increases,
    giving candidates that favor them a mathematical boost in slot N.
    """

    def __init__(self, profiles: List[Profile]):
        self.profiles = profiles
        # Cumulative satisfaction points
        self.cumulative_satisfaction: Dict[str, float] = {p.name: 0.0 for p in profiles}
        self.slots_count: int = 0
        self.history: List[Dict[str, Any]] = []

    def get_underrepresented(self) -> Tuple[Optional[str], float]:
        """Returns the member who is furthest behind the group average satisfaction."""
        if not self.profiles or self.slots_count == 0:
            return None, 0.0

        avg_sat = sum(self.cumulative_satisfaction.values()) / len(self.cumulative_satisfaction)
        # Find person with lowest cumulative satisfaction
        lowest_person = min(self.cumulative_satisfaction, key=self.cumulative_satisfaction.get)
        deficit = max(0.0, avg_sat - self.cumulative_satisfaction[lowest_person])
        return lowest_person, round(deficit, 4)

    def calculate_boosted_score(
        self,
        candidate: Candidate,
        per_person_scores: Dict[str, float]
    ) -> Tuple[float, str]:
        """Calculates group score with a dynamic taste-debt boost for travelers who are behind.

        Returns:
            boosted_score: Adjusted score (0.0 to 1.0)
            explanation: One-line editorial note explaining why this pick was favored.
        """
        base_score = group_score(per_person_scores)
        underrepresented, deficit = self.get_underrepresented()

        if not underrepresented or deficit < 0.02:
            # Everyone is balanced
            return base_score, f"Equally balanced across group (base score: {base_score:.2f})."

        # Boost the candidate if it brings high joy to the person furthest behind
        person_score = per_person_scores.get(underrepresented, 0.5)
        # Boost up to +0.25 depending on deficit and candidate fit for that person
        boost = deficit * (person_score - 0.5) * 0.4
        boosted = max(0.0, min(1.0, base_score + boost))

        explanation = (
            f"Boosted for {underrepresented} (satisfaction was -{deficit:.2f} behind average); "
            f"scores {person_score:.2f} for them."
        )
        return round(boosted, 4), explanation

    def record_pick(
        self,
        candidate: Candidate,
        per_person_scores: Dict[str, float],
        time_slot: str = "slot"
    ) -> Dict[str, Any]:
        """Records an itinerary pick, updating cumulative satisfaction and logging 'why not me' notes."""
        self.slots_count += 1
        for name, score in per_person_scores.items():
            self.cumulative_satisfaction[name] = round(
                self.cumulative_satisfaction.get(name, 0.0) + score, 4
            )

        # Generate 'why not me' one-line explanations for each person
        sorted_members = sorted(per_person_scores.items(), key=lambda x: x[1], reverse=True)
        top_person, top_score = sorted_members[0]
        
        explanations: Dict[str, str] = {}
        for name, score in per_person_scores.items():
            if name == top_person:
                explanations[name] = f"Primary taste match: directly reflects your favorites ({score:.2f})."
            elif score >= 0.70:
                explanations[name] = f"High cross-affinity: aligns with your preferences ({score:.2f})."
            else:
                explanations[name] = (
                    f"Selected to satisfy {top_person} ({top_score:.2f}); "
                    f"your taste debt has been credited for upcoming stops."
                )

        record = {
            "slot": time_slot,
            "candidate_id": candidate.id,
            "candidate_name": candidate.name,
            "scores": per_person_scores,
            "cumulative": dict(self.cumulative_satisfaction),
            "explanations": explanations
        }
        self.history.append(record)
        return record


# =====================================================================
# 5. Spotlight Selection
# =====================================================================
def spotlight_selection(
    profiles: List[Profile],
    candidate_pool: List[Candidate]
) -> Dict[str, Dict[str, Any]]:
    """Guarantees every traveler has at least one highlight venue chosen primarily for them.

    Returns mapping:
    {
      "Alice": {
        "candidate": Candidate,
        "personal_score": float,
        "reason": str
      }
    }
    """
    if not profiles or not candidate_pool:
        return {}

    spotlights: Dict[str, Dict[str, Any]] = {}
    assigned_cand_ids = set()

    for p in profiles:
        best_cand: Optional[Candidate] = None
        best_score = -1.0

        for cand in candidate_pool:
            if cand.id in assigned_cand_ids:
                continue

            score = score_candidate_for_profile(cand, p)
            if score > best_score:
                best_score = score
                best_cand = cand

        # Fallback if all candidates were already assigned once
        if not best_cand and candidate_pool:
            best_cand = max(candidate_pool, key=lambda c: score_candidate_for_profile(c, p))
            best_score = score_candidate_for_profile(best_cand, p)

        if best_cand:
            assigned_cand_ids.add(best_cand.id)
            fav_names = [f.get("name", "") if isinstance(f, dict) else str(f) for f in p.favorites]
            matching_tags = [t for t in best_cand.tags if any(fav.lower() in t.lower() for fav in fav_names)]
            tag_hint = f" ({', '.join(matching_tags)})" if matching_tags else ""
            
            spotlights[p.name] = {
                "candidate": best_cand,
                "personal_score": round(best_score, 4),
                "reason": f"Dedicated spotlight for {p.name} matching top taste signals{tag_hint}."
            }

    return spotlights


# =====================================================================
# 6. Find Bridges
# =====================================================================
def find_bridges(
    profiles: List[Profile],
    candidate_pool: List[Candidate]
) -> Dict[str, Any]:
    """Identifies the two most dissimilar people in the group, then finds candidates

    that score well for both (ranked by the lower score of the two).
    Attaches a short editorial explanation of the shared connection.
    """
    if len(profiles) < 2:
        # Edge case: 1 person
        name = profiles[0].name if profiles else "Solo"
        top_cand = candidate_pool[0] if candidate_pool else None
        return {
            "most_dissimilar_pair": (name, name),
            "divergence": 0.0,
            "bridges": [{"candidate": top_cand, "bridge_score": 1.0, "p1_score": 1.0, "p2_score": 1.0, "explanation": "Solo traveler alignment"}] if top_cand else []
        }

    # 1. Identify the two most divergent profiles based on score variance across candidate pool
    max_divergence = -1.0
    divergent_pair: Tuple[Profile, Profile] = (profiles[0], profiles[1])

    for i in range(len(profiles)):
        for j in range(i + 1, len(profiles)):
            p1, p2 = profiles[i], profiles[j]
            # Calculate sum of squared differences across candidate pool
            div = 0.0
            for cand in candidate_pool:
                s1 = score_candidate_for_profile(cand, p1)
                s2 = score_candidate_for_profile(cand, p2)
                div += (s1 - s2) ** 2

            if div > max_divergence:
                max_divergence = div
                divergent_pair = (p1, p2)

    p1, p2 = divergent_pair

    # 2. Score candidates for both and rank by min(s1, s2)
    bridge_results = []
    for cand in candidate_pool:
        s1 = score_candidate_for_profile(cand, p1)
        s2 = score_candidate_for_profile(cand, p2)
        # Bridge score prioritizes the lower score so neither person is compromised
        bridge_score = min(s1, s2)

        # Editorial connection explanation
        all_fav_names = [f.get("name", "") if isinstance(f, dict) else str(f) for f in p1.favorites + p2.favorites]
        shared_themes = [t for t in cand.tags if any(fav.lower() in t.lower() for fav in all_fav_names)]
        theme_str = f"highlighting shared affinity for {', '.join(shared_themes[:2])}" if shared_themes else "balancing architectural ambiance and culinary craft"

        explanation = (
            f"Bridges {p1.name} ({s1:.2f}) & {p2.name} ({s2:.2f}) {theme_str}."
        )

        bridge_results.append({
            "candidate": cand,
            "bridge_score": round(bridge_score, 4),
            "p1_score": round(s1, 4),
            "p2_score": round(s2, 4),
            "explanation": explanation
        })

    # Rank descending by bridge score
    bridge_results.sort(key=lambda x: x["bridge_score"], reverse=True)

    return {
        "most_dissimilar_pair": (p1.name, p2.name),
        "divergence": round(max_divergence, 4),
        "bridges": bridge_results
    }


# =====================================================================
# 7. Split and Meet
# =====================================================================
def split_and_meet(
    profiles: List[Profile],
    candidate_pool: List[Candidate],
    dinner_candidates: Optional[List[Candidate]] = None
) -> Dict[str, Any]:
    """Proposes two parallel nearby activities for divergent subgroups, reconvening at a shared dinner."""
    if len(profiles) < 2 or len(candidate_pool) < 2:
        cand = candidate_pool[0] if candidate_pool else None
        return {
            "subgroup_a": {"members": [p.name for p in profiles], "activity": cand, "score": 1.0},
            "subgroup_b": {"members": [], "activity": None, "score": 0.0},
            "shared_dinner": cand,
            "dinner_score": 1.0,
            "explanation": "Group remains together."
        }

    # 1. Split profiles into 2 subgroups based on greatest taste contrast
    p1, p2 = profiles[0], profiles[1]
    subgroup_a_profiles = [p1]
    subgroup_b_profiles = [p2]

    # Assign remaining profiles to whichever subgroup anchor they are closer to
    for p in profiles[2:]:
        dist_to_p1 = sum(abs(score_candidate_for_profile(c, p) - score_candidate_for_profile(c, p1)) for c in candidate_pool[:5])
        dist_to_p2 = sum(abs(score_candidate_for_profile(c, p) - score_candidate_for_profile(c, p2)) for c in candidate_pool[:5])
        if dist_to_p1 <= dist_to_p2:
            subgroup_a_profiles.append(p)
        else:
            subgroup_b_profiles.append(p)

    # 2. Pick top activity for subgroup A
    best_cand_a = max(
        candidate_pool,
        key=lambda c: group_score([score_candidate_for_profile(c, p) for p in subgroup_a_profiles])
    )
    score_a = group_score([score_candidate_for_profile(best_cand_a, p) for p in subgroup_a_profiles])

    # 3. Pick top activity for subgroup B (excluding candidate A)
    pool_b = [c for c in candidate_pool if c.id != best_cand_a.id]
    best_cand_b = max(
        pool_b if pool_b else candidate_pool,
        key=lambda c: group_score([score_candidate_for_profile(c, p) for p in subgroup_b_profiles])
    )
    score_b = group_score([score_candidate_for_profile(best_cand_b, p) for p in subgroup_b_profiles])

    # 4. Shared dinner selection that maximizes harmony across ALL profiles
    dinner_pool = dinner_candidates or [c for c in candidate_pool if c.category in ("restaurant", "bar")] or candidate_pool
    shared_dinner = max(
        dinner_pool,
        key=lambda c: group_score([score_candidate_for_profile(c, p) for p in profiles])
    )
    dinner_score = group_score([score_candidate_for_profile(shared_dinner, p) for p in profiles])

    names_a = [p.name for p in subgroup_a_profiles]
    names_b = [p.name for p in subgroup_b_profiles]

    explanation = (
        f"Split afternoon: {', '.join(names_a)} visit {best_cand_a.name} while "
        f"{', '.join(names_b)} explore {best_cand_b.name}; "
        f"reconvening together at {shared_dinner.name} ({dinner_score:.2f} group fit)."
    )

    return {
        "subgroup_a": {
            "members": names_a,
            "activity": best_cand_a,
            "score": score_a
        },
        "subgroup_b": {
            "members": names_b,
            "activity": best_cand_b,
            "score": score_b
        },
        "shared_dinner": shared_dinner,
        "dinner_score": dinner_score,
        "explanation": explanation
    }


# =====================================================================
# 8. Fairness Summary
# =====================================================================
def fairness_summary(
    profiles: List[Profile],
    selected_candidates: List[Candidate]
) -> Dict[str, Any]:
    """Calculates overall per-person happiness across the full itinerary plan."""
    if not profiles or not selected_candidates:
        return {
            "per_person": {},
            "mean_happiness": 0.0,
            "min_happiness": 0.0,
            "max_happiness": 0.0,
            "happiness_spread": 0.0,
            "fairness_score": 0.0,
            "is_balanced": True,
            "verdict": "No stops or profiles to evaluate."
        }

    per_person_totals: Dict[str, float] = {p.name: 0.0 for p in profiles}

    for cand in selected_candidates:
        for p in profiles:
            s = score_candidate_for_profile(cand, p)
            per_person_totals[p.name] += s

    num_stops = len(selected_candidates)
    per_person_avg: Dict[str, float] = {
        name: round(total / num_stops, 4)
        for name, total in per_person_totals.items()
    }

    scores = list(per_person_avg.values())
    mean_val = sum(scores) / len(scores)
    min_val = min(scores)
    max_val = max(scores)
    spread = max_val - min_val

    # Fairness score rewards high minimum satisfaction and low spread
    # Fairness = 0.5 * mean + 0.3 * min + 0.2 * (1.0 - spread)
    fairness = (0.5 * mean_val) + (0.3 * min_val) + (0.2 * max(0.0, 1.0 - spread))
    fairness = round(max(0.0, min(1.0, fairness)), 4)

    is_balanced = spread <= 0.20

    if is_balanced:
        verdict = f"Fair and balanced: All travelers are within {spread*100:.1f}% satisfaction variance."
    else:
        under = min(per_person_avg, key=per_person_avg.get)
        verdict = f"Moderate variance ({spread*100:.1f}% spread): {under} had slightly fewer high-affinity picks."

    return {
        "per_person": per_person_avg,
        "mean_happiness": round(mean_val, 4),
        "min_happiness": round(min_val, 4),
        "max_happiness": round(max_val, 4),
        "happiness_spread": round(spread, 4),
        "fairness_score": fairness,
        "is_balanced": is_balanced,
        "verdict": verdict
    }

