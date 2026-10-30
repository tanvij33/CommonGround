"""Unit tests for validation.py, llm.py, and agent.py."""

import pytest
from pydantic import BaseModel, Field

from backend.models import Candidate, Profile, ProfileConstraints, Plan
from backend.validation import validate_itinerary_grounding, ValidationResult
from backend.llm import generate_structured, LLMValidationError
from backend.agent import plan_trip, CritiqueEvaluation, GeneratedPlaylist


@pytest.fixture
def test_candidates():
    return [
        Candidate(id="c1", name="Fabrica Roastery", category="cafe", location="Lisbon", price_level="$", tags=["specialty-coffee"]),
        Candidate(id="c2", name="MAAT Museum", category="attraction", location="Lisbon", price_level="$$", tags=["contemporary-art"]),
        Candidate(id="c3", name="Prado Restaurant", category="restaurant", location="Lisbon", price_level="$$$", tags=["natural-wine"]),
        Candidate(id="c4", name="Vino Vero", category="bar", location="Lisbon", price_level="$$", tags=["natural-wine"]),
        Candidate(id="c5", name="Santa Clara 1728", category="hotel", location="Lisbon", price_level="$$$$", tags=["minimalism"]),
        Candidate(id="c6", name="Under the Cover", category="shop", location="Lisbon", price_level="$$", tags=["art-books"]),
    ]


@pytest.fixture
def test_profiles():
    return [
        Profile(name="Alice", favorites=["specialty coffee", "natural wine"], constraints=ProfileConstraints(budget="$$$")),
        Profile(name="Bob", favorites=["contemporary art", "architecture"], constraints=ProfileConstraints(budget="$$", dietary=["vegetarian"])),
    ]


# ---------------------------------------------------------------------
# 1. Tests for validation.py
# ---------------------------------------------------------------------
def test_validation_all_grounded_venues(test_candidates):
    proposed = [
        {"time_slot": "Morning", "category": "cafe", "candidate": test_candidates[0]},
        {"time_slot": "Afternoon", "category": "attraction", "candidate": test_candidates[1]},
    ]
    result: ValidationResult = validate_itinerary_grounding(proposed, test_candidates, fail_safely=False)

    assert result.is_valid is True
    assert len(result.violations) == 0
    assert len(result.verified_stops) == 2


def test_validation_rejects_hallucinated_venue_and_fails_safely(test_candidates):
    hallucinated_stop = {
        "time_slot": "Lunch",
        "category": "restaurant",
        "candidate": {"id": "fake-123", "name": "Nonexistent Magic Bistro"}
    }
    proposed = [hallucinated_stop]

    # Without fail_safely
    result_strict: ValidationResult = validate_itinerary_grounding(proposed, test_candidates, fail_safely=False)
    assert result_strict.is_valid is False
    assert len(result_strict.violations) == 1
    assert "Nonexistent Magic Bistro" in result_strict.violations[0]
    assert result_strict.feedback_prompt is not None

    # With fail_safely=True: replaces with top verified candidate in that category
    result_safe: ValidationResult = validate_itinerary_grounding(proposed, test_candidates, fail_safely=True)
    assert len(result_safe.replacements_made) == 1
    # Check that substituted venue is Prado Restaurant
    sub = result_safe.replacements_made[0]
    assert sub["rejected_venue"] == "Nonexistent Magic Bistro"
    assert sub["substituted_venue"] == "Prado Restaurant"
    assert result_safe.verified_stops[0]["candidate"].name == "Prado Restaurant"


# ---------------------------------------------------------------------
# 2. Tests for llm.py structured JSON generation
# ---------------------------------------------------------------------
class SimpleTestModel(BaseModel):
    message: str = Field(default="hello")
    score: float = Field(default=0.9)


def test_llm_generate_structured_mock():
    # Tests that generate_structured returns a valid Pydantic instance in mock mode
    result = generate_structured("Test prompt", CritiqueEvaluation)
    assert isinstance(result, CritiqueEvaluation)
    assert result.fairness_passed is True
    assert result.pacing_passed is True
    assert result.grounding_passed is True


def test_llm_generate_playlist_mock():
    result = generate_structured("Create playlist", GeneratedPlaylist)
    assert isinstance(result, GeneratedPlaylist)
    assert len(result.items) >= 2
    assert result.items[0].title != ""


# ---------------------------------------------------------------------
# 3. Tests for agent.py complete planning pipeline
# ---------------------------------------------------------------------
def test_plan_trip_pipeline(test_profiles, monkeypatch):
    monkeypatch.setenv("QLOO_MOCK", "true")
    events = []

    def capture_progress(event):
        events.append(event)

    plan = plan_trip(
        trip_id="test-trip-01",
        destination="Lisbon",
        profiles=test_profiles,
        on_progress=capture_progress
    )

    # Verify return type and fields
    assert isinstance(plan, Plan)
    assert plan.destination == "Lisbon"
    assert len(plan.itinerary) == 7 # breakfast, morning, lunch, snack, afternoon, dinner, night
    assert plan.stay is not None
    assert len(plan.playlist) >= 2
    assert plan.critique is not None
    assert plan.fairness_score > 0.0

    # Verify progress events were emitted in sequence from start to finish
    assert len(events) >= 8
    assert events[0]["percent"] == 5
    assert events[-1]["percent"] == 100
    assert any("CONSTRAINTS" in e["step"] for e in events)
    assert any("VALIDATION" in e["step"] for e in events)
    assert any("SELF_CRITIQUE" in e["step"] for e in events)

