"""FastAPI REST API for Common Ground.

Provides endpoints for:
- System & Qloo health checks.
- Trip creation, member joining, and profile management with SQLite persistence.
- Cultural entity search via Qloo for frontend autocomplete.
- Taste-fair itinerary plan generation with SSE progress streaming.
- Plan retrieval in the exact data/demo_plan.json shape.
- Plan rebalancing (adventurous/cultural) without new API calls.
- Plain-LLM vs. Common Ground side-by-side fairness comparison.
- Developer demo trip setup prefilled with the 4 test travelers.
"""

import os
import uuid
import json
import asyncio
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.models import (
    Candidate,
    Profile,
    ProfileConstraints,
    Trip,
    Plan,
    FavoriteInput,
    ProfileCreateInput,
    TripCreateInput,
    TripCreateResponse,
    RebalanceInput
)
from backend.db import init_db, get_db, SessionLocal, TripDB, ProfileDB, PlanDB
from backend.pipeline import (
    generate_plan,
    rebalance_plan,
    generate_plain_llm_comparison
)
from backend.qloo_client import (
    search_entity,
    search_destinations,
    get_recommendations,
    resolve_favorite,
    is_type_match,
    is_qloo_mock_mode,
    get_qloo_base_url,
    get_qloo_api_key,
    LOG_FILE_PATH,
    QlooError
)
from backend.mock_data import MOCK_CITIES_DATA

# Initialize database tables & migrations on startup
init_db()

app = FastAPI(
    title="Common Ground API",
    description="Taste-fair group trip planning engine powered by Qloo cultural intelligence.",
    version="1.0.0"
)

# Enable CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory SSE progress broker
progress_queues: Dict[str, List[asyncio.Queue]] = {}
latest_trip_progress: Dict[str, Dict[str, Any]] = {}


def update_trip_progress(trip_id: str, message: str, percent: int, status: str = "running"):
    """Pushes a progress event to all active SSE listeners for a trip."""
    payload = {"message": message, "percent": percent, "status": status}
    latest_trip_progress[trip_id] = payload
    if trip_id in progress_queues:
        for q in list(progress_queues[trip_id]):
            try:
                q.put_nowait(payload)
            except Exception:
                pass


# =====================================================================
# 1. Health & Status Endpoints
# =====================================================================

@app.get("/api/health")
def health_check():
    """Returns system status, active Qloo mode, and target URL."""
    api_key_set = bool(get_qloo_api_key())
    mock_mode = is_qloo_mock_mode()
    return {
        "status": "healthy",
        "mock_mode": mock_mode,
        "base_url": get_qloo_base_url(),
        "api_key_configured": api_key_set,
        "mode_label": "MOCK / OFFLINE" if mock_mode else "LIVE QLOO API",
        "available_mock_cities": list(MOCK_CITIES_DATA.keys())
    }


@app.get("/health/qloo")
@app.get("/api/health/qloo")
def health_qloo():
    """Performs one real search against the live Qloo API and returns ok or the exact error."""
    try:
        results = search_entity("Radiohead", force_mock=False)
        return {
            "status": "ok",
            "message": "Connected to Qloo API successfully",
            "base_url": get_qloo_base_url(),
            "results_found": len(results),
            "sample_match": results[0].get("name") if results else None
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "error": str(e),
            "base_url": get_qloo_base_url()
        }


# =====================================================================
# 2. Cultural Entity Autocomplete Search
# =====================================================================

@app.get("/entities/search")
@app.get("/api/entities/search")
def search_cultural_entities_autocomplete(
    q: str = Query(..., min_length=1, description="Entity name or query string"),
    type: Optional[str] = Query(None, description="Optional type hint: artist, movie, tv_show, brand, place")
):
    """Qloo entity search for autocomplete, returning name, type, id, and image if available."""
    try:
        try:
            results = search_entity(name=q)
        except Exception:
            results = search_entity(name=q, force_mock=True)
        formatted = []
        for r in results:
            if not isinstance(r, dict):
                continue
            props = r.get("properties") or {}
            eid = r.get("entity_id") or r.get("id") or r.get("urn") or props.get("id") or ""
            name = r.get("name") or r.get("title") or props.get("name") or ""
            subtype = r.get("subtype") or r.get("type") or "cultural_entity"

            if type and not is_type_match(str(subtype), type):
                continue

            images = props.get("images") or r.get("images") or []
            image_url = None
            if isinstance(images, list) and images:
                first = images[0]
                image_url = first.get("url") if isinstance(first, dict) else str(first)
            elif isinstance(images, dict):
                image_url = images.get("url")

            formatted.append({
                "id": str(eid),
                "name": str(name),
                "type": str(subtype),
                "image": image_url
            })

        return formatted[:15]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Entity search error: {e}")


@app.get("/destinations/search")
@app.get("/api/destinations/search")
def search_destinations_autocomplete(
    q: str = Query(..., min_length=2, max_length=100, description="City, region, or country name"),
    limit: int = Query(8, ge=1, le=10)
):
    """Qloo locality search for destination autocomplete. Returns 502 if Qloo is unavailable."""
    try:
        return search_destinations(q, limit=limit)
    except QlooError as e:
        raise HTTPException(status_code=502, detail=f"Destination search is unavailable: {e}")


# =====================================================================
# 3. Trip Creation & Member Profile Endpoints
# =====================================================================

@app.post("/trips", response_model=TripCreateResponse)
def create_trip(payload: TripCreateInput, db: Session = Depends(get_db)):
    """Initializes a new group trip and returns the trip ID and friend invite URL."""
    trip_id = f"trip-{uuid.uuid4().hex[:8]}"
    new_trip = TripDB(
        id=trip_id,
        title=payload.name.strip(),
        name=payload.name.strip(),
        destination=payload.destination.strip(),
        destination_query=(payload.destination_query or "").strip() or None,
        days=payload.days,
        status="waiting"
    )
    db.add(new_trip)
    db.commit()

    invite_url = f"http://localhost:3000/trips/{trip_id}/join"
    return TripCreateResponse(id=trip_id, invite_url=invite_url)


@app.get("/trips/{id}")
def get_trip_details(id: str, db: Session = Depends(get_db)):
    """Retrieves trip details plus the list of friends who have joined."""
    trip = db.query(TripDB).filter_by(id=id).first()
    if not trip:
        raise HTTPException(status_code=404, detail=f"Trip '{id}' not found")

    profiles = db.query(ProfileDB).filter_by(trip_id=id).all()
    members = []
    for p in profiles:
        members.append({
            "id": p.id,
            "name": p.name,
            "favorites": p.favorites,
            "constraints": p.constraints
        })

    return {
        "id": trip.id,
        "name": trip.name or trip.title,
        "destination": trip.destination,
        "destination_query": trip.destination_query,
        "days": trip.days or 2,
        "status": trip.status or "waiting",
        "created_at": trip.created_at.isoformat() if trip.created_at else None,
        "members": members
    }


@app.post("/trips/{id}/profiles")
def add_profile_to_trip(
    id: str,
    payload: ProfileCreateInput,
    db: Session = Depends(get_db)
):
    """Saves one traveler to a trip. Also reports any favorite that could not be resolved."""
    trip = db.query(TripDB).filter_by(id=id).first()
    if not trip:
        raise HTTPException(status_code=404, detail=f"Trip '{id}' not found")

    saved_favorites = []
    unresolved_favorites = []

    for fav in payload.favorites:
        fav_name = fav.name.strip()
        fav_type = fav.type
        qloo_id = fav.qloo_id

        if not qloo_id:
            # Resolve entity against Qloo (safe against network failures)
            res = None
            try:
                res = resolve_favorite(fav_name, type_hint=fav_type)
            except Exception:
                res = None

            if res and res.get("id"):
                qloo_id = res["id"]
                saved_favorites.append({
                    "name": res.get("name", fav_name),
                    "type": res.get("type", fav_type or "cultural_entity"),
                    "qloo_id": qloo_id
                })
            else:
                unresolved_favorites.append(fav_name)
                saved_favorites.append({
                    "name": fav_name,
                    "type": fav_type or "cultural_entity",
                    "qloo_id": None
                })
        else:
            saved_favorites.append({
                "name": fav_name,
                "type": fav_type or "cultural_entity",
                "qloo_id": qloo_id
            })

    profile_id = f"prof-{uuid.uuid4().hex[:8]}"
    profile_db = ProfileDB(
        id=profile_id,
        trip_id=id,
        name=payload.name.strip(),
        favorites_json=json.dumps(saved_favorites),
        constraints_json=json.dumps(payload.constraints.model_dump())
    )
    db.add(profile_db)
    db.commit()

    return {
        "profile_id": profile_id,
        "trip_id": id,
        "name": payload.name.strip(),
        "saved_favorites": saved_favorites,
        "unresolved_favorites": unresolved_favorites,
        "constraints": payload.constraints.model_dump()
    }


# =====================================================================
# 4. Plan Generation & SSE Streaming
# =====================================================================

def _background_plan_runner(trip_id: str):
    """Background task running generate_plan with timeout and error handling."""
    with SessionLocal() as db:
        trip = db.query(TripDB).filter_by(id=trip_id).first()
        if not trip:
            return

        profiles_db = db.query(ProfileDB).filter_by(trip_id=trip_id).all()
        if not profiles_db:
            trip.status = "failed"
            db.commit()
            update_trip_progress(trip_id, "No friends found for trip", 0, "failed")
            return

        profiles = []
        for pdb in profiles_db:
            favs = pdb.favorites
            cstr = pdb.constraints
            profiles.append(
                Profile(
                    id=pdb.id,
                    name=pdb.name,
                    favorites=favs,
                    constraints=ProfileConstraints(**cstr)
                )
            )

        trip_model = Trip(
            id=trip.id,
            title=trip.title or trip.name or f"Trip to {trip.destination}",
            destination=trip.destination,
            destination_query=trip.destination_query,
            days=trip.days or 2,
            members=profiles
        )

        def cb(msg: str, pct: int):
            update_trip_progress(trip_id, msg, pct, "running")

        try:
            plan_json_dict = generate_plan(
                trip=trip_model,
                profiles=profiles,
                progress_callback=cb
            )

            # Persist plan to SQLite
            plan_record = db.query(PlanDB).filter_by(trip_id=trip_id).first()
            if not plan_record:
                plan_record = PlanDB(
                    id=f"plan-{uuid.uuid4().hex[:8]}",
                    trip_id=trip_id,
                    destination=trip.destination,
                    title=f"Common Ground Itinerary for {trip.destination}",
                    fairness_score=plan_json_dict.get("fairness", {}).get("fairness_score", 0.0),
                    plan_json=json.dumps(plan_json_dict)
                )
                db.add(plan_record)
            else:
                plan_record.plan_json = json.dumps(plan_json_dict)
                plan_record.fairness_score = plan_json_dict.get("fairness", {}).get("fairness_score", 0.0)

            trip.status = "done"
            db.commit()
            update_trip_progress(trip_id, "Plan ready!", 100, "done")
        except Exception as e:
            trip.status = "failed"
            db.commit()
            update_trip_progress(trip_id, f"Plan generation failed: {e}", 0, "failed")


@app.post("/trips/{id}/generate")
def generate_trip_plan(
    id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Runs generate_plan in a background task. Stream progress using SSE from GET /trips/{id}/progress."""
    trip = db.query(TripDB).filter_by(id=id).first()
    if not trip:
        raise HTTPException(status_code=404, detail=f"Trip '{id}' not found")

    profiles_db = db.query(ProfileDB).filter_by(trip_id=id).all()
    if not profiles_db:
        raise HTTPException(
            status_code=400,
            detail="Cannot generate plan: No friends have joined this trip yet. Add at least one profile first via POST /trips/{id}/profiles."
        )

    trip.status = "running"
    db.commit()

    update_trip_progress(id, "Initializing cultural intelligence pipeline...", 5, "running")
    background_tasks.add_task(_background_plan_runner, id)

    return {
        "status": "started",
        "trip_id": id,
        "message": f"Plan generation started in background for '{trip.title or trip.name}' ({len(profiles_db)} friends)",
        "progress_url": f"/trips/{id}/progress"
    }


@app.get("/trips/{id}/progress")
async def stream_trip_progress(id: str, db: Session = Depends(get_db)):
    """Server-Sent Events endpoint streaming real-time pipeline progress updates."""
    trip = db.query(TripDB).filter_by(id=id).first()
    if not trip:
        raise HTTPException(status_code=404, detail=f"Trip '{id}' not found")

    # If trip is already completed or failed, return immediate event
    if trip.status in ("done", "failed"):
        async def immediate_gen():
            msg = "Plan generation finished" if trip.status == "done" else "Plan generation failed"
            pct = 100 if trip.status == "done" else 0
            yield f"data: {json.dumps({'message': msg, 'percent': pct, 'status': trip.status})}\n\n"
        return StreamingResponse(immediate_gen(), media_type="text/event-stream")

    queue = asyncio.Queue()
    progress_queues.setdefault(id, []).append(queue)

    async def event_generator():
        if id in latest_trip_progress:
            yield f"data: {json.dumps(latest_trip_progress[id])}\n\n"
        try:
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=25.0)
                    yield f"data: {json.dumps(payload)}\n\n"
                    if payload.get("status") in ("done", "failed"):
                        break
                except asyncio.TimeoutError:
                    # Keep-alive heartbeat comment
                    yield f": keep-alive\n\n"
        finally:
            if id in progress_queues and queue in progress_queues[id]:
                progress_queues[id].remove(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/trips/{id}/plan")
def get_trip_plan(id: str, db: Session = Depends(get_db)):
    """Returns the saved plan JSON in exactly the shape of data/demo_plan.json."""
    trip = db.query(TripDB).filter_by(id=id).first()
    if not trip:
        raise HTTPException(status_code=404, detail=f"Trip '{id}' not found")

    plan_db = db.query(PlanDB).filter_by(trip_id=id).first()
    if not plan_db:
        if trip.status == "running":
            raise HTTPException(status_code=202, detail="Plan is currently being generated. Check progress at /trips/{id}/progress.")
        raise HTTPException(
            status_code=404,
            detail=f"Plan has not been generated yet for trip '{id}'. Call POST /trips/{id}/generate first."
        )

    try:
        return json.loads(plan_db.plan_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse stored plan: {e}")


# =====================================================================
# 5. Plan Rebalancing & Plain-LLM Comparison
# =====================================================================

@app.post("/trips/{id}/rebalance")
def rebalance_trip_plan(
    id: str,
    payload: RebalanceInput,
    db: Session = Depends(get_db)
):
    """Re-ranks using cached candidates (no new Qloo calls) and returns the new plan."""
    trip = db.query(TripDB).filter_by(id=id).first()
    if not trip:
        raise HTTPException(status_code=404, detail=f"Trip '{id}' not found")

    plan_db = db.query(PlanDB).filter_by(trip_id=id).first()
    if not plan_db:
        raise HTTPException(status_code=404, detail=f"No plan found for trip '{id}' to rebalance.")

    profiles_db = db.query(ProfileDB).filter_by(trip_id=id).all()
    profiles = [
        Profile(
            id=p.id,
            name=p.name,
            favorites=p.favorites,
            constraints=ProfileConstraints(**p.constraints)
        )
        for p in profiles_db
    ]

    current_plan = json.loads(plan_db.plan_json)
    updated_plan = rebalance_plan(
        current_plan=current_plan,
        profiles=profiles,
        adventurous=payload.adventurous,
        cultural=payload.cultural
    )

    # Persist updated plan in DB
    plan_db.plan_json = json.dumps(updated_plan)
    plan_db.fairness_score = updated_plan.get("fairness", {}).get("fairness_score", plan_db.fairness_score)
    db.commit()

    return updated_plan


@app.get("/trips/{id}/compare")
def compare_plans(id: str, db: Session = Depends(get_db)):
    """Compares plain-LLM itinerary (no Qloo) next to Common Ground plan with per-person scores."""
    trip = db.query(TripDB).filter_by(id=id).first()
    if not trip:
        raise HTTPException(status_code=404, detail=f"Trip '{id}' not found")

    plan_db = db.query(PlanDB).filter_by(trip_id=id).first()
    if not plan_db:
        raise HTTPException(status_code=404, detail=f"Plan has not been generated yet for trip '{id}'.")

    profiles_db = db.query(ProfileDB).filter_by(trip_id=id).all()
    profiles = [
        Profile(
            id=p.id,
            name=p.name,
            favorites=p.favorites,
            constraints=ProfileConstraints(**p.constraints)
        )
        for p in profiles_db
    ]

    trip_model = Trip(
        id=trip.id,
        title=trip.title or trip.name or f"Trip to {trip.destination}",
        destination=trip.destination,
        days=trip.days or 2,
        members=profiles
    )

    common_ground_plan = json.loads(plan_db.plan_json)
    comparison_result = generate_plain_llm_comparison(
        trip=trip_model,
        profiles=profiles,
        common_ground_plan=common_ground_plan
    )

    return comparison_result


# =====================================================================
# 6. Developer Demo Prefill Helper
# =====================================================================

@app.post("/dev/demo-trip")
def create_demo_trip(db: Session = Depends(get_db)):
    """Creates a trip prefilled with the 4 demo friends (Aisha, Rohan, Meera, Kabir) for testing."""
    from backend.run_group_demo import get_demo_group

    trip_id = f"trip-demo-{uuid.uuid4().hex[:6]}"
    trip = TripDB(
        id=trip_id,
        title="Lisbon 4-Friend Culture Demo",
        name="Lisbon 4-Friend Culture Demo",
        destination="Lisbon",
        days=2,
        status="waiting"
    )
    db.add(trip)

    demo_profiles, favs_with_hints = get_demo_group()
    members_saved = []

    for p in demo_profiles:
        hints = favs_with_hints.get(p.name, [])
        fav_list = [{"name": h[0], "type": h[1]} for h in hints]
        prof_id = f"prof-{uuid.uuid4().hex[:6]}"
        prof_db = ProfileDB(
            id=prof_id,
            trip_id=trip_id,
            name=p.name,
            favorites_json=json.dumps(fav_list),
            constraints_json=json.dumps(p.constraints.model_dump())
        )
        db.add(prof_db)
        members_saved.append({
            "id": prof_id,
            "name": p.name,
            "favorites": fav_list,
            "constraints": p.constraints.model_dump()
        })

    db.commit()

    return {
        "trip_id": trip_id,
        "name": trip.title,
        "destination": trip.destination,
        "days": 2,
        "status": "waiting",
        "members": members_saved,
        "message": "Demo trip prefilled with 4 friends successfully"
    }


# =====================================================================
# 7. Legacy Debug Logs Endpoint
# =====================================================================

@app.get("/api/logs")
def get_recent_qloo_logs(limit: int = 20):
    """Retrieves recent raw Qloo requests/responses from data/qloo_log.jsonl for debugging."""
    if not LOG_FILE_PATH.exists():
        return {"logs": []}

    try:
        lines = []
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    lines.append(json.loads(line))
        return {"logs": lines[-limit:]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read logs: {e}")
