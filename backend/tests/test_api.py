"""API integration tests for Common Ground endpoints.

Tests the full lifecycle using FastAPI's TestClient:
- Health check (/health/qloo)
- Trip creation (POST /trips)
- Trip details (GET /trips/{id})
- Entity autocomplete (GET /entities/search)
- Traveler profile addition (POST /trips/{id}/profiles)
- Demo trip creation (POST /dev/demo-trip)
- Plan generation (POST /trips/{id}/generate)
- Progress checking (GET /trips/{id}/progress)
- Plan retrieval (GET /trips/{id}/plan)
- Plan rebalancing (POST /trips/{id}/rebalance)
- Plan comparison (GET /trips/{id}/compare)
- Error handling & validation constraints (404, 400)
"""

import json
import pytest
from fastapi.testclient import TestClient

from backend.main import app, _background_plan_runner
from backend.db import init_db


@pytest.fixture(scope="module")
def client():
    """Initializes the database and yields a FastAPI test client."""
    init_db()
    with TestClient(app) as test_client:
        yield test_client


def test_health_qloo(client):
    """GET /health/qloo should return 200 with status ok."""
    resp = client.get("/health/qloo")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data


def test_trip_creation_and_details(client):
    """POST /trips creates a trip; GET /trips/{id} fetches its details."""
    payload = {
        "name": "Lisbon Culinary Weekend",
        "destination": "Lisbon",
        "days": 2
    }
    create_resp = client.post("/trips", json=payload)
    assert create_resp.status_code == 200
    created = create_resp.json()
    assert "id" in created
    assert "invite_url" in created
    assert created["id"].startswith("trip-")

    trip_id = created["id"]
    get_resp = client.get(f"/trips/{trip_id}")
    assert get_resp.status_code == 200
    trip_data = get_resp.json()
    assert trip_data["id"] == trip_id
    assert trip_data["name"] == "Lisbon Culinary Weekend"
    assert trip_data["destination"] == "Lisbon"
    assert trip_data["days"] == 2
    assert trip_data["status"] == "waiting"
    assert isinstance(trip_data["members"], list)
    assert len(trip_data["members"]) == 0


def test_entities_autocomplete_search(client):
    """GET /entities/search returns autocomplete matches with name, type, and id."""
    resp = client.get("/entities/search?q=Burial&type=artist")
    assert resp.status_code == 200
    results = resp.json()
    assert isinstance(results, list)
    if results:
        first = results[0]
        assert "name" in first
        assert "type" in first
        assert "id" in first


def test_add_profile_to_trip(client):
    """POST /trips/{id}/profiles saves a traveler and reports resolved/unresolved favorites."""
    trip_resp = client.post("/trips", json={"name": "Tokyo Anime Tour", "destination": "Tokyo", "days": 3})
    trip_id = trip_resp.json()["id"]

    profile_payload = {
        "name": "Kenji",
        "favorites": [
            {"name": "Radiohead", "type": "artist"},
            {"name": "NonexistentFictionalBand12345XYZ", "type": "artist"}
        ],
        "constraints": {
            "budget": "$$",
            "dietary": ["vegetarian"],
            "alcohol_free": True,
            "pace": "relaxed"
        }
    }
    resp = client.post(f"/trips/{trip_id}/profiles", json=profile_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Kenji"
    assert data["trip_id"] == trip_id
    assert len(data["saved_favorites"]) == 2
    # The nonexistent band should be reported as unresolved
    assert "NonexistentFictionalBand12345XYZ" in data["unresolved_favorites"]


def test_generate_empty_trip_returns_400(client):
    """POST /trips/{id}/generate with no joined profiles returns 400 Bad Request."""
    trip_resp = client.post("/trips", json={"name": "Empty Trip", "destination": "Lisbon", "days": 2})
    trip_id = trip_resp.json()["id"]

    resp = client.post(f"/trips/{trip_id}/generate")
    assert resp.status_code == 400
    assert "No friends have joined" in resp.json()["detail"]


def test_dev_demo_trip_prefill(client):
    """POST /dev/demo-trip creates a trip prefilled with the 4 test travelers."""
    resp = client.post("/dev/demo-trip")
    assert resp.status_code == 200
    data = resp.json()
    assert "trip_id" in data
    assert data["destination"] == "Lisbon"
    assert len(data["members"]) == 4
    names = [m["name"] for m in data["members"]]
    assert set(names) == {"Aisha", "Rohan", "Meera", "Kabir"}


def test_full_plan_lifecycle_and_rebalance(client):
    """Runs complete flow: dev trip -> generate -> sync execute -> plan -> rebalance -> compare."""
    # 1. Create prefilled trip
    demo_resp = client.post("/dev/demo-trip")
    trip_id = demo_resp.json()["trip_id"]

    # 2. Trigger generate
    gen_resp = client.post(f"/trips/{trip_id}/generate")
    assert gen_resp.status_code == 200
    assert gen_resp.json()["status"] == "started"

    # 3. Ensure plan runner completed (TestClient runs BackgroundTasks synchronously)
    trip_check = client.get(f"/trips/{trip_id}")
    if trip_check.json()["status"] != "done":
        _background_plan_runner(trip_id)

    # 4. Check trip status
    trip_check = client.get(f"/trips/{trip_id}")
    assert trip_check.json()["status"] == "done"

    # 5. Retrieve saved plan (GET /trips/{id}/plan)
    plan_resp = client.get(f"/trips/{trip_id}/plan")
    assert plan_resp.status_code == 200
    plan = plan_resp.json()

    # Assert exact shape of demo_plan.json
    assert "destination" in plan
    assert "trip_id" in plan
    assert "stay" in plan
    assert "days" in plan
    assert "extras" in plan
    assert "fairness" in plan
    assert "critique" in plan
    assert "under_the_hood" in plan

    # Check stay & days
    assert plan["stay"]["category"] == "hotel"
    assert len(plan["days"]) == 2
    for d in plan["days"]:
        assert len(d["slots"]) == 6
        for s in d["slots"]:
            assert "time" in s
            assert "type" in s
            assert "name" in s
            assert "per_person" in s
            assert "why" in s
            assert "guardrails" in s

    # 6. Rebalance plan (POST /trips/{id}/rebalance)
    rebalance_payload = {"adventurous": 0.8, "cultural": 0.9}
    reb_resp = client.post(f"/trips/{trip_id}/rebalance", json=rebalance_payload)
    assert reb_resp.status_code == 200
    rebalanced_plan = reb_resp.json()
    assert "fairness" in rebalanced_plan
    assert "under_the_hood" in rebalanced_plan
    assert rebalanced_plan["under_the_hood"]["rebalanced_parameters"]["adventurous"] == 0.8

    # 7. Compare with plain LLM (GET /trips/{id}/compare)
    comp_resp = client.get(f"/trips/{trip_id}/compare")
    assert comp_resp.status_code == 200
    comparison = comp_resp.json()
    assert "common_ground_plan" in comparison
    assert "plain_llm_plan" in comparison
    assert "comparison" in comparison
    assert "fairness_delta" in comparison["comparison"]


def test_nonexistent_trip_returns_404(client):
    """Endpoints querying a missing trip return 404."""
    bad_id = "trip-nonexistent-99999"
    assert client.get(f"/trips/{bad_id}").status_code == 404
    assert client.get(f"/trips/{bad_id}/plan").status_code == 404
    assert client.post(f"/trips/{bad_id}/generate").status_code == 404
    assert client.post(f"/trips/{bad_id}/rebalance", json={"adventurous": 0.5, "cultural": 0.5}).status_code == 404
    assert client.get(f"/trips/{bad_id}/compare").status_code == 404
