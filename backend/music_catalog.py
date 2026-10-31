"""Track verification and listening links via the Apple iTunes Search API.

Qloo returns artists and their notable song *titles*, but not playable tracks or streaming links.
This module is the smallest additional catalogue integration that fills that gap:

- No API key or account is required (https://itunes.apple.com/search).
- A track is only returned when the catalogue lists it under the *same artist*, so every title,
  link and preview shown to users comes from a real catalogue record.
- Results are cached in the existing SQLite cache table; failures never raise.

Configuration (all optional):
    MUSIC_CATALOG          'itunes' (default) or 'off' to disable lookups entirely.
    MUSIC_CATALOG_COUNTRY  Two-letter storefront code (default 'US').
"""

import os
import re
import json
import hashlib
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

import httpx

from backend.qloo_client import _get_cache, _set_cache, normalize_music_name

ITUNES_SEARCH_URL = "https://itunes.apple.com/search"
PROVIDER = "apple_music"

# Lookup outcomes. 'ok' includes 'no match for this artist'; the other two mean the service
# could not answer, so callers must not treat missing tracks as "artist has no tracks".
STATUS_OK = "ok"
STATUS_UNAVAILABLE = "unavailable"
STATUS_DISABLED = "disabled"


def catalog_enabled() -> bool:
    return os.getenv("MUSIC_CATALOG", "itunes").strip().lower() not in ("off", "none", "false", "0", "")


def _country() -> str:
    code = os.getenv("MUSIC_CATALOG_COUNTRY", "US").strip().upper()
    return code if re.fullmatch(r"[A-Z]{2}", code) else "US"


def normalize_title(title: Any) -> str:
    """Normalizes a track title: drops '(feat. X)', '[Remastered]' and ' - Live' style suffixes."""
    text = unicodedata.normalize("NFKD", str(title or ""))
    text = re.sub(r"[\(\[].*?[\)\]]", " ", text)
    text = re.split(r"\s[-–—]\s", text)[0]
    return normalize_music_name(text)


def _search_artist_songs(artist_term: str) -> Tuple[Optional[List[Dict[str, Any]]], str]:
    """Returns (songs, status). songs is None when the service could not answer."""
    params = {
        "term": artist_term,
        "entity": "song",
        "attribute": "artistTerm",
        "media": "music",
        "limit": 25,
        "country": _country(),
    }
    cache_key = hashlib.sha256(f"itunes:{json.dumps(params, sort_keys=True)}".encode("utf-8")).hexdigest()
    cached = _get_cache(cache_key)
    if isinstance(cached, dict) and isinstance(cached.get("results"), list):
        return cached["results"], STATUS_OK

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.get(ITUNES_SEARCH_URL, params=params)
        if response.status_code != 200:
            return None, STATUS_UNAVAILABLE  # includes 403/429 throttling
        slim = [
            {
                "artist": r.get("artistName"),
                "title": r.get("trackName"),
                "album": r.get("collectionName"),
                "artwork_url": r.get("artworkUrl100"),
                "preview_url": r.get("previewUrl"),
                "listen_url": r.get("trackViewUrl"),
            }
            for r in response.json().get("results", [])
            if isinstance(r, dict) and r.get("kind") == "song"
        ]
    except (httpx.HTTPError, ValueError):
        return None, STATUS_UNAVAILABLE

    _set_cache(cache_key, "itunes_search", params, {"results": slim})
    return slim, STATUS_OK


def find_track(
    artist_names: List[str],
    notable_songs: List[str]
) -> Tuple[Optional[Dict[str, Any]], str]:
    """Finds one verified track for an artist. Returns (track or None, status).

    artist_names: the artist's name followed by known aliases; the first is used as the search
        term and a catalogue record counts only if its artist equals one of them exactly.
    notable_songs: Qloo's notable song titles. A match on one of these is preferred; otherwise the
        first catalogue song by exactly that artist is returned and marked as such in 'basis'.
    """
    if not catalog_enabled():
        return None, STATUS_DISABLED
    names = [n for n in artist_names if n]
    if not names:
        return None, STATUS_OK

    songs, status = _search_artist_songs(names[0])
    if songs is None:
        return None, status

    wanted_artists = {normalize_music_name(n) for n in names}
    by_artist = [
        s for s in songs
        if s.get("listen_url") and s.get("title") and normalize_music_name(s.get("artist")) in wanted_artists
    ]
    if not by_artist:
        return None, STATUS_OK

    for qloo_title in notable_songs:
        wanted_title = normalize_title(qloo_title)
        if not wanted_title:
            continue
        for song in by_artist:
            if normalize_title(song["title"]) == wanted_title:
                return {**song, "provider": PROVIDER, "basis": "qloo_notable_song"}, STATUS_OK

    return {**by_artist[0], "provider": PROVIDER, "basis": "catalog_listing"}, STATUS_OK
