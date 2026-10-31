"""Qloo API Client for Common Ground.

ALL Qloo calls live here only.
Provides search_entity and get_recommendations functions with:
- Live mode (DEFAULT target when QLOO_API_KEY is present) targeting https://hackathon.api.qloo.com.
- Mock mode (when QLOO_MOCK=true or explicit fallback) with realistic offline data for Lisbon, Tokyo, and Delhi.
- Single unified parsing layer (parse_raw_candidate) mapping raw Qloo JSON into Candidate models.
- Location-aware querying: passes the requested city to Qloo without hardcoding or defaulting to Lisbon.
- SQLite response caching to prevent duplicate API calls and save quota.
- Automatic retries with exponential backoff on HTTP 429 and 5xx.
- Clear, distinct error handling for:
  * Missing API key (QlooMissingApiKeyError)
  * Invalid API key (QlooAuthError on 401/403)
  * Request failures (QlooRequestError)
  * Timeout & network failures (QlooNetworkError)
  * Empty candidate sets for a city (QlooNoCandidatesError)
  * Unsupported mock cities (QlooCityNotFoundError)
- Raw request/response logging to data/qloo_log.jsonl with API keys strictly scrubbed.
"""

import os
import re
import time
import json
import hashlib
import threading
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Callable

import httpx
from dotenv import load_dotenv

from backend.models import Candidate
from backend.mock_data import MOCK_CITIES_DATA, MOCK_SEARCH_ENTITIES, calculate_mock_affinity
from backend.db import SessionLocal, QlooCacheDB

# Load environment configuration from .env if present
load_dotenv()

# Audit log file path
LOG_FILE_PATH = Path("./data/qloo_log.jsonl")
# Qloo calls may run on several threads; one writer at a time keeps every log line intact
_LOG_LOCK = threading.Lock()


# =====================================================================
# Configuration Helpers (Dynamic & Environment-Driven)
# =====================================================================

def get_qloo_base_url() -> str:
    """Returns the Qloo API base URL from env var QLOO_BASE_URL (never hardcoded)."""
    return os.getenv("QLOO_BASE_URL", "https://hackathon.api.qloo.com").rstrip("/")


def get_qloo_api_key() -> str:
    """Returns the Qloo API key from env var QLOO_API_KEY (never hardcoded), stripped of quotes."""
    load_dotenv()
    raw_key = os.getenv("QLOO_API_KEY", "")
    return raw_key.strip("\"' \t\n")


def is_qloo_mock_mode() -> bool:
    """Determines whether the client should operate in Mock mode or Live mode.

    Rules:
    - If QLOO_MOCK is explicitly 'true' -> Mock mode.
    - If QLOO_MOCK is 'false' -> Live mode.
    - If QLOO_MOCK is unset:
        * If QLOO_API_KEY is present -> Live mode (Default target).
        * If QLOO_API_KEY is missing -> Mock mode.
    """
    load_dotenv()
    mock_env = os.getenv("QLOO_MOCK", "").lower().strip()
    if mock_env in ("true", "1", "yes"):
        return True
    if mock_env in ("false", "0", "no"):
        return False
    # Default: Live mode if API key exists, otherwise offline mock
    return not bool(get_qloo_api_key())


# Backwards-compatible module-level constants
QLOO_BASE_URL = get_qloo_base_url()
QLOO_API_KEY = get_qloo_api_key()
QLOO_MOCK_ENV = is_qloo_mock_mode()


# =====================================================================
# Custom Exceptions for Clear Diagnostic Error Handling
# =====================================================================

class QlooError(Exception):
    """Base exception for all Qloo client operations."""
    pass


class QlooMissingApiKeyError(QlooError):
    """Raised when live mode is requested but QLOO_API_KEY is not set."""
    pass


class QlooAuthError(QlooError):
    """Raised when authentication fails (HTTP 401 or 403)."""
    pass


class QlooRateLimitError(QlooError):
    """Raised when rate limits are exceeded (HTTP 429) after retries."""
    pass


class QlooServerError(QlooError):
    """Raised when the Qloo API returns 5xx server errors after retries."""
    pass


class QlooRequestError(QlooError):
    """Raised when a Qloo API request fails with an unhandled status code."""
    pass


class QlooNetworkError(QlooError):
    """Raised when network connectivity fails or a request times out."""
    pass


class QlooNoCandidatesError(QlooError):
    """Raised when Qloo returns 0 candidates for a given city and category."""
    pass


class QlooCityNotFoundError(QlooError):
    """Raised in mock mode when a requested city is not in the offline catalog."""
    pass


class QlooNoSignalsResolvedError(QlooError):
    """Raised when none of the provided favorites could be resolved to known entities in Qloo."""
    pass


# =====================================================================
# Logging & SQLite Caching (API Keys Strictly Scrubbed)
# =====================================================================

def _log_interaction(
    method: str,
    endpoint: str,
    params: Dict[str, Any],
    status_code: Optional[int],
    response_body: Any,
    from_cache: bool = False,
    error_message: Optional[str] = None
) -> None:
    """Logs raw request/response metadata to data/qloo_log.jsonl.

    Ensures API keys are never exposed in logs.
    """
    try:
        LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        # Deep scrub parameters to guarantee no API keys are logged
        scrubbed_params = {}
        for k, v in params.items():
            if "key" in k.lower() or "token" in k.lower() or "secret" in k.lower():
                scrubbed_params[k] = "[REDACTED]"
            else:
                scrubbed_params[k] = v

        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method": method,
            "endpoint": endpoint,
            "params": scrubbed_params,
            "status_code": status_code,
            "cached": from_cache,
            "response": response_body,
            "error": error_message
        }
        line = json.dumps(log_entry, default=str) + "\n"
        with _LOG_LOCK:
            with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
                f.write(line)
    except Exception as e:
        print(f"[Warning] Failed to write to qloo_log.jsonl: {e}")


def count_qloo_log_calls() -> Dict[str, int]:
    """Inspects data/qloo_log.jsonl to count total Qloo requests and cache hits."""
    if not LOG_FILE_PATH.exists():
        return {"total": 0, "live": 0, "cache": 0}

    total = 0
    live = 0
    cache = 0
    try:
        with open(LOG_FILE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    entry = json.loads(line_str)
                    total += 1
                    if entry.get("cached") is True or entry.get("from_cache") is True:
                        cache += 1
                    else:
                        live += 1
                except Exception:
                    continue
    except Exception:
        pass

    return {"total": total, "live": live, "cache": cache}


def _get_cache(cache_key: str) -> Optional[Dict[str, Any]]:
    """Retrieves a cached JSON response from the local SQLite cache."""
    try:
        with SessionLocal() as session:
            record = session.query(QlooCacheDB).filter_by(cache_key=cache_key).first()
            if record:
                return json.loads(record.response_body)
    except Exception:
        return None
    return None


def _set_cache(cache_key: str, endpoint: str, params: Dict[str, Any], response_data: Any) -> None:
    """Stores a successful API response into the local SQLite cache."""
    try:
        with SessionLocal() as session:
            record = session.query(QlooCacheDB).filter_by(cache_key=cache_key).first()
            if not record:
                record = QlooCacheDB(
                    cache_key=cache_key,
                    endpoint=endpoint,
                    request_params=json.dumps(params, sort_keys=True),
                    response_body=json.dumps(response_data),
                    created_at=datetime.now(timezone.utc)
                )
                session.add(record)
            else:
                record.response_body = json.dumps(response_data)
                record.created_at = datetime.now(timezone.utc)
            session.commit()
    except Exception as e:
        print(f"[Warning] Could not write to SQLite cache: {e}")


# =====================================================================
# Low-Level HTTP Request Dispatcher
# =====================================================================

def _make_request(
    method: str,
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    max_retries: int = 3,
    backoff_factor: float = 0.5,
    transform: Optional[Callable[[Any], Any]] = None,
    timeout: float = 30.0
) -> Dict[str, Any]:
    """Executes a real HTTP request to the Qloo API with caching, retries, and error handling.

    - Verifies QLOO_API_KEY is present.
    - Uses SHA-256 caching in SQLite.
    - Retries on HTTP 429 and 5xx with exponential backoff.
    - Raises actionable exceptions on 401/403, timeouts, or connection failures.
    - Never prints or exposes the API key.
    - Optional `transform` slims the response before it is cached, logged, and returned.
    """
    api_key = get_qloo_api_key()
    if not api_key:
        raise QlooMissingApiKeyError(
            "QLOO_API_KEY environment variable is missing or empty.\n"
            "To use the LIVE Qloo API, please set QLOO_API_KEY in your .env file or terminal:\n"
            "  export QLOO_API_KEY=\"your_key_here\"\n"
            "Alternatively, run offline by setting QLOO_MOCK=true."
        )

    base_url = get_qloo_base_url()
    clean_params = params or {}
    url = f"{base_url}{endpoint}"

    # Generate deterministic cache key based on endpoint and query parameters
    param_fingerprint = json.dumps(clean_params, sort_keys=True)
    cache_key = hashlib.sha256(f"{endpoint}:{param_fingerprint}".encode("utf-8")).hexdigest()

    # 1. Check SQLite Cache
    cached_data = _get_cache(cache_key)
    if cached_data is not None:
        _log_interaction(
            method=method,
            endpoint=endpoint,
            params=clean_params,
            status_code=200,
            response_body=cached_data,
            from_cache=True
        )
        return cached_data

    # 2. Authentication header (API key passed securely, never printed)
    headers = {
        "X-Api-Key": api_key,
        "Accept": "application/json"
    }

    # 3. Request loop with exponential backoff
    last_exception = None
    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=timeout) as client:
                if method.upper() == "GET":
                    response = client.get(url, headers=headers, params=clean_params)
                else:
                    response = client.post(url, headers=headers, json=clean_params)

                status = response.status_code

                # Surface clear, immediate errors for authentication issues (no retry)
                if status in (401, 403):
                    msg = (
                        f"Qloo Authentication Failed (HTTP {status}).\n"
                        "The QLOO_API_KEY provided is invalid, expired, or unauthorized.\n"
                        "Please verify your API key in .env or your terminal environment."
                    )
                    _log_interaction(method, endpoint, clean_params, status, response.text, False, msg)
                    raise QlooAuthError(msg)

                # Retry on Rate Limit (429) or Server Errors (5xx)
                if status == 429 or status >= 500:
                    wait_time = backoff_factor * (2 ** attempt)
                    msg = f"HTTP {status} from Qloo. Retrying in {wait_time:.1f}s (Attempt {attempt+1}/{max_retries})..."
                    _log_interaction(method, endpoint, clean_params, status, response.text, False, msg)
                    time.sleep(wait_time)
                    continue

                if status >= 400:
                    err_msg = f"Qloo API returned HTTP {status}: {response.text[:300]}"
                    _log_interaction(method, endpoint, clean_params, status, response.text, False, err_msg)
                    raise QlooRequestError(err_msg)

                # Successful response
                data = response.json()
                if transform is not None:
                    data = transform(data)

                # Cache successful response and log
                _set_cache(cache_key, endpoint, clean_params, data)
                _log_interaction(method, endpoint, clean_params, status, data, False)
                return data

        except (httpx.ConnectError, httpx.TimeoutException) as conn_err:
            last_exception = conn_err
            wait_time = backoff_factor * (2 ** attempt)
            time.sleep(wait_time)
        except (QlooAuthError, QlooRequestError, QlooError):
            raise
        except Exception as general_err:
            last_exception = general_err
            break

    # If retries exhausted due to connection or timeout
    err_text = (
        f"Failed to connect to Qloo API at {url} after {max_retries} attempts: {last_exception}.\n"
        "Please check your internet connection or verify that QLOO_BASE_URL is reachable."
    )
    _log_interaction(method, endpoint, clean_params, None, None, False, err_text)
    raise QlooNetworkError(err_text)


# =====================================================================
# Parsing Layer: Maps raw Qloo API JSON into our internal Candidate model
# =====================================================================

def parse_raw_candidate(raw: Dict[str, Any], category: str, location: str) -> Candidate:
    """Parses a single raw entity/venue dictionary from Qloo into our Candidate model.

    Handles real Qloo API payloads from /v2/insights and /v2/search defensively:
    - Never crashes on missing, None, or unexpected fields (e.g., None neighborhood).
    - Uses safe defaults for missing tags, price, location, or description.
    """
    if not isinstance(raw, dict):
        return Candidate(
            id=f"qloo-unknown-{abs(hash(str(raw)))}",
            name="Curated Venue",
            category=category,
            location=location,
            qloo_affinity=0.5,
            tags=[],
            price_level="$$",
            description=f"Curated cultural venue in {location}",
            address=None,
            image_url=None
        )

    props = raw.get("properties")
    if not isinstance(props, dict):
        props = {}

    # 1. ID extraction (ensuring live URNs or UUID entity_ids are preserved)
    cand_id = (
        raw.get("entity_id") or
        raw.get("id") or
        raw.get("urn") or
        props.get("id") or
        f"qloo-{abs(hash(str(raw)))}"
    )

    # 2. Name extraction
    name = (
        raw.get("name") or
        raw.get("title") or
        props.get("name") or
        props.get("title") or
        "Curated Venue"
    )

    # 3. Affinity score extraction (handles float, int, percentage, or nested dicts)
    score_val = raw.get("score")
    if score_val is None:
        aff = raw.get("affinity")
        if isinstance(aff, dict):
            score_val = aff.get("score") or aff.get("value")
        elif isinstance(aff, (int, float, str)):
            score_val = aff

    if score_val is None:
        # Live /v2/insights returns affinity at query.affinity
        query_block = raw.get("query")
        if isinstance(query_block, dict):
            score_val = query_block.get("affinity")
            m_dict = query_block.get("measurements")
            if score_val is None and isinstance(m_dict, dict):
                score_val = m_dict.get("affinity")

    if score_val is None:
        score_val = raw.get("qloo_affinity")

    # Never invent an affinity: missing values are 0.0 and flagged as such
    affinity_source = "qloo"
    try:
        affinity = float(score_val)
        if affinity > 1.0:
            affinity = round(affinity / 100.0, 2)
        else:
            affinity = round(affinity, 2)
    except Exception:
        affinity = 0.0
        affinity_source = "missing"

    # 4. Tags & Keywords extraction from properties
    raw_tags = props.get("tags") or raw.get("tags") or []
    raw_keywords = props.get("keywords") or []

    tags: List[str] = []
    if isinstance(raw_tags, list):
        for t in raw_tags:
            if isinstance(t, dict):
                t_name = t.get("name") or t.get("id") or ""
                if t_name and str(t_name).strip():
                    tags.append(str(t_name).strip().lower())
            elif isinstance(t, str) and t.strip():
                tags.append(t.strip().lower())

    if isinstance(raw_keywords, list):
        for k in raw_keywords:
            if isinstance(k, dict):
                k_name = k.get("name") or ""
                if k_name and str(k_name).strip():
                    tags.append(str(k_name).strip().lower())
            elif isinstance(k, str) and k.strip():
                tags.append(k.strip().lower())

    unique_tags = list(dict.fromkeys(tags))[:10]

    # 5. Price level extraction (defaults safely to "$$")
    price_raw = props.get("price_level") or raw.get("price_level") or props.get("price") or raw.get("price")
    price_verified = bool(price_raw)  # hotels and sights usually carry no price in Qloo
    price_raw = price_raw or "$$"
    price_scale = {1: "$", 2: "$$", 3: "$$$", 4: "$$$$"}
    if isinstance(price_raw, int) and price_raw in price_scale:
        price_level = price_scale[price_raw]
    elif isinstance(price_raw, str) and price_raw.strip():
        price_level = price_raw.strip()
    else:
        price_level = "$$"

    # 6. Location / Address extraction (tolerant of None fields)
    address = props.get("address") or raw.get("address")
    raw_loc = raw.get("location")
    cand_location = location

    # If geocode or locality is present, extract neighborhood/city safely
    locality = props.get("locality")
    if isinstance(locality, dict):
        neigh_obj = locality.get("neighborhood")
        if isinstance(neigh_obj, dict):
            neigh_name = neigh_obj.get("name")
            if neigh_name and str(neigh_name).strip():
                cand_location = f"{location}, {str(neigh_name).strip()}"
        elif isinstance(neigh_obj, str) and neigh_obj.strip():
            cand_location = f"{location}, {neigh_obj.strip()}"

    if cand_location == location and isinstance(raw_loc, str) and raw_loc.strip():
        cand_location = raw_loc.strip()

    # 7. Images & Description
    images = props.get("images") or raw.get("images") or []
    image_url = None
    if isinstance(images, list) and images:
        first_img = images[0]
        if isinstance(first_img, dict):
            image_url = first_img.get("url")
        elif isinstance(first_img, str) and first_img.strip():
            image_url = first_img.strip()
    elif isinstance(images, dict):
        image_url = images.get("url")

    raw_desc = props.get("description") or raw.get("description") or props.get("website") or address
    description = str(raw_desc).strip() if raw_desc else f"Curated cultural venue in {location}"

    # 8. Real Qloo metadata: genre identity, popularity, coordinates, neighborhood
    primary_genre, genre_ids = extract_place_genres(raw)

    geocode = props.get("geocode") if isinstance(props.get("geocode"), dict) else {}
    area = geocode.get("name") or geocode.get("city")
    if cand_location == location and isinstance(area, str) and area.strip() and area.strip().lower() not in location.lower():
        cand_location = f"{location}, {area.strip()}"

    lat = lon = None
    if isinstance(raw_loc, dict):
        try:
            lat, lon = float(raw_loc.get("lat")), float(raw_loc.get("lon"))
        except (TypeError, ValueError):
            lat = lon = None

    popularity = raw.get("popularity")
    popularity = float(popularity) if isinstance(popularity, (int, float)) else None

    return Candidate(
        id=str(cand_id),
        name=str(name).strip(),
        category=category,
        location=cand_location,
        qloo_affinity=affinity,
        tags=unique_tags,
        price_level=price_level,
        description=description,
        address=str(address).strip() if address else None,
        image_url=str(image_url).strip() if image_url else None,
        latitude=lat,
        longitude=lon,
        primary_genre=primary_genre,
        qloo_genres=genre_ids,
        popularity=popularity,
        affinity_source=affinity_source,
        price_verified=price_verified
    )


def extract_place_genres(raw: Dict[str, Any]) -> Tuple[Optional[str], List[str]]:
    """Returns (primary_genre_id, [genre/category tag IDs in Qloo order]) from a raw place payload."""
    props = raw.get("properties") if isinstance(raw.get("properties"), dict) else {}
    primary = props.get("primary_genre")
    primary_id = primary.get("id") if isinstance(primary, dict) else (primary if isinstance(primary, str) else None)

    genre_ids: List[str] = []
    for t in raw.get("tags") or []:
        if not isinstance(t, dict):
            continue
        tid = str(t.get("id") or "")
        if t.get("type") in ("urn:tag:genre:place", "urn:tag:category:place") or tid.startswith(("urn:tag:genre:place:", "urn:tag:category:place:")):
            if tid and tid not in genre_ids:
                genre_ids.append(tid)
    return primary_id, genre_ids


# =====================================================================
# Public Client Functions
# =====================================================================

def search_entity(name: str, force_mock: Optional[bool] = None) -> List[Dict[str, Any]]:
    """Searches for cultural entities (artists, brands, cuisines, places) by name.

    Args:
        name: Name of the entity to search for (e.g. 'Burial', 'Aesop').
        force_mock: Optional override to force mock mode.

    Returns:
        List of matching entity dictionaries containing id, name, type, and tags.
    """
    use_mock = force_mock if force_mock is not None else is_qloo_mock_mode()

    if use_mock:
        query_norm = name.strip().lower()
        results = [
            entity for entity in MOCK_SEARCH_ENTITIES
            if query_norm in entity["name"].lower() or any(query_norm in tag for tag in entity["tags"])
        ]
        # No match means unresolved; never substitute unrelated catalog entities
        results_to_return = results
        _log_interaction(
            method="MOCK_GET",
            endpoint="/search",
            params={"query": name},
            status_code=200,
            response_body=results_to_return,
            from_cache=False
        )
        return results_to_return

    # REAL MODE: Live Qloo API call (/v2/search per Qloo Hackathon developer guide)
    endpoint = "/v2/search"
    params = {"query": name}
    data = _make_request("GET", endpoint, params=params)

    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        return data.get("results") or data.get("entities") or data.get("data") or [data]
    return []


def _slim_locality(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Reduces a raw Qloo locality entity to the fields needed for destination autocomplete.

    Raw locality payloads include boundary polygons and dozens of travel-stat fields
    (often >300KB per result), so they are never cached or logged in full.
    """
    if not isinstance(item, dict):
        return None
    props = item.get("properties") if isinstance(item.get("properties"), dict) else {}
    eid = item.get("entity_id") or item.get("id")
    name = str(item.get("name") or props.get("name") or "").strip()
    if not eid or not name:
        return None

    label = str(item.get("disambiguation") or name).strip()
    ancestors = props.get("ancestors") if isinstance(props.get("ancestors"), list) else []
    country = next(
        (a.get("name") for a in ancestors if isinstance(a, dict) and a.get("place") == "country" and a.get("name")),
        None
    )
    if not country and "," in label:
        country = label.rsplit(",", 1)[-1].strip()

    return {
        "id": str(eid),
        "name": name,
        "label": label,
        # Qloo resolves the full disambiguated label to the exact locality the user picked
        "query": label,
        "country": country,
        "description": props.get("short_description"),
        "popularity": item.get("popularity"),
    }


def _slim_locality_response(data: Any) -> Dict[str, Any]:
    raw = data.get("results") if isinstance(data, dict) else data
    results = []
    seen_labels = set()
    for item in raw if isinstance(raw, list) else []:
        slim = _slim_locality(item)
        if slim and slim["label"].lower() not in seen_labels:
            seen_labels.add(slim["label"].lower())
            results.append(slim)
    return {"results": results}


def search_destinations(query: str, limit: int = 8, force_mock: Optional[bool] = None) -> List[Dict[str, Any]]:
    """Searches Qloo for real destination localities (cities, regions, countries) by name.

    In mock mode only the offline catalog cities are returned, since those are the only
    destinations the offline planner can generate itineraries for.
    """
    query_norm = " ".join(query.strip().lower().split())
    if not query_norm:
        return []

    use_mock = force_mock if force_mock is not None else is_qloo_mock_mode()
    if use_mock:
        return [
            {
                "id": f"mock-{city}",
                "name": city.title(),
                "label": f"{city.title()} (offline catalog)",
                "query": city.title(),
                "country": None,
                "description": None,
                "popularity": None,
            }
            for city in MOCK_CITIES_DATA.keys()
            if query_norm in city
        ][:limit]

    # One fixed-size request per normalized query keeps the SQLite cache key stable across limits
    data = _make_request(
        "GET",
        "/v2/search",
        params={"query": query_norm, "types": "urn:entity:locality", "take": 15},
        transform=_slim_locality_response
    )
    results = (data.get("results") if isinstance(data, dict) else None) or []

    # Qloo ranks sub-areas (wards, parishes) highly; surface exact and prefix name matches first
    def rank(item: Dict[str, Any]) -> int:
        name = item["name"].lower()
        if name == query_norm:
            return 0
        if name.startswith(query_norm):
            return 1
        return 2

    return sorted(results, key=rank)[:limit]


TYPE_HINT_MAP = {
    "artist": ["urn:entity:artist", "urn:entity:person", "artist", "person"],
    "movie": ["urn:entity:movie", "movie"],
    "tv_show": ["urn:entity:tv_show", "tv_show", "tv"],
    "brand": ["urn:entity:brand", "brand"],
    "place": ["urn:entity:place", "place"],
    "book": ["urn:entity:book", "book", "author"]
}


def is_type_match(actual_type: str, type_hint: Optional[str]) -> bool:
    """Checks whether an actual Qloo entity type matches a user type hint."""
    if not type_hint:
        return True
    hint_clean = type_hint.strip().lower()
    allowed = TYPE_HINT_MAP.get(hint_clean, [hint_clean])
    actual_clean = (actual_type or "").lower()
    return any(a in actual_clean for a in allowed)


# Ordered (term, category) rules matched against Qloo place genre/category tag IDs.
# A term containing "_" matches as a substring of the tag path; a plain word must be a whole token.
# First match wins, so lodging and explicit exclusions are checked before broader categories.
# A category of None means "not a travel stop" (excluded).
_GENRE_RULES: List[Tuple[str, Optional[str]]] = [
    # Lodging: only ever recommended as the stay, never scheduled as an activity
    *[(t, "hotel") for t in (
        "hotel", "hostel", "motel", "inn", "lodge", "resort", "pousada", "ryokan", "aparthotel",
        "bed_breakfast", "guest_house", "guesthouse", "serviced_accommodation", "holiday_apartment",
        "self_catering", "furnished_apartment", "country_house", "accommodation", "campground",
        "vacation_rental", "farmstay", "chalet",
    )],
    # Experiences whose tag would otherwise hit an exclusion (e.g. "school", "club")
    *[(t, "attraction") for t in ("surf_school", "cooking_class", "dive_center", "tour_operator")],
    *[(t, "bar") for t in ("disco_club", "dance_club", "jazz_club", "comedy_club")],
    # Everyday services and businesses that are not travel stops
    *[(t, None) for t in (
        "personal_care", "barber", "beauty", "hair", "nail", "salon", "tattoo", "gym", "fitness",
        "crossfit", "training_centre", "training_center", "yoga_studio", "yoga_retreat", "pilates",
        "bank", "atm", "insurance", "government", "office", "embassy", "consulate", "police",
        "post_office", "courthouse", "school", "college", "university", "kindergarten", "daycare",
        "hospital", "clinic", "medical", "dental", "dentist", "doctor", "pharmacy", "drugstore",
        "veterinar", "laboratory", "real_estate", "lawyer", "attorney", "accountant", "notary",
        "event_venue", "event_management", "wedding", "banquet_hall", "party", "conference",
        "coworking", "corporate", "car_", "auto_", "gas_station", "parking", "storage", "laundry",
        "dry_clean", "repair", "funeral", "supermarket", "grocery", "convenience_store", "hardware",
        "fish_store", "butcher", "tobacco", "mobile_phone", "electronics", "nutrition", "furniture",
        "apartment_building", "residential", "association", "union", "warehouse", "factory",
        "industrial", "wholesale", "printing", "telecom", "employment", "ballroom", "country_club",
        "sports_club", "golf_club", "wellness", "decoration",
    )],
    # Cafes before bars/restaurants: Qloo nests them as e.g. urn:tag:genre:place:restaurant:cafe
    *[(t, "cafe") for t in (
        "coffee_shop", "coffee_store", "coffee", "cafe", "cafeteria", "bakery", "cake_shop", "pastry",
        "patisserie", "confectionery", "dessert", "ice_cream", "gelato", "tea_house", "juice", "brunch",
        "breakfast", "chocolate", "creperie", "snack_bar", "espresso",
    )],
    ("tapas_bar", "restaurant"),
    ("sushi_bar", "restaurant"),
    *[(t, "bar") for t in (
        "bar", "pub", "night_club", "nightclub", "cocktail", "brewery", "brewpub", "lounge",
        "live_music_venue", "jazz_club", "karaoke", "beer_garden", "speakeasy", "izakaya",
    )],
    *[(t, "restaurant") for t in (
        "restaurant", "food_court", "steakhouse", "pizzeria", "bistro", "diner", "eatery", "taqueria",
        "brasserie", "trattoria", "ramen", "sushi", "fado", "churrascaria", "tavern", "food_hall",
    )],
    *[(t, "attraction") for t in (
        "tourist_attraction", "museum", "gallery", "landmark", "historical", "monument", "memorial",
        "castle", "palace", "fortress", "fort", "ruins", "archaeological", "church", "cathedral",
        "basilica", "chapel", "temple", "shrine", "mosque", "synagogue", "monastery", "convent",
        "abbey", "park", "garden", "botanical", "scenic_spot", "viewpoint", "observation_deck",
        "beach", "hiking_area", "trail", "nature_reserve", "national_park", "waterfall", "lake",
        "zoo", "aquarium", "theme_park", "amusement_park", "theater", "theatre", "opera",
        "concert_hall", "cultural_center", "arts_center", "library", "plaza", "square", "market",
        "winery", "vineyard", "wine_cellar", "stadium", "cemetery", "bridge", "tower", "lighthouse",
        "cinema", "movie_theater", "pier", "harbor", "promenade", "planetarium", "observatory",
        "heritage", "mountain", "peak", "exhibit", "exhibition", "hanok", "art_center",
    )],
    *[(t, "shop") for t in (
        "shopping", "mall", "store", "shop", "boutique", "book_store", "bookstore", "department_store",
        "gift", "souvenir", "antique", "record", "clothing", "concept_store", "craft", "design",
        "jewelry", "flea_market",
    )],
]

# Generic whole-word keywords for venues without Qloo genre metadata (offline data, sparse payloads).
# Order mirrors _GENRE_RULES: lodging, exclusions, then specific to broad categories.
_NAME_KEYWORD_RULES: List[Tuple[Optional[str], Tuple[str, ...]]] = [
    ("hotel", ("hotel", "hostel", "motel", "inn", "lodge", "resort", "pousada", "guesthouse",
               "guest house", "apartments", "suites", "b&b", "hospedaria")),
    (None, ("barber", "barbearia", "barbershop", "salon", "salão", "hair", "beauty", "gym", "fitness",
            "crossfit", "bank", "banco", "clinic", "clínica", "hospital", "dental", "pharmacy",
            "farmácia", "school", "escola", "colégio", "office", "government", "insurance")),
    ("cafe", ("cafe", "café", "coffee", "bakery", "padaria", "pastelaria", "confeitaria",
              "patisserie", "tea room", "teahouse")),
    ("bar", ("bar", "pub", "lounge", "nightclub", "cocktail", "cocktails", "brewery", "wine bar")),
    ("restaurant", ("restaurant", "restaurante", "ristorante", "taberna", "tasca", "bistro",
                    "trattoria", "cozinha", "churrascaria", "pizzeria", "grill", "steakhouse")),
    ("attraction", ("museum", "museu", "museo", "gallery", "galeria", "park", "parque", "garden",
                    "jardim", "church", "igreja", "cathedral", "castle", "castelo", "palace",
                    "palácio", "monument", "viewpoint", "miradouro", "beach", "praia", "temple",
                    "market", "mercado")),
    ("shop", ("shop", "store", "loja", "bookstore", "livraria", "boutique")),
]

_VALID_CATEGORIES = {"hotel", "restaurant", "cafe", "bar", "attraction", "shop"}

# Secondary tags that disqualify a venue whose primary genre we don't recognise
_HARD_EXCLUSION_TERMS = (
    "clinic", "dental", "dentist", "hospital", "medical", "doctor", "pharmacy", "barber", "beauty",
    "hair", "salon", "personal_care", "bank", "government", "school", "gym", "fitness",
)

# Too loosely applied by Qloo to identify a venue on its own when the primary genre is unknown
_WEAK_SECONDARY_TAGS = ("tourist_attraction",)


def _genre_path(tag_id: str) -> str:
    """Strips the 'urn:tag:genre:place:' / 'urn:tag:category:place:' prefix from a Qloo tag ID."""
    tag = str(tag_id or "").lower()
    for prefix in ("urn:tag:genre:place:", "urn:tag:category:place:"):
        if tag.startswith(prefix):
            # Normalize symbols so e.g. 'bed_&_breakfast' matches 'bed_breakfast'
            return re.sub(r"_+", "_", re.sub(r"[^a-z0-9:_]", "", tag[len(prefix):])).strip("_")
    return ""


def classify_genre_tag(tag_id: str) -> Tuple[bool, Optional[str]]:
    """Maps one Qloo place genre/category tag ID to a travel category.

    Returns (matched, category). category is None for excluded non-travel businesses;
    matched is False when the tag says nothing useful (e.g. the generic 'urn:tag:genre:place').
    """
    path = _genre_path(tag_id)
    if not path:
        return False, None
    tokens = set(re.split(r"[:_]", path))
    for term, category in _GENRE_RULES:
        hit = (term in path) if "_" in term else (term in tokens)
        if hit:
            return True, category
    return False, None


def _classify_by_keywords(text: str) -> Tuple[Optional[str], str]:
    words = " " + re.sub(r"[^\w&]+", " ", text.lower()) + " "
    for category, keywords in _NAME_KEYWORD_RULES:
        if any(f" {kw} " in words for kw in keywords):
            if category is None:
                return None, "Excluded non-travel business (name keywords)"
            return category, "Classified from name keywords (no Qloo genre metadata)"
    return None, "Ambiguous venue without Qloo genre metadata"


def classify_place(
    name: str,
    description: str = "",
    primary_genre: Optional[str] = None,
    genre_ids: Optional[List[str]] = None,
    raw_category: Optional[str] = None
) -> Tuple[Optional[str], str]:
    """Assigns exactly one travel category to a place, or None to drop it.

    Priority:
    1. Any lodging tag, primary or secondary: accommodation is never scheduled as an activity
       (e.g. an inn whose primary genre is 'restaurant').
    2. Qloo's primary_genre (the venue's main identity).
    3. The first recognised Qloo genre/category tag, in Qloo's own order.
    4. An explicit category field on the payload.
    5. Whole-word name keywords, for payloads without any Qloo genre metadata.
    """
    tag_results = [(tid, classify_genre_tag(tid)) for tid in (genre_ids or [])]
    tag_results = [(tid, cat) for tid, (matched, cat) in tag_results if matched]
    primary_matched, primary_category = classify_genre_tag(primary_genre) if primary_genre else (False, None)

    if primary_category == "hotel" or any(cat == "hotel" for _, cat in tag_results):
        return "hotel", "Qloo lodging genre"

    if primary_matched:
        label = _genre_path(primary_genre)
        return primary_category, (f"Qloo primary genre '{label}'" if primary_category else f"Excluded: Qloo primary genre '{label}'")

    if primary_genre:
        # Unrecognised primary genre (e.g. 'wellness_center'): only trust specific, clean secondary tags
        hard = [tid for tid in (genre_ids or []) if any(term in _genre_path(tid) for term in _HARD_EXCLUSION_TERMS)]
        if hard:
            return None, f"Excluded: Qloo genre tag '{_genre_path(hard[0])}'"
        tag_results = [(tid, cat) for tid, cat in tag_results if _genre_path(tid) not in _WEAK_SECONDARY_TAGS]
        if not any(cat for _, cat in tag_results):
            return None, f"Ambiguous: unrecognised Qloo primary genre '{_genre_path(primary_genre)}'"

    positives = [(tid, cat) for tid, cat in tag_results if cat]
    if positives:
        return positives[0][1], f"Qloo genre tag '{_genre_path(positives[0][0])}'"
    if tag_results:
        return None, f"Excluded: Qloo genre tag '{_genre_path(tag_results[0][0])}'"

    rcat = str(raw_category or "").strip().lower()
    if rcat in _VALID_CATEGORIES:
        return rcat, "Category field on payload"

    return _classify_by_keywords(f"{name} {description}")


def score_search_candidate(item: Dict[str, Any], query: str, type_hint: Optional[str] = None) -> float:
    """Scores a search candidate prioritizing exact name match and specified type hint."""
    q_norm = query.strip().lower()
    name = str(item.get("name") or item.get("title") or "").strip().lower()
    subtype = str(item.get("subtype") or "").lower()
    type_ = str(item.get("type") or "").lower()
    full_type = f"{subtype} {type_}"

    score = 0.0

    # 1. Name match precision
    if name == q_norm:
        score += 100.0
    elif name.startswith(q_norm):
        score += 60.0
    elif q_norm in name:
        score += 40.0
    else:
        score += 5.0

    # 2. Type hint matching
    if type_hint:
        if is_type_match(full_type, type_hint):
            score += 150.0
        else:
            score -= 50.0
    else:
        # Default priority: creator/artist entities
        if "artist" in full_type or "person" in full_type:
            score += 50.0
        elif "brand" in full_type:
            score += 30.0

    # 3. Penalize random places when searching cultural favorites
    if ("place" in full_type) and (type_hint != "place"):
        score -= 40.0

    # 4. Popularity
    pop = item.get("popularity")
    if isinstance(pop, (int, float)):
        score += float(pop) * 5.0

    return score


def resolve_favorite(
    favorite: str,
    type_hint: Optional[str] = None,
    force_mock: Optional[bool] = None
) -> Optional[Dict[str, Any]]:
    """Resolves a single cultural favorite into its best Qloo entity or None if NOT FOUND.

    Ranks candidates by type hint match and exact name match.
    Returns top 3 candidates and reports whether resolved type matches type_hint.
    """
    fav_clean = str(favorite).strip()
    if not fav_clean:
        return None

    results = search_entity(fav_clean, force_mock=force_mock)
    if not results:
        return None

    valid_items = [it for it in results if isinstance(it, dict)]
    if not valid_items:
        return None

    # Score and rank results to find the most culturally appropriate match
    ranked = sorted(valid_items, key=lambda it: score_search_candidate(it, fav_clean, type_hint), reverse=True)
    best = ranked[0]

    eid = (
        best.get("entity_id") or
        best.get("id") or
        best.get("urn") or
        (best.get("properties", {}).get("id") if isinstance(best.get("properties"), dict) else None)
    )
    if not eid:
        return None

    subtype = best.get("subtype") or best.get("type") or "cultural_entity"
    type_matched = is_type_match(subtype, type_hint)

    top_candidates = [
        {
            "name": it.get("name") or it.get("title") or "Unknown",
            "type": it.get("subtype") or it.get("type") or "unknown",
            "id": str(it.get("entity_id") or it.get("id") or it.get("urn") or "")
        }
        for it in ranked[:3]
    ]

    return {
        "query": fav_clean,
        "name": best.get("name") or best.get("title") or fav_clean,
        "id": str(eid),
        "subtype": subtype,
        "type_hint": type_hint,
        "type_matched": type_matched,
        "top_candidates": top_candidates,
        "raw": best
    }


def resolve_signal_entities(
    signals: List[str],
    force_mock: Optional[bool] = None
) -> Tuple[List[str], List[Dict[str, Any]], List[str]]:
    """Resolves human taste signals (e.g. 'Norah Jones', 'Aesop') into verified Qloo entity IDs.

    Returns:
        Tuple of:
        - resolved_ids: List of Qloo UUID strings (for insights API)
        - resolved_entities: List of resolved entity info dicts (name, id, subtype)
        - skipped: List of favorite names that could not be resolved (NOT FOUND)
    """
    resolved_ids: List[str] = []
    resolved_entities: List[Dict[str, Any]] = []
    skipped: List[str] = []

    for sig in signals:
        sig_clean = sig.strip()
        if not sig_clean:
            continue
        try:
            res = resolve_favorite(sig_clean, force_mock=force_mock)
            if res and res.get("id"):
                resolved_ids.append(res["id"])
                resolved_entities.append(res)
            else:
                skipped.append(sig_clean)
        except QlooError:
            raise
        except Exception:
            skipped.append(sig_clean)

    return resolved_ids, resolved_entities, skipped


# Qloo tag filters (OR-ed) used to fetch each category; results are re-classified by their own
# primary genre afterwards, because Qloo's tag filter is a loose pre-filter.
CATEGORY_FILTER_TAGS: Dict[str, str] = {
    "hotel": "urn:tag:genre:place:hotel",
    "restaurant": "urn:tag:genre:place:restaurant",
    "cafe": "urn:tag:genre:place:restaurant:coffee_shop,urn:tag:genre:place:restaurant:cafe,urn:tag:genre:place:bakery",
    "bar": "urn:tag:genre:place:restaurant:bar,urn:tag:genre:place:night_club,urn:tag:genre:place:bar",
    "attraction": "urn:tag:genre:place:tourist_attraction,urn:tag:genre:place:museum,urn:tag:genre:place:park",
    "shop": "urn:tag:genre:place:shopping,urn:tag:genre:place:book_store",
}

# Qloo nests bars and cafes under the restaurant genre; without excluding them, taste-driven
# restaurant queries in some cities return almost no sit-down restaurants.
CATEGORY_EXCLUDE_TAGS: Dict[str, str] = {
    "restaurant": (
        "urn:tag:genre:place:restaurant:bar,urn:tag:genre:place:restaurant:cafe,"
        "urn:tag:genre:place:restaurant:coffee_shop,urn:tag:genre:place:restaurant:wine_bar,"
        "urn:tag:genre:place:restaurant:cocktail_bar"
    ),
}

_SLIM_PROPERTY_KEYS = (
    "description", "short_description", "address", "geocode", "price_level", "price",
    "images", "primary_genre", "keywords", "locality", "category", "website",
)


def _extract_raw_items(data: Any) -> List[Dict[str, Any]]:
    """Unpacks the place list from Qloo response containers (results.entities, results.items, ...)."""
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    container = data.get("results")
    if isinstance(container, dict):
        return container.get("entities") or container.get("items") or container.get("data") or []
    if isinstance(container, list):
        return container
    for key in ("entities", "items", "data"):
        if isinstance(data.get(key), list):
            return data[key]
    return []


def _slim_place(raw: Any) -> Any:
    """Drops translations (akas), references and other bulk from a raw place before caching/logging."""
    if not isinstance(raw, dict):
        return raw
    slim = {k: v for k, v in raw.items() if k not in ("references", "external", "disambiguation")}
    props = raw.get("properties")
    if isinstance(props, dict):
        slim_props = {k: props[k] for k in _SLIM_PROPERTY_KEYS if k in props}
        if isinstance(slim_props.get("primary_genre"), dict):
            pg = slim_props["primary_genre"]
            slim_props["primary_genre"] = {"id": pg.get("id"), "name": pg.get("name")}
        if isinstance(slim_props.get("images"), list):
            slim_props["images"] = slim_props["images"][:1]
        slim["properties"] = slim_props
    if isinstance(raw.get("tags"), list):
        slim["tags"] = [
            {"id": t.get("id"), "name": t.get("name"), "type": t.get("type")} if isinstance(t, dict) else t
            for t in raw["tags"]
        ]
    return slim


def _slim_places_response(data: Any) -> Dict[str, Any]:
    return {"results": {"entities": [_slim_place(r) for r in _extract_raw_items(data)]}}


def get_recommendations(
    signals: List[str],
    category: str,
    location: str,
    force_mock: Optional[bool] = None,
    location_query: Optional[str] = None,
    signal_ids: Optional[List[str]] = None,
    take: int = 20,
    include_other_categories: bool = False,
    dropped_log: Optional[List[Dict[str, str]]] = None,
    max_price_level: Optional[int] = None
) -> List[Candidate]:
    """Generates ranked venue recommendations matching a group or individual's taste profile.

    Crucial Rules:
    - In LIVE mode, queries https://hackathon.api.qloo.com for the requested `location`.
    - Never defaults or falls back to Lisbon when another city is requested.
    - If 0 candidates are returned for a city in live mode, raises QlooNoCandidatesError.
    - If in mock mode, returns authentic mock data for Lisbon, Tokyo, or Delhi, or raises
      QlooCityNotFoundError for uncataloged cities.
    - Every live venue is classified from Qloo's own genre metadata (classify_place);
      lodging, non-travel businesses and ambiguous venues never leak into other categories.

    Args:
        signals: Cultural favorites or affinities (e.g. ['Burial', 'natural wine']).
        category: Venue category: 'hotel', 'restaurant', 'cafe', 'bar', 'attraction', 'shop'.
        location: Target city (e.g. 'Lisbon', 'Tokyo', 'Delhi').
        force_mock: Optional override to force mock mode.
        location_query: Optional precise Qloo location string (e.g. 'Porto, Porto, Portugal')
            sent to the API instead of `location`; `location` is still used for display.
        signal_ids: Already-resolved Qloo entity IDs; skips resolving `signals` by name.
        take: Number of places requested from Qloo.
        include_other_categories: Also return venues that classified into a different
            category than requested (each keeps its own real category).
        dropped_log: Optional list that receives {name, reason} for every excluded venue.
        max_price_level: Optional price ceiling (1-4) sent to Qloo as filter.price_level.max, so a
            budget limit shapes the search itself instead of discarding results afterwards.

    Returns:
        List of Candidate objects sorted by qloo_affinity in descending order.
    """
    category_clean = category.strip().lower()
    location_clean = location.strip()

    use_mock = force_mock if force_mock is not None else is_qloo_mock_mode()

    # -----------------------------------------------------------------
    # MOCK MODE (Offline catalog for Lisbon, Tokyo, and Delhi)
    # -----------------------------------------------------------------
    if use_mock:
        return _get_mock_recommendations(signals, category_clean, location_clean)

    # -----------------------------------------------------------------
    # REAL MODE: Live Qloo API call targeted to the requested city
    # -----------------------------------------------------------------
    params: Dict[str, Any] = {
        "filter.type": "urn:entity:place",
        "filter.location.query": (location_query or "").strip() or location_clean,
        "take": take
    }
    if category_clean in CATEGORY_FILTER_TAGS:
        params["filter.tags"] = CATEGORY_FILTER_TAGS[category_clean]
    if category_clean in CATEGORY_EXCLUDE_TAGS:
        params["filter.exclude.tags"] = CATEGORY_EXCLUDE_TAGS[category_clean]
    if max_price_level and 1 <= int(max_price_level) <= 4:
        params["filter.price_level.max"] = int(max_price_level)

    ids = list(signal_ids or [])
    if not ids and signals:
        ids, _, _ = resolve_signal_entities(signals, force_mock=use_mock)
    if ids:
        params["signal.interests.entities"] = ",".join(ids[:8])

    data = _make_request("GET", "/v2/insights", params=params, transform=_slim_places_response)
    raw_items = _extract_raw_items(data)

    # Error handling: If live API returns 0 candidates for this city, DO NOT fall back to Lisbon!
    if not raw_items:
        raise QlooNoCandidatesError(
            f"No candidates returned by Qloo API for city '{location_clean}' in category '{category_clean}'.\n"
            f"Please verify that '{location_clean}' is a recognized city or broaden your query."
        )

    candidates: List[Candidate] = []
    for raw in raw_items:
        try:
            if not isinstance(raw, dict):
                continue
            raw_props = raw.get("properties") if isinstance(raw.get("properties"), dict) else {}
            primary_genre, genre_ids = extract_place_genres(raw)
            inferred_cat, reason = classify_place(
                name=str(raw.get("name") or raw.get("title") or ""),
                description=str(raw_props.get("description") or raw.get("description") or ""),
                primary_genre=primary_genre,
                genre_ids=genre_ids,
                raw_category=raw.get("category") or raw_props.get("category")
            )
            if inferred_cat is None:
                if dropped_log is not None:
                    dropped_log.append({"name": str(raw.get("name") or "Unknown"), "reason": reason})
                continue
            if inferred_cat != category_clean and not include_other_categories:
                continue
            candidates.append(parse_raw_candidate(raw, category=inferred_cat, location=location_clean))
        except Exception:
            # One odd venue never crashes the whole category!
            continue

    # Real Qloo affinity (for the request's signals), highest first
    candidates.sort(key=lambda c: c.qloo_affinity, reverse=True)
    return candidates


def _slim_affinity_response(data: Any) -> Dict[str, Any]:
    rows = []
    for raw in _extract_raw_items(data):
        if not isinstance(raw, dict):
            continue
        eid = raw.get("entity_id") or raw.get("id")
        aff = (raw.get("query") or {}).get("affinity") if isinstance(raw.get("query"), dict) else None
        if eid and isinstance(aff, (int, float)):
            rows.append({"id": str(eid), "affinity": float(aff)})
    return {"results": rows}


def get_place_affinities(
    signal_ids: List[str],
    entity_ids: List[str],
    chunk_size: int = 50,
    entity_type: str = "urn:entity:place",
    timeout: float = 30.0,
    max_retries: int = 3
) -> Dict[str, float]:
    """Returns Qloo's real affinity of each given entity for one traveler's taste signals.

    Uses /v2/insights restricted to the given entity IDs (filter.results.entities), so every
    traveler is scored by Qloo against the same shared candidate pool. Entities Qloo does not
    return are simply absent from the result; no value is invented for them.
    Defaults to places; pass entity_type='urn:entity:artist' to score artists.
    """
    if not signal_ids or not entity_ids:
        return {}
    affinities: Dict[str, float] = {}
    for start in range(0, len(entity_ids), chunk_size):
        chunk = entity_ids[start:start + chunk_size]
        data = _make_request(
            "GET",
            "/v2/insights",
            params={
                "filter.type": entity_type,
                "filter.results.entities": ",".join(chunk),
                "signal.interests.entities": ",".join(signal_ids[:8]),
                "take": len(chunk),
            },
            transform=_slim_affinity_response,
            timeout=timeout,
            max_retries=max_retries
        )
        for row in data.get("results", []) if isinstance(data, dict) else []:
            affinities[row["id"]] = row["affinity"]
    return affinities


# =====================================================================
# Music: artist resolution and artist insights
# =====================================================================

ARTIST_TYPE = "urn:entity:artist"

# Music requests are optional extras: fail fast rather than hang for minutes
MUSIC_TIMEOUT = 20.0
MUSIC_RETRIES = 2


def normalize_music_name(name: Any) -> str:
    """Lowercases, strips accents and keeps only letters/digits, for exact-name comparison."""
    text = unicodedata.normalize("NFKD", str(name or "")).casefold()
    return "".join(ch for ch in text if ch.isalnum())


def _first_external_id(external: Any, key: str) -> Optional[str]:
    entries = external.get(key) if isinstance(external, dict) else None
    if isinstance(entries, list) and entries and isinstance(entries[0], dict) and entries[0].get("id"):
        return str(entries[0]["id"])
    return None


def _slim_artist(raw: Any) -> Optional[Dict[str, Any]]:
    """Reduces a raw Qloo artist entity to the verified fields the music engine uses.

    Raw artist payloads carry long biographies and translations; they are never cached whole.
    Every value is taken directly from Qloo: nothing here is inferred or invented.
    """
    if not isinstance(raw, dict):
        return None
    eid = raw.get("entity_id") or raw.get("id")
    name = str(raw.get("name") or "").strip()
    if not eid or not name:
        return None

    props = raw.get("properties") if isinstance(raw.get("properties"), dict) else {}
    external = raw.get("external") if isinstance(raw.get("external"), dict) else {}
    query_block = raw.get("query") if isinstance(raw.get("query"), dict) else {}
    image = props.get("image")

    def str_list(value: Any, limit: int) -> List[str]:
        return [str(v).strip() for v in value if str(v).strip()][:limit] if isinstance(value, list) else []

    affinity = query_block.get("affinity")
    popularity = raw.get("popularity")
    return {
        # Search returns lower-case UUIDs but insights return upper-case: normalize so IDs always compare equal
        "id": str(eid).upper(),
        "name": name,
        "aliases": str_list(props.get("aliases"), 8),
        "affinity": float(affinity) if isinstance(affinity, (int, float)) else None,
        "popularity": float(popularity) if isinstance(popularity, (int, float)) else None,
        "genres": str_list(props.get("primary_genres"), 4),
        "notable_songs": str_list(props.get("notable_songs"), 8),
        "place_of_birth": props.get("place_of_birth") if isinstance(props.get("place_of_birth"), str) else None,
        "image_url": image.get("url") if isinstance(image, dict) else None,
        "spotify_id": _first_external_id(external, "spotify"),
        "lastfm_id": _first_external_id(external, "lastfm"),
        "musicbrainz_id": _first_external_id(external, "musicbrainz"),
    }


def _slim_artists_response(data: Any) -> Dict[str, Any]:
    slim = [_slim_artist(r) for r in _extract_raw_items(data)]
    return {"results": [s for s in slim if s]}


def resolve_artist(name: str) -> Optional[Dict[str, Any]]:
    """Resolves a favourite to a real Qloo *music artist* entity, or None.

    Unlike resolve_favorite, this searches only urn:entity:artist and accepts a match only when
    the artist's name or one of its aliases equals the query (accents and punctuation ignored).
    A near miss such as 'Metallica and Ozzy Osbourne' for 'Metallica' is rejected, so a wrong
    artist never seeds a recommendation. Returns the slim artist record plus 'matched_name'.
    """
    wanted = normalize_music_name(name)
    if not wanted:
        return None
    data = _make_request(
        "GET",
        "/v2/search",
        params={"query": str(name).strip(), "types": ARTIST_TYPE, "take": 10},
        transform=_slim_artists_response,
        timeout=MUSIC_TIMEOUT,
        max_retries=MUSIC_RETRIES
    )
    matches = []
    for rec in data.get("results", []) if isinstance(data, dict) else []:
        names = [rec["name"]] + rec["aliases"]
        if any(normalize_music_name(n) == wanted for n in names):
            matches.append(rec)
    if not matches:
        return None
    best = max(matches, key=lambda r: r["popularity"] or 0.0)
    return {**best, "matched_name": str(name).strip()}


def get_artist_insights(
    signal_entity_ids: Optional[List[str]] = None,
    signal_tag_ids: Optional[List[str]] = None,
    location_query: Optional[str] = None,
    take: int = 30
) -> List[Dict[str, Any]]:
    """Qloo artist recommendations for entity, tag and/or location signals (all optional, any mix).

    Each result is a slim artist record whose 'affinity' is Qloo's own query.affinity for the
    given signals (None when Qloo did not provide one). Raises QlooError on API failure.
    """
    params: Dict[str, Any] = {"filter.type": ARTIST_TYPE, "take": take}
    if signal_entity_ids:
        params["signal.interests.entities"] = ",".join(signal_entity_ids[:8])
    if signal_tag_ids:
        params["signal.interests.tags"] = ",".join(signal_tag_ids[:8])
    if location_query:
        params["signal.location.query"] = location_query.strip()
    if len(params) == 2:
        return []
    data = _make_request("GET", "/v2/insights", params=params, transform=_slim_artists_response,
                         timeout=MUSIC_TIMEOUT, max_retries=MUSIC_RETRIES)
    return data.get("results", []) if isinstance(data, dict) else []


def get_destination_country(location_query: str) -> Optional[str]:
    """Returns the English country name Qloo reports for places in a destination, or None.

    Uses one place lookup (cached): geocode.country is English, which place_of_birth also uses,
    so the two can be compared reliably regardless of the destination's local-language name.
    """
    def transform(data: Any) -> Dict[str, Any]:
        countries = []
        for raw in _extract_raw_items(data):
            geocode = (raw.get("properties") or {}).get("geocode") if isinstance(raw, dict) else None
            if isinstance(geocode, dict) and geocode.get("country"):
                countries.append(str(geocode["country"]))
        return {"results": countries}

    data = _make_request(
        "GET",
        "/v2/insights",
        params={"filter.type": "urn:entity:place", "filter.location.query": location_query.strip(), "take": 5},
        transform=transform,
        timeout=MUSIC_TIMEOUT,
        max_retries=MUSIC_RETRIES
    )
    countries = data.get("results", []) if isinstance(data, dict) else []
    return max(set(countries), key=countries.count) if countries else None


def _get_mock_recommendations(
    signals: List[str],
    category: str,
    location: str
) -> List[Candidate]:
    """Internal helper for offline mock data retrieval.

    Never silently defaults to Lisbon:
    - Matches 'lisbon', 'tokyo', or 'delhi' from the offline catalog.
    - If the city is not in the offline catalog, raises QlooCityNotFoundError.
    """
    location_lower = location.lower().strip()
    city_key = None

    for known_city in MOCK_CITIES_DATA.keys():
        if known_city in location_lower:
            city_key = known_city
            break

    if not city_key:
        available_cities = ", ".join(k.title() for k in MOCK_CITIES_DATA.keys())
        raise QlooCityNotFoundError(
            f"City '{location}' is not available in the offline mock catalog.\n"
            f"Available offline cities: {available_cities}.\n"
            f"To query live venues for '{location}', please configure QLOO_API_KEY in your .env file "
            f"to use the LIVE QLOO API."
        )

    city_data = MOCK_CITIES_DATA[city_key]
    raw_venues = city_data.get(category, [])

    if not raw_venues and city_data:
        raw_venues = list(city_data.values())[0]

    candidates: List[Candidate] = []
    for venue in raw_venues:
        affinity = calculate_mock_affinity(
            candidate_tags=venue.get("tags", []),
            candidate_name=venue.get("name", ""),
            signals=signals
        )

        cand = Candidate(
            id=venue["id"],
            name=venue["name"],
            category=venue["category"],
            location=venue["location"],
            qloo_affinity=affinity,
            tags=venue.get("tags", []),
            price_level=venue.get("price_level", "$$"),
            description=venue.get("description"),
            address=venue.get("address")
        )
        candidates.append(cand)

    candidates.sort(key=lambda c: c.qloo_affinity, reverse=True)

    _log_interaction(
        method="MOCK_GET",
        endpoint="/v2/insights",
        params={"category": category, "location": location, "signals": signals},
        status_code=200,
        response_body=[c.model_dump() for c in candidates],
        from_cache=False
    )

    return candidates
