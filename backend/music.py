"""Three-mode group music recommendation engine for Common Ground.

Modes
-----
vibes       The group picks moods (chill, party, nostalgic...). Each vibe maps to verified Qloo
            artist tags (genre, style, mood) used as Qloo taste signals.
favourites  Members' favourite artists seed Qloo recommendations. Every member gets a spotlight
            slot, the rest are shared picks and discoveries chosen with a taste-debt balancer so
            no single member dominates.
local       Qloo's location signal for the destination finds artists popular with listeners
            there; artists are kept only with local evidence (birthplace or a locally
            characteristic genre), and weaker "popular here" artists are labelled as such.

Data rules
----------
- Artists, genres, popularity, affinity, notable-song titles and Spotify/Last.fm IDs come from Qloo.
- Qloo does not return playable tracks. Tracks, previews and Apple Music links come only from the
  catalogue (backend/music_catalog.py) and only when the catalogue lists the song under the same
  artist. Nothing here fabricates an artist, track, link or score.
- API values (qloo_*) and Common Ground calculations (group_fit, member_fit) are stored in
  separate fields.
"""

import re
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional, Tuple

from backend.models import MusicPlaylist, Profile
from backend.scoring import TasteDebtTracker, group_score
from backend.music_catalog import find_track, STATUS_OK, STATUS_DISABLED, PROVIDER
from backend.qloo_client import (
    ARTIST_TYPE,
    MUSIC_RETRIES,
    MUSIC_TIMEOUT,
    QlooError,
    get_artist_insights,
    get_destination_country,
    get_place_affinities,
    is_qloo_mock_mode,
    normalize_music_name,
    resolve_artist,
    resolve_favorite,
)

MODE_LABELS = {"vibes": "Vibes", "favourites": "Favourites", "local": "Local music"}
DEFAULT_SIZE = 12
NEUTRAL_FIT = 0.5
MAX_PER_GENRE = 3
POOL_PER_MEMBER_CALL = 14
POOL_PER_GROUP_CALL = 20
AFFINITY_CHUNK = 50

# Vibe -> Qloo artist tag IDs. Every ID below was confirmed to exist in Qloo's /v2/tags for the
# artist entity type. Mood/style tags carry the feeling; genre tags anchor it in actual sound.
VIBES: Dict[str, Dict[str, Any]] = {
    "chill": {
        "label": "Chill",
        "tags": ["urn:tag:genre:music:chill", "urn:tag:genre:music:chillout",
                 "urn:tag:genre:music:downtempo", "urn:tag:style:qloo:relaxed"],
    },
    "energetic": {
        "label": "Energetic",
        "tags": ["urn:tag:style:qloo:energetic", "urn:tag:music:qloo:energetic",
                 "urn:tag:genre:music:upbeat"],
    },
    "romantic": {
        "label": "Romantic",
        "tags": ["urn:tag:genre:music:romantic", "urn:tag:music:qloo:romantic",
                 "urn:tag:style:qloo:romantic"],
    },
    "adventurous": {
        "label": "Adventurous",
        "tags": ["urn:tag:audience:qloo:adventurous", "urn:tag:genre:music:experimental",
                 "urn:tag:music:qloo:experimental", "urn:tag:genre:music:world_fusion"],
    },
    "nostalgic": {
        "label": "Nostalgic",
        "tags": ["urn:tag:style:qloo:nostalgic", "urn:tag:music:qloo:nostalgic",
                 "urn:tag:style:qloo:retro", "urn:tag:music:qloo:retro"],
    },
    "party": {
        "label": "Party",
        "tags": ["urn:tag:genre:music:party", "urn:tag:theme:qloo:party",
                 "urn:tag:genre:music:club_music", "urn:tag:genre:music:dance"],
    },
    "indie": {
        "label": "Indie",
        "tags": ["urn:tag:genre:music:indie", "urn:tag:genre:music:indie_rock",
                 "urn:tag:genre:music:indie_pop", "urn:tag:genre:music:indie_folk"],
    },
    "cultural": {
        "label": "Cultural exploration",
        # Worldwide world/folk/traditional taste. Destination-specific music is the Local mode: Qloo's
        # location signal does not combine reliably with these tags (it returned non-local artists).
        "tags": ["urn:tag:genre:music:worldmusic", "urn:tag:genre:music:world_fusion",
                 "urn:tag:genre:music:folk", "urn:tag:genre:music:traditional"],
    },
}

# Genres too widespread to say anything about a place's sound
_GENERIC_GENRES = {
    "pop", "rock", "hip hop", "rap", "electronic", "dance", "r&b", "alternative rock", "indie rock",
    "indie", "dance pop", "dance-pop", "house", "edm", "jazz", "country", "soul", "blues", "classical",
    "folk", "metal", "punk", "singer & songwriter", "singer-songwriter", "electropop", "synthpop",
    "pop rock", "alternative", "funk", "reggae", "heavy metal", "hard rock", "electro house",
    "world music", "latin", "latin pop", "afrobeat", "afrobeats", "lounge", "experimental",
}
_NON_MUSIC_GENRES = {"comedy", "stand-up comedy", "standup comedy", "spoken word", "podcast", "audiobook"}
_NON_ARTIST_FAVORITE_TYPES = {"movie", "tv_show", "brand", "place", "book", "podcast", "game"}


# =====================================================================
# Small helpers
# =====================================================================

def _tag_label(tag_id: str) -> str:
    return tag_id.rsplit(":", 1)[-1].replace("_", " ").title()


def _try(fn: Callable[[Any], Any], arg: Any) -> Tuple[Any, Optional[Exception]]:
    try:
        return fn(arg), None
    except Exception as e:  # noqa: BLE001 - each caller decides how to report partial failure
        return None, e


def _parallel(fn: Callable[[Any], Any], items: List[Any], workers: int = 4) -> List[Tuple[Any, Optional[Exception]]]:
    """Applies fn to every item concurrently; returns (result, error) pairs in input order."""
    if len(items) <= 1:
        return [_try(fn, i) for i in items]
    with ThreadPoolExecutor(max_workers=min(workers, len(items))) as pool:
        return list(pool.map(lambda i: _try(fn, i), items))


def _raise_if_all_failed(outcomes: List[Tuple[Any, Optional[Exception]]]) -> None:
    errors = [e for _, e in outcomes if e is not None]
    if outcomes and len(errors) == len(outcomes):
        raise errors[0]


def is_music_artist(rec: Dict[str, Any]) -> bool:
    """Qloo's artist type also holds actors and comedians. Keep real music acts that have either
    notable songs or a Spotify/Last.fm presence."""
    genres = [g for g in rec.get("genres", []) if g.casefold() not in _NON_MUSIC_GENRES]
    if not genres:
        return False
    return bool(rec.get("notable_songs") or rec.get("spotify_id") or rec.get("lastfm_id"))


def _identity_keys(rec: Dict[str, Any]) -> set:
    """External IDs that identify the same real-world act even when Qloo holds two entities for it
    (e.g. a romanized and a native-script entry)."""
    return {(kind, rec[field]) for kind, field in (("spotify", "spotify_id"), ("musicbrainz", "musicbrainz_id")) if rec.get(field)}


def _dedupe(recs: List[Dict[str, Any]], seen: Optional[set] = None) -> List[Dict[str, Any]]:
    """Drops later records that share a Spotify/MusicBrainz ID with an earlier one."""
    seen = seen if seen is not None else set()
    out = []
    for rec in recs:
        keys = _identity_keys(rec)
        if keys & seen:
            continue
        seen |= keys
        out.append(rec)
    return out


def _percentile_ranks(values: Dict[str, float]) -> Dict[str, float]:
    items = sorted(values.items(), key=lambda kv: kv[1])
    n = len(items)
    if n == 0:
        return {}
    if n == 1:
        return {items[0][0]: NEUTRAL_FIT}
    ranks: Dict[str, float] = {}
    i = 0
    while i < n:
        j = i
        while j + 1 < n and items[j + 1][1] == items[i][1]:
            j += 1
        for k in range(i, j + 1):
            ranks[items[k][0]] = round(((i + j) / 2) / (n - 1), 4)
        i = j + 1
    return ranks


def _artist_links(rec: Dict[str, Any]) -> List[Dict[str, str]]:
    links = []
    spotify = rec.get("spotify_id")
    if spotify and re.fullmatch(r"[A-Za-z0-9]{22}", spotify):
        links.append({"label": "Spotify", "url": f"https://open.spotify.com/artist/{spotify}", "kind": "artist"})
    lastfm = rec.get("lastfm_id")
    if lastfm and re.fullmatch(r"[A-Za-z0-9%._~+()'!*,:;@&=$-]+", lastfm):
        links.append({"label": "Last.fm", "url": f"https://www.last.fm/music/{lastfm}", "kind": "artist"})
    return links


def _top_genre(rec: Dict[str, Any]) -> str:
    return rec["genres"][0].casefold() if rec.get("genres") else ""


def _entry(
    rec: Dict[str, Any],
    role: str,
    why: str,
    *,
    group_fit: Optional[float] = None,
    group_fit_basis: str = "",
    qloo_affinity: Optional[float] = None,
    member_fit: Optional[Dict[str, float]] = None,
    qloo_affinity_by_member: Optional[Dict[str, float]] = None,
    vibes: Optional[List[str]] = None,
    local_evidence: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "artist": rec.get("display_name") or rec["name"],
        "qloo_id": rec["id"],
        "role": role,
        "genres": rec.get("genres", []),
        "image_url": rec.get("image_url"),
        "known_for": rec.get("notable_songs", [])[:4],
        "track": None,
        "links": _artist_links(rec),
        "scores": {
            "qloo_affinity": round(qloo_affinity, 4) if qloo_affinity is not None else None,
            "qloo_popularity": round(rec["popularity"], 4) if rec.get("popularity") is not None else None,
            "qloo_affinity_by_member": {k: round(v, 4) for k, v in (qloo_affinity_by_member or {}).items()},
            "group_fit": round(group_fit, 4) if group_fit is not None else None,
            "group_fit_basis": group_fit_basis,
            "member_fit": {k: round(v, 4) for k, v in (member_fit or {}).items()},
        },
        "why": why,
        "vibes": vibes or [],
        "local_evidence": local_evidence,
        "_rec": rec,  # removed before the playlist is returned
    }


def _attach_tracks(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Looks each artist up in the catalogue (concurrently) and attaches verified tracks."""
    def lookup(entry: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], str]:
        rec = entry["_rec"]
        names = [rec.get("display_name") or rec["name"], rec["name"]] + rec.get("aliases", [])
        return find_track(list(dict.fromkeys(names)), rec.get("notable_songs", []))

    outcomes = _parallel(lookup, entries)
    statuses = []
    verified = 0
    for entry, (result, error) in zip(entries, outcomes):
        track, status = result if error is None else (None, "unavailable")
        statuses.append(status)
        if track:
            verified += 1
            entry["track"] = {k: track.get(k) for k in ("title", "album", "artwork_url", "preview_url", "listen_url", "provider", "basis")}
            entry["links"].append({"label": "Apple Music", "url": track["listen_url"], "kind": "track"})

    if entries and all(s == STATUS_DISABLED for s in statuses):
        overall = "disabled"
    elif any(s not in (STATUS_OK, STATUS_DISABLED) for s in statuses):
        overall = "partial" if verified else "unavailable"
    else:
        overall = "ok"
    return {"provider": PROVIDER, "status": overall, "verified_tracks": verified, "artists_checked": len(entries)}


# =====================================================================
# Mode 2: FAVOURITES
# =====================================================================

def _member_artist_favorites(profile: Profile) -> Tuple[List[str], List[Tuple[str, Optional[str]]]]:
    """Splits a member's favourites into artist-eligible names and other (movie/brand/...) entities."""
    artists: List[str] = []
    others: List[Tuple[str, Optional[str]]] = []
    for item in profile.favorites:
        if isinstance(item, dict):
            name, ftype = str(item.get("name") or "").strip(), item.get("type")
        elif isinstance(item, (tuple, list)) and item:
            name, ftype = str(item[0]).strip(), (item[1] if len(item) > 1 else None)
        else:
            name, ftype = str(item).strip(), None
        if not name:
            continue
        if str(ftype or "").lower() in _NON_ARTIST_FAVORITE_TYPES:
            others.append((name, ftype))
        else:
            artists.append(name)
    return list(dict.fromkeys(artists)), others


def _build_favourites(profiles: List[Profile], size: int) -> Dict[str, Any]:
    names = [p.name for p in profiles]
    if not profiles:
        return _result("favourites", "empty", "This trip has no members yet, so there are no favourites to build from.", size=size)

    # ---- 1. Resolve each member's favourite artists to real Qloo artist entities ----
    tasks: List[Tuple[str, str]] = []
    others_by_member: Dict[str, List[Tuple[str, Optional[str]]]] = {}
    for p in profiles:
        artist_names, others = _member_artist_favorites(p)
        others_by_member[p.name] = others
        tasks.extend((p.name, a) for a in artist_names)

    outcomes = _parallel(lambda t: resolve_artist(t[1]), tasks)
    _raise_if_all_failed(outcomes)

    seeds: Dict[str, List[Dict[str, Any]]] = {n: [] for n in names}
    unresolved: Dict[str, List[str]] = {n: [] for n in names}
    for (member, fav), (rec, error) in zip(tasks, outcomes):
        if rec is None:
            unresolved[member].append(fav)
        elif is_music_artist(rec) and rec["id"] not in {s["id"] for s in seeds[member]}:
            seeds[member].append({**rec, "display_name": fav})
        else:
            unresolved[member].append(fav)

    # ---- 2. Signals: favourite artists; otherwise the member's other favourites (cross-domain) ----
    signal_ids: Dict[str, List[str]] = {}
    signal_basis: Dict[str, str] = {}
    for p in profiles:
        if seeds[p.name]:
            signal_ids[p.name] = [s["id"] for s in seeds[p.name]][:5]
            signal_basis[p.name] = "favourite_artists"
            continue
        fallback_ids = []
        for fav, ftype in others_by_member[p.name][:5]:
            res, _ = _try(lambda a: resolve_favorite(a[0], type_hint=a[1]), (fav, ftype))
            if res and res.get("id"):
                fallback_ids.append(res["id"])
        if fallback_ids:
            signal_ids[p.name] = fallback_ids
            signal_basis[p.name] = "other_favourites"
        else:
            signal_ids[p.name] = []
            signal_basis[p.name] = "none"

    active = [n for n in names if signal_ids[n]]
    without_signal = [n for n in names if not signal_ids[n]]
    if not active:
        return _result(
            "favourites", "empty",
            "None of the group's favourites could be matched to Qloo music artists. "
            + _unresolved_note(unresolved),
            size=size, summary={"unresolved": unresolved, "members_without_signal": without_signal},
        )

    # ---- 3. Candidate pool: Qloo recommendations per member + for the whole group + the seeds ----
    group_signals = _round_robin([signal_ids[n] for n in active], 8)
    rec_jobs = [("member", n, signal_ids[n]) for n in active] + [("group", "", group_signals)]
    rec_outcomes = _parallel(lambda j: get_artist_insights(signal_entity_ids=j[2], take=30), rec_jobs)
    _raise_if_all_failed(rec_outcomes)

    # Qloo ranks each result list by affinity; only the best of each list enters the pool, which keeps the
    # per-member affinity stage to one or two requests instead of a dozen
    rec_outcomes = [
        (sorted(recs or [], key=lambda r: -(r.get("affinity") or 0.0))[:(POOL_PER_GROUP_CALL if job[0] == "group" else POOL_PER_MEMBER_CALL)], err)
        for job, (recs, err) in zip(rec_jobs, rec_outcomes)
    ]
    pool: Dict[str, Dict[str, Any]] = {}
    group_affinity: Dict[str, Optional[float]] = {}
    seed_keys = set().union(*(_identity_keys(s) for n in names for s in seeds[n]))
    seen_keys = set(seed_keys)
    seed_id_set = {s["id"] for n in names for s in seeds[n]}
    for (kind, _, _), (recs, _) in zip(rec_jobs, rec_outcomes):
        for rec in recs or []:
            if not is_music_artist(rec):
                continue
            if rec["id"] not in pool and rec["id"] not in seed_id_set:
                keys = _identity_keys(rec)
                if keys & seen_keys:
                    continue  # same act as a favourite or an earlier recommendation
                seen_keys |= keys
            pool.setdefault(rec["id"], rec)
            if kind == "group":
                group_affinity[rec["id"]] = rec.get("affinity")
    seed_ids_by_member = {n: {s["id"] for s in seeds[n]} for n in names}
    all_seed_ids = set().union(*seed_ids_by_member.values())
    for n in names:
        for s in seeds[n]:
            pool[s["id"]] = {**pool.get(s["id"], {}), **s}

    # ---- 4. Qloo's affinity of every pool artist for every member (API values) ----
    pool_ids = list(pool)
    chunks = [pool_ids[i:i + AFFINITY_CHUNK] for i in range(0, len(pool_ids), AFFINITY_CHUNK)]
    aff_jobs = [(n, chunk) for n in active for chunk in chunks]
    aff_outcomes = _parallel(
        lambda job: get_place_affinities(signal_ids[job[0]], job[1], entity_type=ARTIST_TYPE,
                                         timeout=MUSIC_TIMEOUT, max_retries=MUSIC_RETRIES),
        aff_jobs,
    )
    _raise_if_all_failed(aff_outcomes)
    affinity: Dict[str, Dict[str, float]] = {n: {} for n in active}
    failed_chunks: Dict[str, int] = {}
    for (n, _), (res, err) in zip(aff_jobs, aff_outcomes):
        if err is not None:
            failed_chunks[n] = failed_chunks.get(n, 0) + 1
        else:
            affinity[n].update({k.upper(): v for k, v in (res or {}).items()})
    members_affinity_failed = sorted(failed_chunks)
    failed_rec_calls = sum(1 for _, err in rec_outcomes if err is not None)

    # ---- 5. Our member-fit: favourites are 1.0; others are each member's percentile of Qloo affinity ----
    # Qloo may omit an artist for a member; that fit is "unknown" (counted as neutral 0.5 in the maths
    # but never displayed as if it were a score).
    fit: Dict[str, Dict[str, float]] = {n: {} for n in active}
    unknown: Dict[str, List[str]] = {rid: [] for rid in pool_ids}
    for n in active:
        non_seed = {i: a for i, a in affinity[n].items() if i in pool and i not in seed_ids_by_member[n]}
        ranks = _percentile_ranks(non_seed)
        for rid in pool_ids:
            if rid in seed_ids_by_member[n]:
                fit[n][rid] = 1.0
            elif rid in ranks:
                fit[n][rid] = ranks[rid]
            else:
                fit[n][rid] = NEUTRAL_FIT
                unknown[rid].append(n)
    unknown_fits = sum(len(v) for v in unknown.values())

    # ---- 6. Selection: spotlights, then alternating shared picks and member-targeted discoveries ----
    tracker = TasteDebtTracker([SimpleNamespace(name=n) for n in active])
    picked: Dict[str, str] = {}
    targets: Dict[str, str] = {}
    genre_counts: Counter = Counter()
    roles: Dict[str, List[str]] = {"spotlight": [], "shared": [], "discovery": []}

    def fits_for(rid: str) -> Dict[str, float]:
        return {n: fit[n][rid] for n in active}

    def commit(rid: str, role: str, target: Optional[str] = None) -> None:
        picked[rid] = role
        roles[role].append(rid)
        if target:
            targets[rid] = target
        genre_counts[_top_genre(pool[rid])] += 1
        tracker.record_pick(SimpleNamespace(id=rid, name=pool[rid]["name"]), fits_for(rid), time_slot=role)

    def rank_pick(candidates: List[str], score: Callable[[str], float]) -> Optional[str]:
        scored = [
            (genre_counts[_top_genre(pool[r])] < MAX_PER_GENRE,
             score(r) - 0.04 * genre_counts[_top_genre(pool[r])],
             pool[r].get("popularity") or 0.0, r)
            for r in candidates
        ]
        return max(scored)[3] if scored else None

    n_spot = min(len(active), max(1, size // 3))
    for n in active[:n_spot]:
        options = [s for s in seeds[n] if s["id"] not in picked]
        if not options:
            continue
        others = [m for m in active if m != n]
        choice = max(options, key=lambda s: (sum(fit[m][s["id"]] for m in others) / len(others) if others else 0.0,
                                             s.get("popularity") or 0.0))
        commit(choice["id"], "spotlight")

    for slot in range(size - len(picked)):
        free = [r for r in pool_ids if r not in picked]
        if slot % 2 == 1:
            # Discovery: a new artist (nobody's favourite) chosen for whoever is furthest behind
            target, _ = tracker.get_underrepresented()
            target = target or active[slot % len(active)]
            choice = rank_pick([r for r in free if r not in all_seed_ids],
                               lambda r: fit[target][r] + 0.3 * group_score(fits_for(r)))
            if choice is not None:
                commit(choice, "discovery", target)
                continue
        choice = rank_pick(free, lambda r: tracker.calculate_boosted_score(
            SimpleNamespace(id=r, name=pool[r]["name"]), fits_for(r))[0])
        if choice is None:
            break
        commit(choice, "shared")

    # ---- 7. Explanations and entries ----
    entries: List[Dict[str, Any]] = []
    for rid, role in picked.items():
        rec = pool[rid]
        all_fits = fits_for(rid)
        owners = [n for n in active if rid in seed_ids_by_member[n]]
        shown_fit = {n: v for n, v in all_fits.items() if n not in unknown[rid]}
        entry = _entry(
            rec, role,
            _favourites_why(rec, role, owners, targets.get(rid), all_fits, unknown[rid], affinity, seeds, active),
            group_fit=group_score(all_fits),
            group_fit_basis="0.6 x mean + 0.4 x lowest member fit (a member Qloo gave no affinity for counts as neutral 0.5)",
            qloo_affinity=group_affinity.get(rid),
            member_fit=shown_fit,
            qloo_affinity_by_member={n: affinity[n][rid] for n in active if rid in affinity[n] and rid not in seed_ids_by_member[n]},
        )
        entry["scores"]["fit_unknown_members"] = unknown[rid]
        entries.append(entry)
    entries = _interleave(entries, ["shared", "spotlight", "discovery"])

    avg_fit = {n: round(sum(fit[n][r] for r in picked) / len(picked), 4) for n in active} if picked else {}
    summary = {
        "members": names,
        "members_without_signal": without_signal,
        "signal_basis": signal_basis,
        "unresolved": {k: v for k, v in unresolved.items() if v},
        "roles": {k: len(v) for k, v in roles.items()},
        "average_member_fit": avg_fit,
        "fit_spread": round(max(avg_fit.values()) - min(avg_fit.values()), 4) if avg_fit else 0.0,
        "pool_size": len(pool),
        "unknown_affinity_count": unknown_fits,
        "members_affinity_unavailable": members_affinity_failed,
    }
    notes = []
    if without_signal:
        notes.append(f"No usable favourites for {', '.join(without_signal)}, so their taste is not reflected.")
    if any(unresolved.values()):
        notes.append(_unresolved_note(unresolved))
    if members_affinity_failed or failed_rec_calls:
        notes.append("Some Qloo requests failed, so recommendations may be less personalised"
                     + (f" (fit data incomplete for {', '.join(members_affinity_failed)})." if members_affinity_failed else "."))
    summary["failed_recommendation_calls"] = failed_rec_calls
    return _result("favourites", None, " ".join(notes) or None, entries=entries, size=size, summary=summary,
                   selection={"members": names})


def _unresolved_note(unresolved: Dict[str, List[str]]) -> str:
    parts = [f"{m}: {', '.join(v)}" for m, v in unresolved.items() if v]
    return ("Could not match to a Qloo music artist: " + "; ".join(parts) + ".") if parts else ""


def _round_robin(lists: List[List[str]], limit: int) -> List[str]:
    merged: List[str] = []
    depth = 0
    while len(merged) < limit and any(depth < len(lst) for lst in lists):
        for lst in lists:
            if depth < len(lst) and lst[depth] not in merged and len(merged) < limit:
                merged.append(lst[depth])
        depth += 1
    return merged


def _interleave(entries: List[Dict[str, Any]], order: List[str]) -> List[Dict[str, Any]]:
    queues = {role: [e for e in entries if e["role"] == role] for role in order}
    out: List[Dict[str, Any]] = []
    while any(queues.values()):
        for role in order:
            if queues[role]:
                out.append(queues[role].pop(0))
    return out


def _favourites_why(rec, role, owners, target, fits, unknown_members, affinity, seeds, active) -> str:
    genres = ", ".join(rec["genres"][:2]) or "no genre listed"
    known = {m: v for m, v in fits.items() if m not in unknown_members}
    others = [f"{m} {fits[m]:.2f}" for m in active if m not in owners and m in known]
    shared_genres = sorted({g for n in active for s in seeds[n] for g in s["genres"] if g in rec["genres"]})
    link = f" Shares {', '.join(shared_genres[:2])} with the group's favourites." if shared_genres else ""
    if owners:
        who = " and ".join(owners)
        lead = f"Favourite of {who}" + (", so a shared pick" if len(owners) > 1 else "")
        return f"{lead}." + (f" Fit for the rest of the group: {', '.join(others)}." if others else "") + f" Genres: {genres}."
    qaff = affinity.get(target, {}).get(rec["id"]) if target else None
    solo = len(active) == 1
    if role == "discovery":
        qpart = f" (Qloo affinity {qaff:.2f})" if qaff is not None else ""
        if solo:
            return f"A new artist Qloo recommends from {target}'s favourites{qpart}.{link} Genres: {genres}."
        return (f"New for the group, chosen for {target}{qpart}, who had the least of the playlist so far.{link} "
                f"Genres: {genres}.")
    if solo:
        return f"A strong match for {active[0]}'s favourites.{link} Genres: {genres}."
    best_member = max(known, key=known.get) if known else None
    weakest = min(known, key=known.get) if known else None
    spread = (f" Best fit: {best_member}; weakest fit: {weakest} at {known[weakest]:.2f}." if best_member else "")
    return f"Broad appeal across the group.{spread}{link} Genres: {genres}."


# =====================================================================
# Mode 1: VIBES
# =====================================================================

def _build_vibes(vibes: List[str], size: int) -> Dict[str, Any]:
    unknown = [v for v in vibes if v not in VIBES]
    chosen = [v for v in dict.fromkeys(vibes) if v in VIBES]
    if unknown:
        raise ValueError(f"Unknown vibe(s): {', '.join(unknown)}. Choose from: {', '.join(VIBES)}.")
    if not chosen:
        raise ValueError("Pick at least one vibe.")

    def fetch(vibe: str) -> List[Dict[str, Any]]:
        return get_artist_insights(signal_tag_ids=VIBES[vibe]["tags"], take=30)

    outcomes = _parallel(fetch, chosen)
    _raise_if_all_failed(outcomes)

    lists: Dict[str, List[Dict[str, Any]]] = {}
    for vibe, (recs, _) in zip(chosen, outcomes):
        # Qloo's tag affinities are near-identical (e.g. 0.998 vs 0.999), so ties fall back to popularity
        lists[vibe] = sorted(
            (r for r in (recs or []) if is_music_artist(r)),
            key=lambda r: (-round(r.get("affinity") or 0.0, 2), -(r.get("popularity") or 0.0)),
        )
        lists[vibe] = _dedupe(lists[vibe])
    empty_vibes = [VIBES[v]["label"] for v in chosen if not lists[v]]

    matched: Dict[str, Dict[str, int]] = {}
    by_id: Dict[str, Dict[str, Any]] = {}
    affinities: Dict[str, List[float]] = {}
    for vibe, recs in lists.items():
        for rank, rec in enumerate(recs):
            by_id.setdefault(rec["id"], rec)
            matched.setdefault(rec["id"], {})[vibe] = rank
            if rec.get("affinity") is not None:
                affinities.setdefault(rec["id"], []).append(rec["affinity"])

    genre_counts: Counter = Counter()
    picked: List[str] = []

    def take(rid: str) -> bool:
        if rid in picked or genre_counts[_top_genre(by_id[rid])] >= MAX_PER_GENRE:
            return False
        picked.append(rid)
        genre_counts[_top_genre(by_id[rid])] += 1
        return True

    # Artists matching several chosen vibes first, then round-robin so every vibe is represented
    multi = sorted((r for r in matched if len(matched[r]) > 1),
                   key=lambda r: (-len(matched[r]), sum(matched[r].values()) / len(matched[r])))
    for rid in multi:
        if len(picked) < size:
            take(rid)
    depth = 0
    while len(picked) < size and any(depth < len(lists[v]) for v in chosen):
        for vibe in chosen:
            if depth < len(lists[vibe]) and len(picked) < size:
                take(lists[vibe][depth]["id"])
        depth += 1

    entries = []
    for rid in picked:
        rec = by_id[rid]
        vibe_ids = [v for v in chosen if v in matched[rid]]
        share = len(vibe_ids) / len(chosen)
        labels = " + ".join(VIBES[v]["label"] for v in vibe_ids)
        tags = ", ".join(sorted({_tag_label(t) for v in vibe_ids for t in VIBES[v]["tags"]})[:4])
        aff = affinities.get(rid)
        entries.append(_entry(
            rec, "vibe_match" if len(vibe_ids) > 1 else "vibe_pick",
            f"Matches {labels} via Qloo tags ({tags}). Genres: {', '.join(rec['genres'][:2])}.",
            group_fit=share,
            group_fit_basis="Share of the selected vibes this artist matched",
            qloo_affinity=sum(aff) / len(aff) if aff else None,
            vibes=vibe_ids,
        ))

    notes = []
    if empty_vibes:
        notes.append(f"Qloo returned no music artists for: {', '.join(empty_vibes)}.")
    if any(len(matched[r]) > 1 for r in picked) is False and len(chosen) > 1:
        notes.append("No artist matched more than one of the selected vibes, so each vibe is represented separately.")
    return _result(
        "vibes", None, " ".join(notes) or None, entries=entries, size=size,
        selection={"vibes": chosen, "vibe_labels": [VIBES[v]["label"] for v in chosen]},
        summary={"vibes_without_results": empty_vibes,
                 "per_vibe_candidates": {v: len(lists[v]) for v in chosen},
                 "note": "Qloo's affinity for tag signals is close to 1.0 for every result, so artists are "
                         "ordered by that affinity (rounded) and then Qloo popularity, with vibe coverage "
                         "and genre variety applied on top."},
    )


# =====================================================================
# Mode 3: LOCAL MUSIC
# =====================================================================

def _build_local(destination: str, destination_query: Optional[str], size: int) -> Dict[str, Any]:
    location = (destination_query or destination or "").strip()
    if not location:
        return _result("local", "empty", "This trip has no destination to find local music for.", size=size)

    recs = _dedupe([r for r in get_artist_insights(location_query=location, take=50) if is_music_artist(r)])
    country, _ = _try(get_destination_country, location)
    city_norm = normalize_music_name((destination or location).split(",")[0])
    country_norm = normalize_music_name(country) if country else ""

    genre_counts: Counter = Counter()
    for rec in recs:
        for genre in rec["genres"][:2]:
            genre_counts[genre] += 1
    characteristic = {g for g, c in genre_counts.items() if c >= 2 and g.casefold() not in _GENERIC_GENRES}

    tiered: List[Tuple[int, int, Dict[str, Any], str, str]] = []
    excluded_foreign: List[str] = []
    for index, rec in enumerate(recs):
        birth = (rec.get("place_of_birth") or "").strip().strip(",").strip() or None
        birth_norm = normalize_music_name(birth) if birth else ""
        local_genres = [g for g in rec["genres"][:2] if g in characteristic]
        if birth_norm and city_norm and city_norm in birth_norm:
            tiered.append((0, index, rec, "born_in_city", f"Born in {birth} (Qloo)"))
        elif birth_norm and country_norm and country_norm in birth_norm:
            tiered.append((1, index, rec, "born_in_country", f"Born in {birth} (Qloo), in {country}"))
        elif birth_norm and country_norm:
            excluded_foreign.append(rec["name"])
        elif local_genres:
            tiered.append((2, index, rec, "local_genre",
                           f"Plays {local_genres[0]}, a sound that stands out among artists popular in {destination or location} "
                           f"({genre_counts[local_genres[0]]} of {len(recs)}); birthplace not listed by Qloo"))
        else:
            tiered.append((3, index, rec, "popular_here",
                           f"Popular with listeners in {destination or location} (Qloo location signal); "
                           "origin not listed by Qloo, so not confirmed as local"))
    tiered.sort(key=lambda t: (t[0], t[1]))

    genre_taken: Counter = Counter()
    popular_here_cap = max(2, size // 4)
    entries, popular_here = [], 0
    for tier, _, rec, evidence, detail in tiered:
        if len(entries) >= size:
            break
        if genre_taken[_top_genre(rec)] >= MAX_PER_GENRE or (tier == 3 and popular_here >= popular_here_cap):
            continue
        genre_taken[_top_genre(rec)] += 1
        popular_here += tier == 3
        entries.append(_entry(
            rec, "local", f"{detail}. Genres: {', '.join(rec['genres'][:2])}.",
            qloo_affinity=rec.get("affinity"),
            group_fit_basis="Not scored for the group: local mode ranks by local evidence",
            local_evidence=evidence,
        ))

    notes = []
    if excluded_foreign:
        notes.append(f"Left out {len(excluded_foreign)} artists popular there but born elsewhere.")
    if country is None:
        notes.append("Could not determine the destination's country, so birthplace checks were limited to the city.")
    return _result(
        "local", None, " ".join(notes) or None, entries=entries, size=size,
        selection={"destination": destination or location, "country": country},
        summary={
            "local_sound": sorted(characteristic, key=lambda g: -genre_counts[g])[:5],
            "candidates_from_qloo": len(recs),
            "excluded_born_elsewhere": excluded_foreign[:10],
            "evidence_counts": dict(Counter(e["local_evidence"] for e in entries)),
        },
    )


# =====================================================================
# Public entry point
# =====================================================================

def _result(mode: str, status: Optional[str], message: Optional[str], *, entries: Optional[List[Dict[str, Any]]] = None,
            size: int = DEFAULT_SIZE, summary: Optional[Dict[str, Any]] = None,
            selection: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    entries = entries or []
    if status is None:
        status = "empty" if not entries else ("sparse" if len(entries) < min(size, 6) else "ok")
        if status == "empty" and not message:
            message = "Qloo returned no music artists with usable data for this request."
        if status == "sparse":
            message = ((message + " ") if message else "") + f"Only {len(entries)} matching artists were found."
    return {
        "mode": mode, "mode_label": MODE_LABELS[mode], "status": status, "message": message,
        "selection": selection or {}, "entries": entries, "summary": summary or {},
    }


_SOURCES = {
    "artists_genres_popularity": "Qloo",
    "qloo_affinity": "Qloo API value for this request's signals",
    "qloo_affinity_by_member": "Qloo API value for each member's favourite artists",
    "group_fit": "Common Ground calculation (see group_fit_basis on each artist)",
    "member_fit": "Common Ground calculation: 1.0 for a member's own favourites, otherwise the percentile of Qloo's affinity among the candidates",
    "tracks_and_links": "Apple iTunes Search catalogue (tracks, previews, Apple Music links); Spotify and Last.fm artist links come from Qloo's external IDs",
}


def build_playlist(
    mode: str,
    profiles: List[Profile],
    destination: str,
    destination_query: Optional[str] = None,
    vibes: Optional[List[str]] = None,
    size: int = DEFAULT_SIZE,
) -> Dict[str, Any]:
    """Builds a group playlist in one of the three modes. Never raises for service problems:
    those come back as status 'unavailable' with an explanation.
    """
    if mode not in MODE_LABELS:
        raise ValueError(f"Unknown music mode '{mode}'. Choose from: {', '.join(MODE_LABELS)}.")
    size = max(6, min(20, int(size or DEFAULT_SIZE)))

    if is_qloo_mock_mode():
        result = _result(mode, "unavailable",
                         "Music recommendations use the live Qloo API, but the app is running in offline mock mode.", size=size)
    else:
        try:
            if mode == "vibes":
                result = _build_vibes(vibes or [], size)
            elif mode == "favourites":
                result = _build_favourites(profiles, size)
            else:
                result = _build_local(destination, destination_query, size)
        except QlooError as e:
            result = _result(mode, "unavailable", f"Qloo is unavailable right now: {str(e).splitlines()[0]}", size=size)

    if result["entries"]:
        catalog = _attach_tracks(result["entries"])
    else:
        catalog = {"provider": PROVIDER, "status": "not_used", "verified_tracks": 0, "artists_checked": 0}
    for entry in result["entries"]:
        entry.pop("_rec", None)

    if catalog["status"] in ("unavailable", "partial"):
        result["message"] = ((result["message"] + " ") if result["message"] else "") + \
            "Track lookup was unavailable for some artists, so they show artist links only."
    elif catalog["status"] == "disabled":
        result["message"] = ((result["message"] + " ") if result["message"] else "") + \
            "Track lookup is disabled (MUSIC_CATALOG=off), so only artist links are shown."

    result.update({"sources": _SOURCES, "catalog": catalog, "generated_at": datetime.now(timezone.utc).isoformat()})
    return MusicPlaylist.model_validate(result).model_dump()


def validate_request(mode: str, vibes: Optional[List[str]]) -> List[str]:
    """Validates a playlist request, returning the cleaned vibe list. Raises ValueError with a
    user-facing message for an unknown mode, unknown vibes, or vibes mode without any vibe."""
    if mode not in MODE_LABELS:
        raise ValueError(f"Unknown music mode '{mode}'. Choose from: {', '.join(MODE_LABELS)}.")
    cleaned = list(dict.fromkeys(vibes or []))
    unknown = [v for v in cleaned if v not in VIBES]
    if unknown:
        raise ValueError(f"Unknown vibe(s): {', '.join(unknown)}. Choose from: {', '.join(VIBES)}.")
    if mode == "vibes" and not cleaned:
        raise ValueError("Pick at least one vibe for Vibes mode.")
    return cleaned


def safe_build_playlist(*args: Any, timeout_seconds: Optional[float] = None, **kwargs: Any) -> Dict[str, Any]:
    """Like build_playlist but converts every error into an explanatory playlist, so a music
    problem can never fail trip generation. With timeout_seconds, a slow build is abandoned
    (it finishes harmlessly in the background) and reported, so it cannot delay the caller."""
    mode = args[0] if args else kwargs.get("mode", "favourites")

    def unavailable(status: str, message: str) -> Dict[str, Any]:
        return MusicPlaylist.model_validate({
            "mode": mode if mode in MODE_LABELS else "favourites",
            "mode_label": MODE_LABELS.get(mode, "Favourites"),
            "status": status,
            "message": message,
            "sources": _SOURCES,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }).model_dump()

    def run() -> Dict[str, Any]:
        try:
            return build_playlist(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            if isinstance(e, ValueError):
                return unavailable("empty", str(e))
            return unavailable("unavailable", f"The playlist could not be built ({type(e).__name__}).")

    if timeout_seconds is None:
        return run()

    box: Dict[str, Dict[str, Any]] = {}
    worker = threading.Thread(target=lambda: box.update(result=run()), daemon=True)
    worker.start()
    worker.join(timeout_seconds)
    if "result" in box:
        return box["result"]
    return unavailable(
        "unavailable",
        f"Building the playlist took longer than {int(timeout_seconds)} seconds, so it was skipped. "
        "Use the playlist panel to build it again.",
    )
