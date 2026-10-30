"""Unit and integration tests for Qloo client and live/mock location handling.

Verifies:
1. Live mode sends the requested city in filter.location.query to Qloo API.
2. Lisbon mock IDs (lis-*) are NOT returned for Delhi or Tokyo when live mode is used.
3. Missing API key raises QlooMissingApiKeyError in live mode.
4. HTTP 401/403 raises QlooAuthError.
5. Network timeouts raise QlooNetworkError.
6. Zero candidates returned raises QlooNoCandidatesError (never falls back to Lisbon).
7. Mock mode returns city-specific candidates for Lisbon, Tokyo, and Delhi, and raises
   QlooCityNotFoundError for uncataloged cities rather than silently returning Lisbon.
"""

import os
import pytest
import httpx
from unittest.mock import patch, MagicMock

from backend.qloo_client import (
    get_recommendations,
    search_entity,
    parse_raw_candidate,
    is_qloo_mock_mode,
    QlooError,
    QlooMissingApiKeyError,
    QlooAuthError,
    QlooNetworkError,
    QlooNoCandidatesError,
    QlooCityNotFoundError
)
from backend.models import Candidate


# ---------------------------------------------------------------------
# 1. Tests for City-Specific Location in Live Qloo API Requests
# ---------------------------------------------------------------------

def test_live_qloo_request_includes_requested_city_delhi():
    """Verifies that requesting Delhi sends filter.location.query=Delhi to the live API."""
    mock_response_data = {
        "results": {
            "items": [
                {
                    "id": "urn:entity:place:delhi-live-01",
                    "name": "Indian Accent New Delhi",
                    "category": "restaurant",
                    "location": "Delhi, Lodhi Road",
                    "affinity": {"score": 0.94},
                    "tags": ["progressive-indian", "tasting-menu"],
                    "price_level": "$$$$"
                }
            ]
        }
    }

    with patch("backend.qloo_client.get_qloo_api_key", return_value="test_hackathon_key"), \
         patch("backend.qloo_client.is_qloo_mock_mode", return_value=False), \
         patch("backend.qloo_client._get_cache", return_value=None), \
         patch("httpx.Client") as mock_client_cls:

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response_data
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        candidates = get_recommendations(
            signals=["progressive-indian"],
            category="restaurant",
            location="Delhi",
            force_mock=False
        )

        # 1. Verify HTTP request was made with Delhi
        assert mock_client.get.called
        call_args = mock_client.get.call_args
        params = call_args[1].get("params") or call_args[0][1]
        assert params["filter.location.query"] == "Delhi"

        # 2. Verify candidate results are Delhi venues and NOT Lisbon mock IDs
        assert len(candidates) == 1
        cand = candidates[0]
        assert cand.id == "urn:entity:place:delhi-live-01"
        assert cand.name == "Indian Accent New Delhi"
        assert "Delhi" in cand.location
        assert not cand.id.startswith("lis-")


def test_live_qloo_request_includes_requested_city_tokyo():
    """Verifies that requesting Tokyo sends filter.location.query=Tokyo to the live API."""
    mock_response_data = {
        "results": {
            "items": [
                {
                    "id": "urn:entity:place:tokyo-live-01",
                    "name": "Bar Trench Shibuya",
                    "category": "bar",
                    "location": "Tokyo, Ebisu",
                    "affinity": {"score": 0.91},
                    "tags": ["craft-cocktails", "speakeasy"]
                }
            ]
        }
    }

    with patch("backend.qloo_client.get_qloo_api_key", return_value="test_hackathon_key"), \
         patch("backend.qloo_client.is_qloo_mock_mode", return_value=False), \
         patch("backend.qloo_client._get_cache", return_value=None), \
         patch("httpx.Client") as mock_client_cls:

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response_data
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        candidates = get_recommendations(
            signals=["cocktails"],
            category="bar",
            location="Tokyo",
            force_mock=False
        )

        assert mock_client.get.called
        params = mock_client.get.call_args[1]["params"]
        assert params["filter.location.query"] == "Tokyo"
        assert not candidates[0].id.startswith("lis-")
        assert "Tokyo" in candidates[0].location


# ---------------------------------------------------------------------
# 2. Tests for Error Handling (Missing Key, 401 Auth, Timeout, Zero Results)
# ---------------------------------------------------------------------

def test_missing_api_key_raises_clear_error_in_live_mode():
    """Verifies that attempting live mode without QLOO_API_KEY raises QlooMissingApiKeyError."""
    with patch("backend.qloo_client.get_qloo_api_key", return_value=""), \
         patch("backend.qloo_client.is_qloo_mock_mode", return_value=False):

        with pytest.raises(QlooMissingApiKeyError) as exc_info:
            get_recommendations(signals=["wine"], category="bar", location="Delhi", force_mock=False)

        assert "QLOO_API_KEY environment variable is missing" in str(exc_info.value)


def test_invalid_api_key_raises_qloo_auth_error():
    """Verifies that HTTP 401/403 raises QlooAuthError with remediation guidance."""
    with patch("backend.qloo_client.get_qloo_api_key", return_value="invalid_expired_key"), \
         patch("backend.qloo_client.is_qloo_mock_mode", return_value=False), \
         patch("backend.qloo_client._get_cache", return_value=None), \
         patch("httpx.Client") as mock_client_cls:

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized: Invalid API Key"
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        with pytest.raises(QlooAuthError) as exc_info:
            get_recommendations(signals=["wine"], category="bar", location="Lisbon", force_mock=False)

        assert "Qloo Authentication Failed" in str(exc_info.value)
        assert "401" in str(exc_info.value)


def test_network_failure_raises_qloo_network_error():
    """Verifies that connection errors raise QlooNetworkError."""
    with patch("backend.qloo_client.get_qloo_api_key", return_value="test_key"), \
         patch("backend.qloo_client.is_qloo_mock_mode", return_value=False), \
         patch("backend.qloo_client._get_cache", return_value=None), \
         patch("httpx.Client") as mock_client_cls:

        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")
        mock_client_cls.return_value.__enter__.return_value = mock_client

        with pytest.raises(QlooNetworkError) as exc_info:
            get_recommendations(signals=["wine"], category="bar", location="Tokyo", force_mock=False)

        assert "Failed to connect to Qloo API" in str(exc_info.value)


def test_zero_candidates_returned_does_not_fallback_to_lisbon():
    """Verifies that an empty result set raises QlooNoCandidatesError rather than defaulting to Lisbon."""
    with patch("backend.qloo_client.get_qloo_api_key", return_value="test_key"), \
         patch("backend.qloo_client.is_qloo_mock_mode", return_value=False), \
         patch("backend.qloo_client._get_cache", return_value=None), \
         patch("httpx.Client") as mock_client_cls:

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"results": {"items": []}} # 0 items
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        with pytest.raises(QlooNoCandidatesError) as exc_info:
            get_recommendations(signals=["wine"], category="bar", location="Delhi", force_mock=False)

        assert "No candidates returned by Qloo API for city 'Delhi'" in str(exc_info.value)


# ---------------------------------------------------------------------
# 3. Tests for Mock Mode Handling (No Silent Lisbon Defaulting)
# ---------------------------------------------------------------------

def test_mock_mode_returns_delhi_venues_for_delhi():
    """Verifies that mock mode returns authentic Delhi candidates for Delhi."""
    candidates = get_recommendations(signals=["specialty coffee"], category="cafe", location="Delhi", force_mock=True)
    assert len(candidates) > 0
    for c in candidates:
        assert c.id.startswith("del-")
        assert "Delhi" in c.location
        assert not c.id.startswith("lis-")


def test_mock_mode_returns_tokyo_venues_for_tokyo():
    """Verifies that mock mode returns authentic Tokyo candidates for Tokyo."""
    candidates = get_recommendations(signals=["ambient"], category="bar", location="Tokyo", force_mock=True)
    assert len(candidates) > 0
    for c in candidates:
        assert c.id.startswith("tyo-")
        assert "Tokyo" in c.location
        assert not c.id.startswith("lis-")


def test_mock_mode_raises_error_for_unknown_city_instead_of_defaulting_to_lisbon():
    """Verifies that requesting an unknown city in mock mode does NOT silently return Lisbon data."""
    with pytest.raises(QlooCityNotFoundError) as exc_info:
        get_recommendations(signals=["wine"], category="bar", location="Berlin", force_mock=True)

    assert "City 'Berlin' is not available in the offline mock catalog" in str(exc_info.value)


# ---------------------------------------------------------------------
# 4. Tests for Robust Parsing Layer
# ---------------------------------------------------------------------

def test_parse_raw_candidate_with_nested_affinity_and_price_int():
    raw = {
        "id": "qloo-place-99",
        "name": "Blue Tokai Delhi",
        "affinity": {"score": 0.884},
        "price": 1,
        "location": {"city": "Delhi", "neighborhood": "Saidulajab"},
        "tags": ["specialty-coffee", "roastery"]
    }
    cand = parse_raw_candidate(raw, category="cafe", location="Delhi")
    assert cand.id == "qloo-place-99"
    assert cand.name == "Blue Tokai Delhi"
    assert cand.qloo_affinity == 0.88
    assert cand.price_level == "$"
    assert "Delhi" in cand.location


def test_parse_raw_candidate_with_none_neighborhood_does_not_crash():
    """REGRESSION TEST: Verifies that locality.neighborhood=None does NOT crash with NoneType attribute error."""
    raw = {
        "id": "qloo-rua-nova",
        "name": "Rua nova do Carvalho",
        "properties": {
            "address": "Rua Nova do Carvalho, Lisbon",
            "locality": {
                "city": {"name": "Lisbon"},
                "neighborhood": None  # Triggered the bug: 'NoneType' object has no attribute 'get'
            },
            "tags": [{"name": "food"}, {"name": "bar"}],
            "price_level": 2
        }
    }
    cand = parse_raw_candidate(raw, category="bar", location="Lisbon")
    assert cand.id == "qloo-rua-nova"
    assert cand.name == "Rua nova do Carvalho"
    assert cand.location == "Lisbon"
    assert cand.price_level == "$$"
    assert "food" in cand.tags
    assert "bar" in cand.tags


def test_resolve_favorite_prefers_artist_entity_type():
    """Verifies that ambiguous names like 'Metallica' or 'Slipknot' prefer music artist over movies/books."""
    from backend.qloo_client import resolve_favorite

    mock_search_results = [
        {"name": "Metallica: Some Kind of Monster", "subtype": "urn:entity:movie", "entity_id": "movie-1"},
        {"name": "Metallica and Ozzy Osbourne", "subtype": "urn:entity:artist", "entity_id": "artist-1"},
        {"name": "Metallica Acessórios", "subtype": "urn:entity:place", "entity_id": "place-1"}
    ]

    with patch("backend.qloo_client.search_entity", return_value=mock_search_results):
        res = resolve_favorite("Metallica", force_mock=False)
        assert res is not None
        assert res["id"] == "artist-1"
        assert res["subtype"] == "urn:entity:artist"


def test_resolve_signal_entities_skips_unresolved_favorites():
    """Verifies that unknown favorites are skipped cleanly while known ones resolve."""
    from backend.qloo_client import resolve_signal_entities

    def mock_search(query, force_mock=None):
        if query == "Norah Jones":
            return [{"name": "Norah Jones", "subtype": "urn:entity:artist", "entity_id": "norah-1"}]
        return [] # NOT FOUND for unknown signals

    with patch("backend.qloo_client.search_entity", side_effect=mock_search):
        ids, resolved, skipped = resolve_signal_entities(["Norah Jones", "FakeUnknownBand"])
        assert len(ids) == 1
        assert ids[0] == "norah-1"
        assert len(resolved) == 1
        assert resolved[0]["name"] == "Norah Jones"
        assert skipped == ["FakeUnknownBand"]


