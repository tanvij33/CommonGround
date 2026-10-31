"""Tests for destination-aware venue classification, real-signal scoring, and itinerary hygiene.

All Qloo access is mocked: no network calls and no API quota are used.
"""

from unittest.mock import patch, MagicMock

import pytest

from backend.models import Candidate, Profile, ProfileConstraints, Trip
from backend.qloo_client import classify_place, get_recommendations, parse_raw_candidate
from backend.pipeline import generate_plan, _percentile_ranks


# ---------------------------------------------------------------------
# Classification from Qloo genre metadata
# ---------------------------------------------------------------------

@pytest.mark.parametrize("primary, genres, expected", [
    ("urn:tag:genre:place:barber_shop", [], None),
    ("urn:tag:genre:place:state_government_office", [], None),
    ("urn:tag:genre:place:personal_care", [], None),
    ("urn:tag:genre:place:restaurant:cafe", [], "cafe"),
    ("urn:tag:genre:place:restaurant:bar", [], "bar"),
    ("urn:tag:genre:place:restaurant:tapas_bar", [], "restaurant"),
    ("urn:tag:genre:place:modern_art_museum", [], "attraction"),
    ("urn:tag:genre:place:hotel:furnished_apartment_building", [], "hotel"),
    # Inn + restaurant tags: lodging always wins so it can only ever be the stay
    (None, ["urn:tag:category:place:inn", "urn:tag:genre:place:restaurant"], "hotel"),
    ("urn:tag:genre:place:restaurant", ["urn:tag:category:place:inn"], "hotel"),
    # Real Qloo ID seen for a Porto guesthouse; '&' must not hide the lodging genre
    ("urn:tag:genre:place:bed_&_breakfast", [], "hotel"),
    (None, ["urn:tag:genre:place"], None),
    # Real Cuiabá cases: unknown primary genre + loose 'tourist_attraction' tag must not become an activity
    ("urn:tag:genre:place:wellness_center", ["urn:tag:genre:place:tourist_attraction", "urn:tag:genre:place:dental_clinic"], None),
    ("urn:tag:genre:place:ballroom", ["urn:tag:genre:place:tourist_attraction"], None),
    ("urn:tag:genre:place:country_club", ["urn:tag:genre:place:tourist_attraction"], None),
    ("urn:tag:genre:place:disco_club", ["urn:tag:genre:place:restaurant:bar"], "bar"),
    ("urn:tag:genre:place:beverage_supplier", ["urn:tag:genre:place:cocktail_bar"], "bar"),
])
def test_classify_place_uses_qloo_genres(primary, genres, expected):
    category, _ = classify_place("Some Venue", "", primary, genres)
    assert category == expected


def test_name_fallback_uses_whole_words_not_substrings():
    # "Barbearia" must not be read as a bar; pousadas are lodging
    assert classify_place("Barbearia Leônidas")[0] is None
    assert classify_place("Atmã Restaurante & Pousada")[0] == "hotel"
    assert classify_place("Bar do Zé")[0] == "bar"


def _live_place(eid, name, primary, affinity=0.8, lat=41.15, lon=-8.61, extra_tags=None):
    return {
        "entity_id": eid,
        "name": name,
        "popularity": 0.8,
        "location": {"lat": lat, "lon": lon},
        "query": {"affinity": affinity},
        "properties": {"primary_genre": {"id": primary, "name": name}, "geocode": {"name": "Centro"}},
        "tags": [{"id": t, "name": t, "type": "urn:tag:genre:place"} for t in (extra_tags or [])],
    }


def test_live_recommendations_classify_and_drop_irrelevant_businesses():
    payload = {"results": {"entities": [
        _live_place("r1", "Casa Bacalhau", "urn:tag:genre:place:restaurant", 0.83),
        _live_place("b1", "Barbearia Leônidas", "urn:tag:genre:place:barber_shop", 0.9),
        _live_place("h1", "Atmã Pousada", "urn:tag:category:place:inn", 0.85),
    ]}}
    dropped = []
    with patch("backend.qloo_client.get_qloo_api_key", return_value="test_key"), \
         patch("backend.qloo_client._get_cache", return_value=None), \
         patch("backend.qloo_client._set_cache"), \
         patch("backend.qloo_client._log_interaction"), \
         patch("httpx.Client") as mock_client_cls:
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = payload
        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        cands = get_recommendations(
            signals=[], category="restaurant", location="Porto", force_mock=False,
            location_query="Porto, Porto, Portugal", signal_ids=["sig-1"],
            include_other_categories=True, dropped_log=dropped
        )
        params = mock_client.get.call_args[1]["params"]

    assert params["filter.location.query"] == "Porto, Porto, Portugal"
    assert params["filter.tags"] == "urn:tag:genre:place:restaurant"
    by_name = {c.name: c for c in cands}
    assert "Barbearia Leônidas" not in by_name
    assert by_name["Atmã Pousada"].category == "hotel"
    assert by_name["Casa Bacalhau"].category == "restaurant"
    assert by_name["Casa Bacalhau"].qloo_affinity == 0.83
    assert by_name["Casa Bacalhau"].affinity_source == "qloo"
    assert dropped and "barber_shop" in dropped[0]["reason"]


def test_missing_affinity_is_not_invented():
    cand = parse_raw_candidate({"id": "x", "name": "No Score Cafe"}, category="cafe", location="Porto")
    assert cand.qloo_affinity == 0.0
    assert cand.affinity_source == "missing"


def test_percentile_ranks_handles_ties_and_single_values():
    assert _percentile_ranks({"a": 0.8}) == {"a": 0.5}
    ranks = _percentile_ranks({"a": 0.70, "b": 0.80, "c": 0.80, "d": 0.90})
    assert ranks["a"] == 0.0 and ranks["d"] == 1.0
    assert ranks["b"] == ranks["c"]


# ---------------------------------------------------------------------
# End-to-end plan generation with a mocked Qloo layer
# ---------------------------------------------------------------------

def _cand(cid, name, category, lat=41.15, lon=-8.61, genre=None):
    return Candidate(
        id=cid, name=name, category=category, location="Porto", qloo_affinity=0.8,
        price_level="$$", latitude=lat, longitude=lon, popularity=0.7,
        primary_genre=genre or f"urn:tag:genre:place:{category}", affinity_source="qloo",
        tags=["vegetarian"] if category in ("restaurant", "cafe") else []
    )


POOL = (
    [_cand(f"h{i}", f"Hotel {i}", "hotel") for i in range(2)]
    + [_cand(f"r{i}", f"Restaurant {i}", "restaurant") for i in range(6)]
    + [_cand(f"c{i}", f"Cafe {i}", "cafe") for i in range(3)]
    + [_cand(f"a{i}", f"Attraction {i}", "attraction", genre=f"urn:tag:genre:place:{g}")
       for i, g in enumerate(["museum", "park", "museum", "garden", "castle", "art_gallery"])]
    + [_cand(f"s{i}", f"Shop {i}", "shop") for i in range(2)]
    + [_cand("far", "Far Away Museum", "attraction", lat=38.72, lon=-9.14)]  # Lisbon, ~275 km away
)


def _fake_recommendations(category, include_other_categories=False, **kwargs):
    # Every category call returns the whole pool, as overlapping Qloo filters can
    return [c.model_copy(deep=True) for c in POOL]


def _fake_affinities(signal_ids, entity_ids):
    # Each traveler has a distinct real-looking preference ordering
    seed = sum(ord(ch) for ch in signal_ids[0])
    return {eid: 0.70 + ((hash(eid) + seed) % 20) / 100.0 for eid in entity_ids}


def _profiles():
    return [
        Profile(name="Aisha", favorites=[{"name": "Radiohead", "type": "artist"}], constraints=ProfileConstraints()),
        Profile(name="Rohan", favorites=[{"name": "Metallica", "type": "artist"}], constraints=ProfileConstraints()),
        Profile(name="Meera", favorites=[{"name": "Norah Jones", "type": "artist"}], constraints=ProfileConstraints(alcohol_free=True)),
    ]


def _run_plan(days=2):
    trip = Trip(id="trip-test", title="Porto test", destination="Porto", destination_query="Porto, Porto, Portugal", days=days)
    with patch("backend.pipeline.resolve_favorite", side_effect=lambda name, **kw: {"id": f"sig-{name}"}), \
         patch("backend.pipeline.get_recommendations", side_effect=_fake_recommendations), \
         patch("backend.pipeline.get_place_affinities", side_effect=_fake_affinities), \
         patch("backend.pipeline.safe_build_playlist", return_value={"mode": "favourites", "status": "unavailable", "entries": []}):
        return generate_plan(trip, _profiles(), config={"force_mock": False})


def test_plan_never_schedules_lodging_and_keeps_stay_separate():
    plan = _run_plan()
    slots = [s for d in plan["days"] for s in d["slots"]]
    assert plan["stay"]["category"] == "hotel"
    assert all(s["type"] != "hotel" for s in slots)
    assert plan["stay"]["id"] not in {s["candidate_id"] for s in slots}


def test_plan_has_no_duplicate_venues_including_extras():
    plan = _run_plan()
    ids = [s["candidate_id"] for d in plan["days"] for s in d["slots"]]
    extras = [v["id"] for k, v in plan["extras"].items() if k != "music" and v]
    assert len(ids) == len(set(ids))
    assert not set(ids) & set(extras)
    assert len(extras) == len(set(extras))


def test_plan_excludes_far_venues_and_bars_for_alcohol_free_group():
    plan = _run_plan()
    names = {s["name"] for d in plan["days"] for s in d["slots"]}
    assert "Far Away Museum" not in names
    assert any("Far Away Museum" == e["name"] for e in plan["under_the_hood"]["candidate_pool"]["excluded_examples"])
    # Meera is alcohol-free and the pool has no bars: the nightlife slot falls back to a cafe or is skipped
    assert all(s["type"] != "bar" for d in plan["days"] for s in d["slots"])


def test_plan_scores_come_from_qloo_affinity_and_are_labelled():
    plan = _run_plan()
    slot = plan["days"][0]["slots"][0]
    assert set(slot["qloo_affinity_per_person"]) == {"Aisha", "Rohan", "Meera"}
    assert all(0.0 <= v <= 1.0 for v in slot["per_person"].values())
    sources = plan["under_the_hood"]["scores"]["per_person_affinity_source"]
    assert set(sources.values()) == {"qloo_insights_affinity"}
    assert "basis" in plan["fairness"]


def test_unfillable_slots_are_skipped_not_filled_with_other_categories():
    plan = _run_plan(days=3)
    total_slots = sum(len(d["slots"]) for d in plan["days"])
    # 18 template slots but only 17 usable activity venues (far museum excluded) and no reuse allowed
    assert total_slots <= 17
    assert plan["under_the_hood"]["skipped_slots"]


# ---------------------------------------------------------------------
# Demo friends join the CURRENT trip
# ---------------------------------------------------------------------

def test_demo_profiles_are_added_to_the_current_trip():
    from fastapi.testclient import TestClient
    from backend.main import app

    with TestClient(app) as client:
        trip_id = client.post("/trips", json={"name": "Seoul crew", "destination": "Seoul", "destination_query": "Seoul, 대한민국", "days": 2}).json()["id"]
        first = client.post(f"/trips/{trip_id}/demo-profiles")
        assert first.status_code == 200 and first.json()["added_count"] == 4

        # Idempotent: clicking twice does not duplicate friends
        assert client.post(f"/trips/{trip_id}/demo-profiles").json()["added_count"] == 0

        members = client.get(f"/trips/{trip_id}").json()["members"]
        assert sorted(m["name"] for m in members) == ["Aisha", "Kabir", "Meera", "Rohan"]

        assert client.post("/trips/trip-does-not-exist/demo-profiles").status_code == 404


# ---------------------------------------------------------------------
# Budget handling and the staged fallback (regression: Tokyo failed with
# "Qloo returned no activity venues" because taste-matched venues were all
# above the group's budget and were rejected after fetching)
# ---------------------------------------------------------------------

from backend.qloo_client import QlooNoCandidatesError
from backend.scoring import apply_constraints, group_budget_level


def _priced(cid, name, category, price, verified=True):
    return Candidate(id=cid, name=name, category=category, location="Tokyo", qloo_affinity=0.8, price_level=price,
                     price_verified=verified, latitude=35.68, longitude=139.70, popularity=0.7,
                     primary_genre=f"urn:tag:genre:place:{category}", affinity_source="qloo")


def _venues(category, tag, price, n=6, verified=True):
    return [_priced(f"{category}-{tag}-{i}", f"{tag.title()} {category} {i}", category, price, verified) for i in range(n)]


def _budget_group(budget="$$"):
    return [Profile(name="Paoli", favorites=[{"name": "Loewe", "type": "brand"}], constraints=ProfileConstraints(budget=budget))]


def _run_budget_plan(fake, budget="$$", days=2):
    trip = Trip(id="trip-tokyo", title="Tokyo", destination="Tokyo", destination_query="東京都", days=days)
    recorder = MagicMock(side_effect=fake)
    with patch("backend.pipeline.resolve_favorite", side_effect=lambda name, **kw: {"id": f"sig-{name}"}), \
         patch("backend.pipeline.get_recommendations", recorder), \
         patch("backend.pipeline.get_place_affinities", side_effect=_fake_affinities), \
         patch("backend.pipeline.safe_build_playlist", return_value={"mode": "favourites", "status": "unavailable", "entries": []}):
        return generate_plan(trip, _budget_group(budget), config={"force_mock": False}), recorder


def _fallback_fake(category, signal_ids=None, **kw):
    """Taste-matched results are premium with no sights; destination-only results are affordable."""
    if signal_ids:
        if category == "hotel":
            return _venues("hotel", "inn", "$$", n=2, verified=False)
        if category == "attraction":
            return []
        return _venues(category, "lux", "$$$$")
    if category == "hotel":
        return []
    return _venues(category, "cheap", "$$")


def test_group_budget_level_is_the_lowest_member_ceiling():
    assert group_budget_level([]) is None
    assert group_budget_level(_budget_group("$$")) == 2
    assert group_budget_level(_budget_group("$$$$")) is None            # no effective limit
    both = _budget_group("$$$") + [Profile(name="B", favorites=[], constraints=ProfileConstraints(budget="$"))]
    assert group_budget_level(both) == 1
    assert group_budget_level([Profile(name="C", favorites=[], constraints=ProfileConstraints())]) is None


def test_budget_is_sent_to_qloo_only_for_categories_that_have_prices():
    _, recorder = _run_budget_plan(_fallback_fake)
    sent = {}
    for call in recorder.call_args_list:
        sent.setdefault(call.kwargs["category"], set()).add(call.kwargs["max_price_level"])
    assert sent["restaurant"] == sent["cafe"] == sent["bar"] == sent["shop"] == {2}
    assert sent["hotel"] == sent["attraction"] == {None}               # Qloo has no price data for these


def test_unknown_price_is_unverified_not_rejected():
    hotel = _priced("h", "Unpriced Hotel", "hotel", "$$", verified=False)
    priced = _priced("r", "Pricey", "restaurant", "$$$")
    kept, records = apply_constraints([hotel, priced], _budget_group("$"))
    assert records["h"]["budget_status"] == "unverified" and hotel in kept
    assert records["r"]["budget_status"] == "failed" and priced not in kept     # a known price is still enforced


def test_parse_marks_missing_price_as_unverified():
    unpriced = parse_raw_candidate({"id": "x", "name": "Some Hotel"}, category="hotel", location="Tokyo")
    priced = parse_raw_candidate({"id": "y", "name": "Some Cafe", "properties": {"price_level": 2}}, category="cafe", location="Tokyo")
    assert unpriced.price_verified is False and priced.price_verified is True and priced.price_level == "$$"


def test_live_query_carries_the_price_ceiling():
    payload = {"results": {"entities": [{"entity_id": "p1", "name": "Ramen Ya", "popularity": 0.5, "location": {"lat": 35.6, "lon": 139.7},
                                          "properties": {"primary_genre": {"id": "urn:tag:genre:place:restaurant"}, "price_level": 2}}]}}
    with patch("backend.qloo_client.get_qloo_api_key", return_value="k"), patch("backend.qloo_client._get_cache", return_value=None), \
         patch("backend.qloo_client._set_cache"), patch("backend.qloo_client._log_interaction"), patch("httpx.Client") as client_cls:
        resp = MagicMock(status_code=200)
        resp.json.return_value = payload
        client = MagicMock()
        client.get.return_value = resp
        client_cls.return_value.__enter__.return_value = client
        get_recommendations(signals=[], category="restaurant", location="Tokyo", force_mock=False,
                            location_query="東京都", signal_ids=["s1"], max_price_level=2)
        assert client.get.call_args[1]["params"]["filter.price_level.max"] == 2
        get_recommendations(signals=[], category="restaurant", location="Tokyo", force_mock=False,
                            location_query="東京都", signal_ids=["s1"])
        assert "filter.price_level.max" not in client.get.call_args[1]["params"]


def test_tokyo_regression_over_budget_taste_results_trigger_the_fallback_not_a_crash():
    plan, recorder = _run_budget_plan(_fallback_fake)
    slots = [s for d in plan["days"] for s in d["slots"]]
    fallback = plan["under_the_hood"]["fallback"]
    assert slots and fallback["used"] is True
    assert {"restaurant", "attraction"} <= set(fallback["categories"]) and fallback["relaxed"] == "taste signals"
    assert all("lux" not in s["candidate_id"] for s in slots)                    # over-budget venues never scheduled
    assert all(s["sourcing"] == "destination_popular" for s in slots)            # honest about where they came from
    assert all("not matched to the group's taste signals" in s["why"] for s in slots)
    assert plan["stay"] is not None and plan["stay"]["category"] == "hotel"
    assert plan["under_the_hood"]["budget_ceiling"] == "$$"
    fallback_calls = [c for c in recorder.call_args_list if not c.kwargs["signal_ids"]]
    assert fallback_calls and all(c.kwargs["signals"] == [] for c in fallback_calls)       # taste really was relaxed
    assert all(c.kwargs["max_price_level"] == (2 if c.kwargs["category"] in ("restaurant", "cafe", "bar", "shop") else None)
               for c in recorder.call_args_list)                                           # budget never relaxed


def test_no_fallback_when_taste_matched_venues_already_fit():
    def taste_ok(category, signal_ids=None, **kw):
        return _venues(category, "good", "$$", n=5)
    plan, recorder = _run_budget_plan(taste_ok)
    assert plan["under_the_hood"]["fallback"] == {"used": False}
    assert all(s["sourcing"] == "taste_matched" for d in plan["days"] for s in d["slots"])
    assert all(c.kwargs["signal_ids"] for c in recorder.call_args_list)                    # one pass only


def test_nothing_affordable_gives_an_explanation_and_never_substitutes():
    def all_luxury(category, signal_ids=None, **kw):
        return _venues("hotel", "inn", "$$", n=1, verified=False) if category == "hotel" else _venues(category, "lux", "$$$$")
    with pytest.raises(RuntimeError) as err:
        _run_budget_plan(all_luxury)
    message = str(err.value)
    assert "none fit this group's constraints" in message and "$$ budget" in message
    assert "exceeds group budget limit" in message and "Widening beyond the group's taste signals did not help" in message
    assert "Nothing was substituted" in message and "no activity venues" not in message


def test_nothing_returned_by_qloo_is_explained_separately():
    def only_hotels(category, signal_ids=None, **kw):
        if category == "hotel":
            return _venues("hotel", "inn", "$$", n=1, verified=False)
        raise QlooNoCandidatesError("No candidates returned by Qloo API")
    with pytest.raises(RuntimeError) as err:
        _run_budget_plan(only_hotels)
    assert "Qloo returned no restaurants, cafes, bars, sights or shops for Tokyo" in str(err.value)
    assert "No candidates returned" in str(err.value)
