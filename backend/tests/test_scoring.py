"""Unit tests for backend/scoring.py.

Covers all 8 scoring and fairness functions, including the required edge cases:
- One person (solo traveler)
- Identical tastes across group
- Opposite / divergent tastes
- A constraint that removes every candidate
"""

import pytest

from backend.models import Candidate, Profile, ProfileConstraints
from backend.scoring import (
    normalize_affinity,
    group_score,
    apply_constraints,
    TasteDebtTracker,
    spotlight_selection,
    find_bridges,
    split_and_meet,
    fairness_summary,
    score_candidate_for_profile
)


# Helper fixtures for candidates and profiles
@pytest.fixture
def sample_candidates():
    return [
        Candidate(
            id="c1",
            name="Specialty Coffee Roastery",
            category="cafe",
            location="Lisbon",
            price_level="$",
            tags=["specialty-coffee", "pour-over", "minimalist"]
        ),
        Candidate(
            id="c2",
            name="Natural Wine Bar",
            category="bar",
            location="Lisbon",
            price_level="$$",
            tags=["natural-wine", "biodynamic", "intimate"]
        ),
        Candidate(
            id="c3",
            name="Luxury Steakhouse",
            category="restaurant",
            location="Lisbon",
            price_level="$$$$",
            tags=["steak", "traditional", "fine-dining", "meat-lover"]
        ),
        Candidate(
            id="c4",
            name="Modern Art Museum",
            category="attraction",
            location="Lisbon",
            price_level="$$",
            tags=["contemporary-art", "architecture", "step-free", "accessible"]
        ),
        Candidate(
            id="c5",
            name="Historic Tower Walkup",
            category="attraction",
            location="Lisbon",
            price_level="$",
            tags=["panoramic-views", "stairs-only", "historic"]
        ),
    ]


# ---------------------------------------------------------------------
# 1. Tests for normalize_affinity()
# ---------------------------------------------------------------------
def test_normalize_affinity_standard():
    assert normalize_affinity(0.85) == 0.85
    assert normalize_affinity(0.0) == 0.0
    assert normalize_affinity(1.0) == 1.0


def test_normalize_affinity_percentage():
    # Percentages > 1.0 get divided by 100
    assert normalize_affinity(85.0) == 0.85
    assert normalize_affinity(100.0) == 1.0
    assert normalize_affinity(42) == 0.42


def test_normalize_affinity_edge_cases():
    # Negative values clamped to 0.0
    assert normalize_affinity(-0.5) == 0.0
    # Excessive values clamped to 1.0
    assert normalize_affinity(150.0) == 1.0
    # None or unparseable
    assert normalize_affinity(None) == 0.0
    assert normalize_affinity("invalid") == 0.0


# ---------------------------------------------------------------------
# 2. Tests for group_score() (0.6 * mean + 0.4 * min)
# ---------------------------------------------------------------------
def test_group_score_formula():
    # mean = (1.0 + 0.5) / 2 = 0.75, min = 0.5
    # 0.6 * 0.75 + 0.4 * 0.5 = 0.45 + 0.20 = 0.65
    assert group_score([1.0, 0.5]) == 0.65


def test_group_score_exact_formula():
    """Asserts group_score matches 0.6*mean + 0.4*min precisely across 4 people and dict inputs."""
    # 4 people vector
    scores = [0.80, 0.60, 0.90, 0.50]
    # mean = 2.80 / 4 = 0.70, min = 0.50
    # 0.6 * 0.70 + 0.4 * 0.50 = 0.42 + 0.20 = 0.62
    assert group_score(scores) == 0.62

    # Dict input
    dict_scores = {"Aisha": 0.85, "Rohan": 0.75, "Meera": 0.65}
    # mean = 2.25 / 3 = 0.75, min = 0.65
    # 0.6 * 0.75 + 0.4 * 0.65 = 0.45 + 0.26 = 0.71
    assert group_score(dict_scores) == 0.71


def test_rescale_affinity_scores():
    from backend.scoring import rescale_affinity_scores
    raw = {"c1": 0.52, "c2": 0.54, "c3": 0.58}
    rescaled = rescale_affinity_scores(raw, target_min=0.35, target_max=0.95)
    assert rescaled["c1"] == 0.35
    assert rescaled["c3"] == 0.95
    assert 0.35 < rescaled["c2"] < 0.95


def test_group_score_empty():
    assert group_score([]) == 0.0


def test_group_score_edge_case_one_person():
    # 1 person: 0.6 * s + 0.4 * s = 1.0 * s
    assert group_score([0.8]) == 0.8


def test_group_score_edge_case_identical_tastes():
    # All scores equal 0.75
    # mean = 0.75, min = 0.75 -> 0.75
    assert group_score([0.75, 0.75, 0.75]) == 0.75


def test_group_score_edge_case_opposite_tastes():
    # One loves it (0.95), one hates it (0.15)
    # mean = 0.55, min = 0.15
    # 0.6 * 0.55 + 0.4 * 0.15 = 0.33 + 0.06 = 0.39
    assert group_score([0.95, 0.15]) == 0.39


# ---------------------------------------------------------------------
# 3. Tests for apply_constraints()
# ---------------------------------------------------------------------
def test_apply_constraints_budget_filter(sample_candidates):
    # Profile with strict $ budget
    profile_budget = Profile(
        name="Budget Traveler",
        constraints=ProfileConstraints(budget="$")
    )
    kept, records = apply_constraints(sample_candidates, [profile_budget])

    # Only $ venues kept: c1 ($) and c5 ($)
    kept_ids = [c.id for c in kept]
    assert "c1" in kept_ids
    assert "c5" in kept_ids
    assert "c2" not in kept_ids # $$
    assert "c3" not in kept_ids # $$$$
    assert records["c3"]["budget"] is False
    assert records["c1"]["budget"] is True


def test_apply_constraints_mobility_filter(sample_candidates):
    # Profile with mobility need
    profile_mobility = Profile(
        name="Accessibility Traveler",
        constraints=ProfileConstraints(accessibility=["step-free"])
    )
    kept, records = apply_constraints(sample_candidates, [profile_mobility])

    # c5 has 'stairs-only', so it must be filtered out
    kept_ids = [c.id for c in kept]
    assert "c5" not in kept_ids
    assert records["c5"]["mobility"] is False
    assert records["c4"]["mobility"] is True


def test_apply_constraints_alcohol_free(sample_candidates):
    profile_sober = Profile(
        name="Alcohol Free Traveler",
        constraints=ProfileConstraints(dietary=["alcohol-free"])
    )
    kept, records = apply_constraints(sample_candidates, [profile_sober])

    # c2 is a bar with natural wine, must be filtered out
    kept_ids = [c.id for c in kept]
    assert "c2" not in kept_ids
    assert records["c2"]["alcohol_free"] is False


def test_edge_case_constraint_removes_every_candidate(sample_candidates):
    """EDGE CASE: An impossible combination of constraints filters out every candidate."""
    impossible_profile = Profile(
        name="Super Constrained",
        constraints=ProfileConstraints(
            budget="$",
            dietary=["strict-kosher-macrobiotic-gluten-free"],
            accessibility=["no-elevation-changes"]
        )
    )
    # Ensure food places fail dietary, and stairs-only fails accessibility
    # Force a dietary filter on food places:
    food_only_candidates = [c for c in sample_candidates if c.category in ("restaurant", "cafe", "bar")]
    kept, records = apply_constraints(food_only_candidates, [impossible_profile])

    assert len(kept) == 0
    # Verify that records still return diagnostic failure reasons for every candidate
    for cand in food_only_candidates:
        assert records[cand.id]["passed"] is False
        assert len(records[cand.id]["reasons"]) > 0


# ---------------------------------------------------------------------
# 4. Tests for TasteDebtTracker
# ---------------------------------------------------------------------
def test_taste_debt_tracker_boosts_underrepresented(sample_candidates):
    p_alice = Profile(name="Alice", favorites=["specialty coffee"])
    p_bob = Profile(name="Bob", favorites=["contemporary art"])

    tracker = TasteDebtTracker([p_alice, p_bob])

    # Slot 1: Alice gets a huge score (0.90), Bob gets low score (0.40)
    tracker.record_pick(sample_candidates[0], {"Alice": 0.90, "Bob": 0.40}, "morning")

    underrepresented, deficit = tracker.get_underrepresented()
    assert underrepresented == "Bob"
    assert deficit > 0.20

    # Next candidate: Bob scores 0.85, Alice scores 0.50
    boosted_score, explanation = tracker.calculate_boosted_score(
        sample_candidates[3],
        {"Alice": 0.50, "Bob": 0.85}
    )
    assert "Boosted for Bob" in explanation
    assert boosted_score > group_score([0.50, 0.85])

    # Verify 'why not me' explanation in recorded pick
    record = tracker.record_pick(sample_candidates[3], {"Alice": 0.50, "Bob": 0.85}, "afternoon")
    assert "Primary taste match" in record["explanations"]["Bob"]
    assert "taste debt has been credited" in record["explanations"]["Alice"]


# ---------------------------------------------------------------------
# 5. Tests for spotlight_selection()
# ---------------------------------------------------------------------
def test_spotlight_selection_guarantees_each_member(sample_candidates):
    p_coffee = Profile(name="Coffee Lover", favorites=["specialty coffee", "pour-over"])
    p_art = Profile(name="Art Lover", favorites=["contemporary art", "architecture"])

    spotlights = spotlight_selection([p_coffee, p_art], sample_candidates)

    assert "Coffee Lover" in spotlights
    assert "Art Lover" in spotlights

    # Coffee Lover should have cafe c1
    assert spotlights["Coffee Lover"]["candidate"].id == "c1"
    # Art Lover should have museum c4
    assert spotlights["Art Lover"]["candidate"].id == "c4"


def test_spotlight_selection_edge_case_one_person(sample_candidates):
    p_solo = Profile(name="Solo Traveler", favorites=["specialty coffee"])
    spotlights = spotlight_selection([p_solo], sample_candidates)

    assert "Solo Traveler" in spotlights
    assert spotlights["Solo Traveler"]["candidate"].id == "c1"


# ---------------------------------------------------------------------
# 6. Tests for find_bridges()
# ---------------------------------------------------------------------
def test_find_bridges_opposite_tastes(sample_candidates):
    p_coffee_only = Profile(name="Barista", favorites=["specialty coffee", "pour-over"])
    p_art_only = Profile(name="Curator", favorites=["contemporary art", "architecture"])

    result = find_bridges([p_coffee_only, p_art_only], sample_candidates)

    pair = result["most_dissimilar_pair"]
    assert "Barista" in pair and "Curator" in pair
    assert len(result["bridges"]) > 0

    # Top bridge has highest min(s1, s2)
    top_bridge = result["bridges"][0]
    assert "explanation" in top_bridge
    assert top_bridge["bridge_score"] == min(top_bridge["p1_score"], top_bridge["p2_score"])


def test_find_bridges_edge_case_one_person(sample_candidates):
    p_solo = Profile(name="Solo", favorites=["specialty coffee"])
    result = find_bridges([p_solo], sample_candidates)
    assert result["most_dissimilar_pair"] == ("Solo", "Solo")
    assert len(result["bridges"]) > 0


# ---------------------------------------------------------------------
# 7. Tests for split_and_meet()
# ---------------------------------------------------------------------
def test_split_and_meet_divergent_group(sample_candidates):
    p_coffee = Profile(name="Coffee Fan", favorites=["specialty coffee"])
    p_art = Profile(name="Art Fan", favorites=["contemporary art"])

    result = split_and_meet([p_coffee, p_art], sample_candidates)

    assert "subgroup_a" in result
    assert "subgroup_b" in result
    assert "shared_dinner" in result
    assert result["subgroup_a"]["activity"] is not None
    assert result["subgroup_b"]["activity"] is not None
    assert "Split afternoon" in result["explanation"]


def test_split_and_meet_edge_case_one_person(sample_candidates):
    p_solo = Profile(name="Solo", favorites=["specialty coffee"])
    result = split_and_meet([p_solo], sample_candidates)
    assert result["subgroup_a"]["members"] == ["Solo"]
    assert result["explanation"] == "Group remains together."


# ---------------------------------------------------------------------
# 8. Tests for fairness_summary()
# ---------------------------------------------------------------------
def test_fairness_summary_balanced_vs_unbalanced(sample_candidates):
    p1 = Profile(name="Alice", favorites=["specialty coffee"])
    p2 = Profile(name="Bob", favorites=["specialty coffee"])

    # Both love specialty coffee
    balanced_result = fairness_summary([p1, p2], [sample_candidates[0]])
    assert balanced_result["is_balanced"] is True
    assert balanced_result["happiness_spread"] < 0.10
    assert balanced_result["fairness_score"] > 0.70

    # Unbalanced: pick only meat steakhouse for a vegan vs meat lover
    p_vegan = Profile(name="Vegan", favorites=["vegan", "plant-based"])
    p_meat = Profile(name="Carnivore", favorites=["steak", "meat-lover"])
    unbalanced_result = fairness_summary([p_vegan, p_meat], [sample_candidates[2]])
    assert unbalanced_result["happiness_spread"] >= 0.10
    assert unbalanced_result["per_person"]["Carnivore"] > unbalanced_result["per_person"]["Vegan"]


def test_fairness_summary_edge_case_empty():
    empty_result = fairness_summary([], [])
    assert empty_result["mean_happiness"] == 0.0
    assert empty_result["fairness_score"] == 0.0
