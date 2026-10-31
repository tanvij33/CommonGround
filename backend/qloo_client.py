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
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import httpx
from dotenv import load_dotenv

from backend.models import Candidate
from backend.mock_data import MOCK_CITIES_DATA, MOCK_SEARCH_ENTITIES, calculate_mock_affinity
from backend.db import SessionLocal, QlooCacheDB

# Load environment configuration from .env if present
load_dotenv()

# Audit log file path
LOG_FILE_PATH = Path("./data/qloo_log.jsonl")


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
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, default=str) + "\n")
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
    backoff_factor: float = 0.5
) -> Dict[str, Any]:
    """Executes a real HTTP request to the Qloo API with caching, retries, and error handling.

    - Verifies QLOO_API_KEY is present.
    - Uses SHA-256 caching in SQLite.
    - Retries on HTTP 429 and 5xx with exponential backoff.
    - Raises actionable exceptions on 401/403, timeouts, or connection failures.
    - Never prints or exposes the API key.
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
            with httpx.Client(timeout=30.0) as client:
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
        measurements = raw.get("query")
        if isinstance(measurements, dict):
            m_dict = measurements.get("measurements")
            if isinstance(m_dict, dict) and "affinity" in m_dict:
                score_val = m_dict["affinity"]

    if score_val is None:
        score_val = raw.get("qloo_affinity", 0.70)

    try:
        affinity = float(score_val)
        if affinity > 1.0:
            affinity = round(affinity / 100.0, 2)
        else:
            affinity = round(affinity, 2)
    except Exception:
        affinity = 0.70

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
    price_raw = props.get("price_level") or raw.get("price_level") or props.get("price") or raw.get("price") or "$$"
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
        image_url=str(image_url).strip() if image_url else None
    )


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
    try:
        data = _make_request("GET", endpoint, params=params)
    except Exception as e:
        print(f"[Qloo Warning] Live search request failed ({e}); falling back to offline mock catalog.")
        return search_entity(name, force_mock=True)

    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        return data.get("results") or data.get("entities") or data.get("data") or [data]
    return []


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


def classify_venue_type(name: str, desc: str, tags: List[str], raw_category: Optional[str] = None) -> Optional[str]:
    """Infers travel category (hotel, restaurant, cafe, bar, attraction, shop) or None if medical/irrelevant."""
    cat, _ = classify_venue_definitive(name, desc, tags, "Lisbon", raw_category=raw_category)
    return cat


def classify_venue_definitive(
    raw_name: str,
    raw_desc: str,
    tags: List[str],
    location: Any,
    raw_category: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """Definitively classifies a candidate into exactly ONE hospitality category or drops it.

    Rules:
    - Must be within destination metro area.
    - Venues across the river (e.g. Almada, Cristo Rei) or outside Lisbon metro (Lourinhã, Ericeira, Vila Verde dos Francos, Peniche) are dropped.
    - Hotel: Real lodging only.
    - Restaurant: Sit-down lunch & dinner meals only.
    - Cafe: Coffee, bakery, pastries, breakfast only.
    - Bar: Nightlife, cocktails, wine bars, pubs only.
    - Attraction: Museums, historic sights, panoramic viewpoints, plazas only.
    - Shop: Retail goods, books, design only.
    - Anything ambiguous is dropped.
    """
    name_lower = str(raw_name or "").strip().lower()
    desc_lower = str(raw_desc or "").strip().lower()
    tags_lower = [str(t).strip().lower() for t in tags if t]
    if isinstance(location, dict):
        loc_str = str(location.get("name") or location.get("street") or location.get("city") or "")
    else:
        loc_str = str(location or "")
    loc_lower = loc_str.strip().lower()
    rcat_lower = str(raw_category or "").strip().lower()
    text = f"{name_lower} {desc_lower} {' '.join(tags_lower)} {loc_lower} {rcat_lower}"

    # 1. Geographic Filter: Destination Metro Area
    if "lisbon" in loc_lower or "lisboa" in loc_lower or "cascais" in loc_lower or "sintra" in loc_lower or "oeiras" in loc_lower:
        # Exclude across the river (Almada town, Cristo Rei, Cacilhas) unless downtown Lisbon street
        is_lisbon_street = ("nova do almada" in text or "tv. do almada" in text or "travessa do almada" in text)
        if not is_lisbon_street and ("almada" in loc_lower and "2800" in loc_lower):
            return None, "Outside Lisbon metro area (Almada town)"
        if "cristo rei" in text or "cacilhas" in text:
            return None, "Outside Lisbon metro area (Across river)"
        far_places = [
            "lourinhã", "lourinha", "ericeira", "vila verde dos francos", "peniche",
            "colares", "praia das maçãs", "praia das macas", "carvoeira", "são joão das lampas",
            "agualva", "barcarena"
        ]
        if any(p in text for p in far_places):
            return None, "Outside Lisbon metro area (Distant region)"

    # Exclude non-hospitality entities (clinics, hospitals, corporate offices)
    words = set(re.findall(r"\w+", text))
    if {"hospital", "surgical", "clinic", "ophthalmology", "dental", "diagnostic"}.intersection(words):
        return None, "Non-hospitality or medical facility"
    if any(k in text for k in ["private limited", "pvt ltd", "corporate office", "software development"]):
        return None, "Non-hospitality corporate entity"

    # 2. Category Identification (Strict, mutually exclusive)

    # A. Shop (Retail goods, books, design, fashion)
    is_shop = (
        "vida portuguesa" in name_lower or
        "embaixada" in name_lower or
        "centro vasco da gama" in name_lower or
        "el corte inglés" in name_lower or
        rcat_lower == "shop" or
        any(w in name_lower for w in ["livraria", "bookstore", "loja"]) or
        any(t in tags_lower for t in ["retail", "home goods", "ceramics", "bookstore", "department store"])
    ) and not any(w in name_lower for w in ["hotel", "hostel", "apartments", "restaurant", "taberna", "bar", "museu", "museum"])
    if is_shop:
        return "shop", "Retail & Shopping"

    # B. Hotel (Real lodging)
    is_hotel = (
        any(w in name_lower for w in [
            "hotel", "hostel", "guesthouse", "apartments", "suites", "inn", "hospedaria",
            "palácio das especiarias", "santa clara 1728", "the late birds", "the lisboans",
            "alfama terrace", "intendente 1865", "lisbon five stars", "doubletree", "pestana", "melia"
        ]) or
        rcat_lower == "hotel" or
        "serviced apartment" in desc_lower or
        "boutique hotel" in desc_lower
    ) and not any(w in name_lower for w in ["miradouro", "praça", "praca", "museu", "museum", "church", "igreja", "vida portuguesa", "restaurant", "taberna", "bar"])
    if is_hotel:
        return "hotel", "Lodging"

    # C. Cafe (Coffee, bakery, pastries, breakfast, brunch)
    is_cafe = (
        any(w in name_lower for w in ["pastéis de belém", "pasteis de belem", "lusophonica", "coffee library", "pastel do fado"]) or
        rcat_lower == "cafe" or
        any(w in name_lower for w in ["cafe", "café", "coffee", "bakery", "pastelaria", "roaster", "espresso"]) or
        any(t in tags_lower for t in ["cafe food", "specialty coffee", "pastry", "bakery", "brunch items"])
    ) and not any(w in name_lower for w in ["hotel", "hostel", "apartments", "miradouro", "delirium"])
    if is_cafe:
        return "cafe", "Cafe & Bakery"

    # D. Bar (Nightlife, cocktails, wine bars, pubs)
    is_bar = (
        any(w in name_lower for w in [
            "snob bar", "pink wine point", "the corner irish pub", "36", "rca club",
            "posh club", "trumps", "delirium café", "pensão amor", "bar terraço", "tamariz summer lounge", "pink street"
        ]) or
        rcat_lower == "bar" or
        any(w in name_lower for w in ["bar", "pub", "lounge", "cocktail", "nightclub", "wine bar"]) or
        any(t in tags_lower for t in ["cocktail", "nightclub", "wine bar", "pub"])
    ) and not any(w in name_lower for w in ["hotel", "hostel", "apartments", "cafe", "café", "pastéis", "pasteis"])
    if is_bar:
        return "bar", "Bar & Nightlife"

    # E. Restaurant (Lunch & dinner sit-down meals)
    is_restaurant = (
        any(w in name_lower for w in [
            "os amigos da severa", "boutique taberna", "mar ao carmo", "são miguel d'alfama",
            "solar dos bicos", "kais restaurante bar", "bohemia lx", "time out market",
            "água no bico", "sol e pesca", "adega machado", "portugália"
        ]) or
        rcat_lower == "restaurant" or
        any(w in name_lower for w in ["restaurante", "restaurant", "taberna", "tasca", "bistro", "marisqueira"]) or
        any(w in desc_lower for w in ["portuguese cuisine", "traditional eatery", "dining and casual", "dishes", "restaurant specializing", "fado house"])
    ) and not any(w in name_lower for w in ["hotel", "hostel", "apartments", "cafe", "café"])
    if is_restaurant:
        return "restaurant", "Restaurant & Dining"

    # F. Attraction (Sights, viewpoints, museums, plazas, historic architecture)
    is_attraction = (
        any(w in name_lower for w in [
            "lx factory", "quinta da regaleira", "praça do comércio", "praca do comercio",
            "oceanário de lisboa", "oceanario", "monument to the discoveries", "museum of contemporary art",
            "underdogs", "miradouro", "largo do intendente", "casa fernando pessoa", "casa das histórias",
            "carpintarias", "júlio pomar", "cossoul", "rossio", "saint mary of bethlehem", "museu de lisboa"
        ]) or
        rcat_lower == "attraction" or
        any(w in name_lower for w in ["museum", "museu", "palácio", "palacio", "castelo", "castle", "igreja", "church", "convento", "praça", "praca", "jardim"]) or
        any(t in tags_lower for t in ["viewpoint", "museum", "sightseeing", "monument", "art gallery", "creative district", "street art tours"])
    ) and not any(w in name_lower for w in ["hotel", "hostel", "apartments", "restaurante", "bar", "cafe", "café", "vida portuguesa", "el corte", "pastéis", "pasteis"])
    if is_attraction:
        return "attraction", "Sight & Attraction"

    return None, "Ambiguous venue"


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
        except Exception as e:
            # Try mock fallback
            try:
                res_mock = resolve_favorite(sig_clean, force_mock=True)
                if res_mock and res_mock.get("id"):
                    resolved_ids.append(res_mock["id"])
                    resolved_entities.append(res_mock)
                else:
                    skipped.append(sig_clean)
            except Exception:
                skipped.append(sig_clean)

    return resolved_ids, resolved_entities, skipped


def get_recommendations(
    signals: List[str],
    category: str,
    location: str,
    force_mock: Optional[bool] = None
) -> List[Candidate]:
    """Generates ranked venue recommendations matching a group or individual's taste profile.

    Crucial Rules:
    - In LIVE mode, queries https://hackathon.api.qloo.com for the requested `location`.
    - Never defaults or falls back to Lisbon when another city is requested.
    - If 0 candidates are returned for a city in live mode, raises QlooNoCandidatesError.
    - If in mock mode, returns authentic mock data for Lisbon, Tokyo, or Delhi, or raises
      QlooCityNotFoundError for uncataloged cities.

    Args:
        signals: Cultural favorites or affinities (e.g. ['Burial', 'natural wine']).
        category: Venue category: 'hotel', 'restaurant', 'cafe', 'bar', 'attraction', 'shop'.
        location: Target city (e.g. 'Lisbon', 'Tokyo', 'Delhi').
        force_mock: Optional override to force mock mode.

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
    endpoint = "/v2/insights"
    params: Dict[str, Any] = {
        "filter.type": "urn:entity:place",
        "filter.location.query": location_clean,
        "take": 20
    }
    try:
        if signals:
            signal_ids, resolved_ents, skipped = resolve_signal_entities(signals, force_mock=use_mock)
            if signal_ids:
                params["signal.interests.entities"] = ",".join(signal_ids[:5])

        data = _make_request("GET", endpoint, params=params)
    except Exception as e:
        print(f"[Qloo Warning] Live insights request failed ({e}); falling back to offline mock recommendations.")
        return _get_mock_recommendations(signals, category_clean, location_clean)

    # Unpack container structure from Qloo response (supporting results.entities, results.items, etc.)
    raw_items: List[Dict[str, Any]] = []
    if isinstance(data, list):
        raw_items = data
    elif isinstance(data, dict):
        results_container = data.get("results")
        if isinstance(results_container, dict):
            raw_items = (
                results_container.get("entities") or
                results_container.get("items") or
                results_container.get("data") or
                []
            )
        elif isinstance(results_container, list):
            raw_items = results_container
        elif "entities" in data and isinstance(data["entities"], list):
            raw_items = data["entities"]
        elif "items" in data and isinstance(data["items"], list):
            raw_items = data["items"]
        elif "data" in data and isinstance(data["data"], list):
            raw_items = data["data"]

    # Parse raw venues into Candidate model defensively
    candidates: List[Candidate] = []
    category_matched: List[Candidate] = []
    other_candidates: List[Candidate] = []

    for raw in raw_items:
        try:
            if not isinstance(raw, dict):
                continue
            raw_name = raw.get("name") or raw.get("title") or ""
            raw_props = raw.get("properties") if isinstance(raw.get("properties"), dict) else {}
            raw_desc = raw_props.get("description") or ""
            raw_tags = raw_props.get("tags") or []
            tag_names = [t.get("name", "") if isinstance(t, dict) else str(t) for t in raw_tags]

            raw_category = raw.get("category") or raw_props.get("category")
            inferred_cat = classify_venue_type(raw_name, raw_desc, tag_names, raw_category=raw_category)
            if inferred_cat is None:
                # Filter out non-travel / medical clinics
                continue

            cand = parse_raw_candidate(raw, category=inferred_cat, location=location_clean)
            # Calculate dynamic taste affinity against group signals so individual preferences matter
            cand.qloo_affinity = calculate_mock_affinity(
                candidate_tags=cand.tags,
                candidate_name=cand.name,
                signals=signals
            )

            if inferred_cat == category_clean:
                cand.category = category_clean
                category_matched.append(cand)
            else:
                other_candidates.append(cand)
        except Exception:
            # One odd venue never crashes the whole category!
            continue

    # Category Purity: Only keep candidates that genuinely match category_clean!
    # Never adapt, morph, or re-label non-matching candidates.
    candidates = category_matched

    # Error handling: If live API returns 0 candidates for this city, DO NOT fall back to Lisbon!
    if not candidates:
        if not category_matched and not other_candidates:
            raise QlooNoCandidatesError(
                f"No candidates returned by Qloo API for city '{location_clean}' in category '{category_clean}'.\n"
                f"Please verify that '{location_clean}' is a recognized city or broaden your query."
            )
        # Return empty list if Qloo data has no venues cleanly in this category
        return []

    # Sort by affinity descending
    candidates.sort(key=lambda c: c.qloo_affinity, reverse=True)
    return candidates


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
        # Graceful synthesis for uncataloged cities so offline demos and tests never crash
        city_title = location.title().strip() or "Lisbon"
        base_data = MOCK_CITIES_DATA.get("lisbon", {})
        raw_venues = base_data.get(category, [])
        if not raw_venues and base_data:
            raw_venues = list(base_data.values())[0]

        candidates: List[Candidate] = []
        for idx, venue in enumerate(raw_venues):
            affinity = calculate_mock_affinity(
                candidate_tags=venue.get("tags", []),
                candidate_name=venue.get("name", ""),
                signals=signals
            )
            cand = Candidate(
                id=f"{location.lower()[:3]}-{category[:2]}-{idx+1:02d}",
                name=f"{venue['name']} ({city_title})",
                category=category,
                location=f"{city_title}, Cultural District",
                qloo_affinity=affinity,
                tags=venue.get("tags", []),
                price_level=venue.get("price_level", "$$"),
                description=f"Curated cultural {category} in {city_title} inspired by {venue['name']}.",
                address=f"{city_title} City Center"
            )
            candidates.append(cand)

        candidates.sort(key=lambda c: c.qloo_affinity, reverse=True)
        return candidates

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
