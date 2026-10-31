"""Tests for the three-mode music recommendation engine.

Every Qloo and catalogue call is mocked: no network, no API quota, no real database writes
(the API tests only create rows with unique IDs).
"""

from contextlib import contextmanager
from unittest.mock import patch, MagicMock

import pytest

from backend import music
from backend.models import Profile, ProfileConstraints
from backend.music import build_playlist, safe_build_playlist, validate_request, VIBES
from backend.music_catalog import find_track, normalize_title
from backend.qloo_client import (
    QlooMissingApiKeyError,
    QlooNetworkError,
    _slim_artist,
    normalize_music_name,
    resolve_artist,
)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def rec(i, name, genres=("Indie Rock",), pop=0.9, aff=None, songs=("Hit",), birth=None, aliases=(), spotify=True):
    return {
        "id": f"ID-{i:04d}", "name": name, "aliases": list(aliases), "affinity": aff, "popularity": pop,
        "genres": list(genres), "notable_songs": list(songs), "place_of_birth": birth, "image_url": None,
        "spotify_id": f"{i:022d}" if spotify else None, "lastfm_id": name.lower().replace(" ", "%20") if spotify else None,
        "musicbrainz_id": f"mb-{i}",
    }


def fake_track(artist_names, notable_songs):
    return ({"title": (notable_songs or ["Catalog Song"])[0], "album": "Album", "artwork_url": None,
             "preview_url": "https://audio.example/p.m4a", "listen_url": f"https://music.apple.com/{artist_names[0].replace(' ', '-')}",
             "provider": "apple_music", "basis": "qloo_notable_song"}, "ok")


@contextmanager
def qloo(**overrides):
    """Patches every external call used by the music engine (live mode, working catalogue by default)."""
    defaults = dict(
        is_qloo_mock_mode=MagicMock(return_value=False),
        resolve_artist=MagicMock(return_value=None),
        resolve_favorite=MagicMock(return_value=None),
        get_artist_insights=MagicMock(return_value=[]),
        get_place_affinities=MagicMock(return_value={}),
        get_destination_country=MagicMock(return_value="Portugal"),
        find_track=MagicMock(side_effect=fake_track),
    )
    defaults.update(overrides)
    with patch.multiple("backend.music", **defaults):
        yield defaults


def profiles(*specs):
    return [Profile(name=n, favorites=[{"name": f, "type": "artist"} for f in favs], constraints=ProfileConstraints())
            for n, favs in specs]


# ---------------------------------------------------------------------
# Qloo artist plumbing
# ---------------------------------------------------------------------

def test_slim_artist_normalizes_id_case_and_keeps_only_verified_fields():
    raw = {"entity_id": "abcdef12-0000-0000-0000-000000000001", "name": "Carminho", "popularity": 0.9,
           "query": {"affinity": 0.8}, "external": {"spotify": [{"id": "x" * 22}], "lastfm": [{"id": "carminho"}]},
           "properties": {"primary_genres": ["Fado"], "notable_songs": ["Perdao"], "biography": "very long text", "aliases": ["Carminho X"]}}
    slim = _slim_artist(raw)
    assert slim["id"] == "ABCDEF12-0000-0000-0000-000000000001"  # search returns lower case, insights upper case
    assert slim["genres"] == ["Fado"] and slim["spotify_id"] == "x" * 22 and slim["affinity"] == 0.8
    assert "biography" not in slim


def test_resolve_artist_requires_exact_name_or_alias_match():
    payload = {"results": [
        _slim_artist({"entity_id": "a1", "name": "Metallica and Ozzy Osbourne", "popularity": 0.6, "properties": {"primary_genres": ["Metal"]}}),
        _slim_artist({"entity_id": "a2", "name": "On a Friday", "popularity": 0.9, "properties": {"aliases": ["Radiohead"], "primary_genres": ["Rock"]}}),
    ]}
    with patch("backend.qloo_client._make_request", return_value=payload):
        assert resolve_artist("Metallica") is None                      # near miss is rejected, not guessed
        hit = resolve_artist("Radiohead")                               # Qloo stores this act under its old name
    assert hit["id"] == "A2" and hit["matched_name"] == "Radiohead"


def test_normalize_music_name_ignores_case_accents_and_punctuation():
    assert normalize_music_name("Beyoncé!") == normalize_music_name("beyonce")


# ---------------------------------------------------------------------
# Service problems
# ---------------------------------------------------------------------

@pytest.mark.parametrize("mode", ["vibes", "favourites", "local"])
def test_mock_mode_is_reported_not_faked(mode):
    with qloo(is_qloo_mock_mode=MagicMock(return_value=True)) as m:
        result = build_playlist(mode, profiles(("A", ["X"])), "Lisbon", vibes=["chill"])
    assert result["status"] == "unavailable" and result["entries"] == []
    assert "mock mode" in result["message"]
    m["get_artist_insights"].assert_not_called()


@pytest.mark.parametrize("mode", ["vibes", "favourites", "local"])
@pytest.mark.parametrize("error", [QlooNetworkError("Failed to connect to Qloo API"), QlooMissingApiKeyError("QLOO_API_KEY missing")])
def test_qloo_failures_become_unavailable_playlists(mode, error):
    with qloo(resolve_artist=MagicMock(side_effect=error), get_artist_insights=MagicMock(side_effect=error)):
        result = build_playlist(mode, profiles(("A", ["X"])), "Lisbon", vibes=["chill"])
    assert result["status"] == "unavailable" and result["entries"] == []
    assert result["message"].startswith("Qloo is unavailable")
    assert result["mode"] == mode


def test_safe_build_playlist_never_raises():
    with patch("backend.music.build_playlist", side_effect=RuntimeError("boom")):
        result = safe_build_playlist("favourites", [], "Lisbon")
    assert result["status"] == "unavailable" and "RuntimeError" in result["message"]


# ---------------------------------------------------------------------
# VIBES
# ---------------------------------------------------------------------

def test_validate_request_rejects_bad_input():
    with pytest.raises(ValueError, match="at least one vibe"):
        validate_request("vibes", [])
    with pytest.raises(ValueError, match="Unknown vibe"):
        validate_request("vibes", ["sad-trombone"])
    with pytest.raises(ValueError, match="Unknown music mode"):
        validate_request("karaoke", [])
    assert validate_request("favourites", []) == []


def test_every_vibe_maps_to_qloo_artist_tags():
    assert len(VIBES) == 8
    for cfg in VIBES.values():
        assert cfg["tags"] and all(t.startswith("urn:tag:") for t in cfg["tags"])


def test_vibes_use_the_vibe_tags_as_qloo_signals_and_filter_non_music():
    def insights(signal_tag_ids=None, **kw):
        if signal_tag_ids == VIBES["chill"]["tags"]:
            return [rec(1, "Zero 7", ("Downtempo",), aff=0.999), rec(2, "A Comedian", ("Stand-up Comedy",), songs=()),
                    rec(3, "No Data", ("Ambient",), songs=(), spotify=False)]
        return [rec(4, "Flo Rida", ("Rap",), aff=0.998)]

    with qloo(get_artist_insights=MagicMock(side_effect=insights)) as m:
        result = build_playlist("vibes", [], "Lisbon", vibes=["chill", "party"])
    names = {e["artist"] for e in result["entries"]}
    assert names == {"Zero 7", "Flo Rida"}                       # comedian and data-less act dropped
    assert result["mode"] == "vibes" and result["selection"]["vibe_labels"] == ["Chill", "Party"]
    used = [c.kwargs["signal_tag_ids"] for c in m["get_artist_insights"].call_args_list]
    assert VIBES["chill"]["tags"] in used and VIBES["party"]["tags"] in used
    entry = next(e for e in result["entries"] if e["artist"] == "Zero 7")
    assert entry["vibes"] == ["chill"] and "Chill" in entry["why"]
    assert entry["scores"]["qloo_affinity"] == 0.999            # API value, kept separate from our share
    assert entry["scores"]["group_fit"] == 0.5 and "vibes" in entry["scores"]["group_fit_basis"]


def test_artist_matching_several_vibes_ranks_first_and_genres_are_capped():
    shared = rec(1, "Bridge Act", ("Pop",), aff=0.99)
    chill = [shared] + [rec(10 + i, f"Chill {i}", ("Ambient",), aff=0.99) for i in range(8)]
    party = [shared] + [rec(30 + i, f"Party {i}", ("House",), aff=0.99) for i in range(8)]
    insights = lambda signal_tag_ids=None, **kw: chill if signal_tag_ids == VIBES["chill"]["tags"] else party
    with qloo(get_artist_insights=MagicMock(side_effect=insights)):
        result = build_playlist("vibes", [], "Lisbon", vibes=["chill", "party"], size=12)
    assert result["entries"][0]["artist"] == "Bridge Act" and result["entries"][0]["role"] == "vibe_match"
    assert result["entries"][0]["scores"]["group_fit"] == 1.0
    genres = [e["genres"][0] for e in result["entries"]]
    assert genres.count("Ambient") <= 3 and genres.count("House") <= 3
    assert len({e["qloo_id"] for e in result["entries"]}) == len(result["entries"])


def test_vibes_sparse_and_empty_results_are_explained():
    one = [rec(1, "Only Act", ("Ambient",), aff=0.99)]
    with qloo(get_artist_insights=MagicMock(return_value=one)):
        sparse = build_playlist("vibes", [], "Lisbon", vibes=["chill"])
    assert sparse["status"] == "sparse" and len(sparse["entries"]) == 1 and "Only 1" in sparse["message"]

    with qloo(get_artist_insights=MagicMock(return_value=[])):
        empty = build_playlist("vibes", [], "Lisbon", vibes=["romantic"])
    assert empty["status"] == "empty" and empty["entries"] == [] and "no music artists" in empty["message"]
    assert empty["summary"]["vibes_without_results"] == ["Romantic"]


# ---------------------------------------------------------------------
# FAVOURITES
# ---------------------------------------------------------------------

SEEDS = {
    "Burial": rec(100, "Burial", ("Dubstep",)),
    "Black Sabbath": rec(101, "Black Sabbath", ("Heavy Metal",)),
    "Norah Jones": rec(102, "Norah Jones", ("Vocal Jazz",)),
}
POOL = ([rec(200 + i, f"Shared {i}", (f"Shared Genre {i % 4}",), pop=0.95) for i in range(6)]
        + [rec(300 + i, f"Aisha Find {i}", (f"Electro {i % 4}",), pop=0.9) for i in range(4)]
        + [rec(400 + i, f"Rohan Find {i}", (f"Metal {i % 4}",), pop=0.9) for i in range(4)]
        + [rec(500 + i, f"Meera Find {i}", (f"Jazz {i % 4}",), pop=0.9) for i in range(4)])
LIKES = {"ID-0100": "Aisha Find", "ID-0101": "Rohan Find", "ID-0102": "Meera Find"}


def affinities(signal_ids, entity_ids, entity_type=None, **limits):
    liked = LIKES[signal_ids[0]]
    by_id = {r["id"]: r for r in POOL + list(SEEDS.values())}
    return {i: (0.95 if (by_id[i]["name"].startswith(liked) or by_id[i]["name"].startswith("Shared")) else 0.60 - 0.01 * int(i[-2:]) % 7)
            for i in entity_ids if i in by_id}


def fav_insights(signal_entity_ids=None, **kw):
    if signal_entity_ids and len(signal_entity_ids) == 1:
        prefix = LIKES[signal_entity_ids[0]]
        return [r for r in POOL if r["name"].startswith((prefix, "Shared"))]
    return list(POOL)


def run_favourites(size=12, group=None, **overrides):
    group = group or profiles(("Aisha", ["Burial"]), ("Rohan", ["Black Sabbath", "Metallica"]), ("Meera", ["Norah Jones"]))
    kwargs = dict(
        resolve_artist=MagicMock(side_effect=lambda n: SEEDS.get(n)),
        get_artist_insights=MagicMock(side_effect=fav_insights),
        get_place_affinities=MagicMock(side_effect=affinities),
    )
    kwargs.update(overrides)
    with qloo(**kwargs) as m:
        return build_playlist("favourites", group, "Lisbon", size=size), m


def test_favourites_give_every_member_a_spotlight_and_balance_the_rest():
    result, _ = run_favourites()
    entries = result["entries"]
    assert result["status"] == "ok" and len(entries) == 12
    spotlights = {e["artist"] for e in entries if e["role"] == "spotlight"}
    assert spotlights == {"Burial", "Black Sabbath", "Norah Jones"}
    roles = result["summary"]["roles"]
    assert roles["shared"] >= 2 and roles["discovery"] >= 2
    assert len({e["qloo_id"] for e in entries}) == 12                       # no duplicates
    assert result["summary"]["fit_spread"] < 0.25                            # nobody dominates
    targets = {e["why"].split("chosen for ")[1].split(" ")[0] for e in entries if e["role"] == "discovery"}
    assert len(targets) >= 2                                                 # discoveries rotate between members


def test_favourites_separate_api_scores_from_calculated_fit():
    result, _ = run_favourites()
    discovery = next(e for e in result["entries"] if e["role"] == "discovery")
    scores = discovery["scores"]
    assert set(scores["member_fit"]) <= {"Aisha", "Rohan", "Meera"} and scores["group_fit"] is not None
    assert "lowest member fit" in scores["group_fit_basis"]
    assert scores["qloo_affinity_by_member"]                                  # raw Qloo values, not our percentiles
    own = next(e for e in result["entries"] if e["artist"] == "Burial")
    assert own["scores"]["member_fit"]["Aisha"] == 1.0 and "Aisha" not in own["scores"]["qloo_affinity_by_member"]
    assert [l["label"] for l in own["links"]][:1] == ["Spotify"] and own["track"]["listen_url"].startswith("https://music.apple.com")


def test_favourites_report_unmatched_artists_instead_of_guessing():
    result, _ = run_favourites()
    assert result["summary"]["unresolved"] == {"Rohan": ["Metallica"]}
    assert "Metallica" in result["message"]


def test_favourites_member_without_any_signal_is_flagged():
    group = profiles(("Aisha", ["Burial"]), ("Ghost", ["Nobody Known"]))
    result, _ = run_favourites(group=group)
    assert result["summary"]["members_without_signal"] == ["Ghost"]
    assert "Ghost" in result["message"] and result["status"] in ("ok", "sparse")


def test_favourites_empty_when_nothing_resolves():
    result, m = run_favourites(resolve_artist=MagicMock(return_value=None))
    assert result["status"] == "empty" and result["entries"] == []
    assert "could be matched" in result["message"]
    m["get_artist_insights"].assert_not_called()


def test_favourites_unknown_affinity_is_not_displayed_as_a_score():
    result, _ = run_favourites(get_place_affinities=MagicMock(return_value={}))
    entry = next(e for e in result["entries"] if e["role"] == "discovery")
    assert entry["scores"]["fit_unknown_members"] and entry["scores"]["member_fit"] == {}
    assert result["summary"]["unknown_affinity_count"] > 0


def test_same_act_under_two_qloo_entities_is_not_duplicated():
    twin = {**POOL[0], "id": "ID-9999", "name": "Shared 0 (native script)"}      # same Spotify + MusicBrainz IDs
    result, _ = run_favourites(get_artist_insights=MagicMock(side_effect=lambda **kw: fav_insights(**kw) + [twin]))
    assert "ID-9999" not in {e["qloo_id"] for e in result["entries"]}


# ---------------------------------------------------------------------
# LOCAL MUSIC
# ---------------------------------------------------------------------

LISBON = [rec(1, "Ana Moura", ("Fado",), birth="Santarem, Portugal", aff=1.0), rec(2, "Carminho", ("Fado",), aff=1.0),
          rec(3, "Gisela Joao", ("Fado",), aff=1.0), rec(4, "Madonna", ("Pop", "Dance Pop"), aff=1.0),
          rec(5, "Anitta", ("Funk Carioca",), birth="Rio de Janeiro, Brazil", aff=1.0),
          rec(6, "Conan Osiris", ("Experimental Pop",), birth="Lisbon, Lisboa, Portugal", aff=1.0)]
TOKYO = [rec(11, "Gen Hoshino", ("J-Pop",), birth="Tokyo, Japan"), rec(12, "Chara", ("J-Pop",)), rec(13, "Madonna", ("Pop",))]


def run_local(destination, recs, country):
    with qloo(get_artist_insights=MagicMock(return_value=recs), get_destination_country=MagicMock(return_value=country)) as m:
        return build_playlist("local", [], destination, destination_query=f"{destination}, X", size=6), m


def test_local_uses_the_destination_as_the_qloo_location_signal():
    _, m = run_local("Lisbon", LISBON, "Portugal")
    assert m["get_artist_insights"].call_args.kwargs["location_query"] == "Lisbon, X"


def test_local_prefers_birthplace_then_local_genre_and_labels_the_rest_honestly():
    result, _ = run_local("Lisbon", LISBON, "Portugal")
    by_name = {e["artist"]: e for e in result["entries"]}
    assert by_name["Conan Osiris"]["local_evidence"] == "born_in_city"
    assert by_name["Ana Moura"]["local_evidence"] == "born_in_country"
    assert by_name["Carminho"]["local_evidence"] == "local_genre" and "Fado" in by_name["Carminho"]["why"]
    assert by_name["Madonna"]["local_evidence"] == "popular_here" and "not confirmed as local" in by_name["Madonna"]["why"]
    assert "Anitta" not in by_name and result["summary"]["excluded_born_elsewhere"] == ["Anitta"]
    assert result["summary"]["local_sound"] == ["Fado"]
    assert list(by_name)[:2] == ["Conan Osiris", "Ana Moura"]               # strongest evidence first
    assert by_name["Carminho"]["scores"]["group_fit"] is None                 # local mode makes no group-fit claim


def test_local_recommendations_change_with_the_destination():
    lisbon, _ = run_local("Lisbon", LISBON, "Portugal")
    tokyo, _ = run_local("Tokyo", TOKYO, "Japan")
    assert {e["artist"] for e in lisbon["entries"]}.isdisjoint({"Gen Hoshino", "Chara"})
    assert {e["artist"] for e in tokyo["entries"]}.isdisjoint({"Ana Moura", "Carminho", "Conan Osiris"})
    assert lisbon["selection"]["country"] == "Portugal" and tokyo["selection"]["country"] == "Japan"


def test_local_caps_unconfirmed_popular_artists():
    generic = [rec(50 + i, f"Global Star {i}", (f"Genre {i}",)) for i in range(10)]
    result, _ = run_local("Lisbon", generic, "Portugal")
    assert result["status"] == "sparse" and len(result["entries"]) == 2        # max(2, size // 4)


def test_local_without_destination_or_country_degrades_gracefully():
    with qloo():
        assert build_playlist("local", [], "", None)["status"] == "empty"
    result, _ = run_local("Lisbon", LISBON, None)
    assert "Could not determine the destination's country" in result["message"]
    # With no country to compare against, a known foreign birthplace cannot be judged: the act is
    # kept but never presented as confirmed local
    anitta = next(e for e in result["entries"] if e["artist"] == "Anitta")
    assert anitta["local_evidence"] == "popular_here" and "not confirmed as local" in anitta["why"]


# ---------------------------------------------------------------------
# Track catalogue
# ---------------------------------------------------------------------

SONGS = [
    {"artist": "Nuno Ribeiro", "title": "Rosa (feat. Conan Osiris)", "listen_url": "https://music.apple.com/1", "preview_url": "p1", "album": "a", "artwork_url": None},
    {"artist": "Conan Osiris", "title": "Telemóveis - Remastered 2020", "listen_url": "https://music.apple.com/2", "preview_url": "p2", "album": "b", "artwork_url": None},
    {"artist": "Conan Osiris", "title": "Other", "listen_url": "https://music.apple.com/3", "preview_url": None, "album": "c", "artwork_url": None},
]


def test_find_track_matches_qloo_notable_song_by_the_same_artist_only():
    with patch("backend.music_catalog._search_artist_songs", return_value=(SONGS, "ok")):
        track, status = find_track(["Conan Osiris"], ["Telemóveis"])
        fallback, _ = find_track(["Conan Osiris"], ["Not In Catalog"])
        collab_only, _ = find_track(["Nuno Ribeiro Jr"], ["Rosa"])
    assert status == "ok" and track["listen_url"] == "https://music.apple.com/2" and track["basis"] == "qloo_notable_song"
    assert fallback["basis"] == "catalog_listing" and fallback["artist"] == "Conan Osiris"
    assert collab_only is None                                                  # feature credits never count as the artist


def test_find_track_reports_service_problems_and_can_be_disabled(monkeypatch):
    with patch("backend.music_catalog._search_artist_songs", return_value=(None, "unavailable")):
        assert find_track(["X"], ["Y"]) == (None, "unavailable")
    monkeypatch.setenv("MUSIC_CATALOG", "off")
    assert find_track(["X"], ["Y"]) == (None, "disabled")


def test_normalize_title_drops_decorations():
    assert normalize_title("Wonderwall (Remastered)") == normalize_title("wonderwall")
    assert normalize_title("Heroes - 2017 Remaster") == normalize_title("Heroes")


def test_playlist_survives_catalogue_outage_with_artist_links_only():
    with qloo(get_artist_insights=MagicMock(return_value=[rec(i, f"Act {i}", (f"G{i}",)) for i in range(8)]),
              find_track=MagicMock(return_value=(None, "unavailable"))):
        result = build_playlist("vibes", [], "Lisbon", vibes=["indie"])
    assert result["status"] == "ok" and all(e["track"] is None for e in result["entries"])
    assert result["catalog"]["status"] == "unavailable" and "Track lookup was unavailable" in result["message"]
    assert all(any(l["kind"] == "artist" for l in e["links"]) for e in result["entries"])
    assert all(e["known_for"] for e in result["entries"])                       # Qloo's song titles still shown, unverified


# ---------------------------------------------------------------------
# HTTP API and trip generation
# ---------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from backend.main import app
    with TestClient(app) as c:
        yield c


def _lisbon_trip_with_plan(client, monkeypatch):
    """Creates a Lisbon trip with demo friends and a generated plan, using the offline catalog (no Qloo calls)."""
    monkeypatch.setenv("QLOO_MOCK", "true")
    trip_id = client.post("/trips", json={"name": "Music test", "destination": "Lisbon", "days": 1}).json()["id"]
    assert client.post(f"/trips/{trip_id}/demo-profiles").json()["added_count"] == 4
    assert client.post(f"/trips/{trip_id}/generate").status_code == 200
    return trip_id


def test_generation_still_works_and_embeds_an_honest_playlist(client, monkeypatch):
    trip_id = _lisbon_trip_with_plan(client, monkeypatch)
    assert client.get(f"/trips/{trip_id}").json()["status"] == "done"
    extras = client.get(f"/trips/{trip_id}/plan").json()["extras"]
    assert "playlist" not in extras                                              # the fabricated tracks are gone
    assert extras["music"]["mode"] == "favourites" and extras["music"]["status"] == "unavailable"
    assert extras["music"]["entries"] == []


def test_generate_validates_the_music_request(client):
    trip_id = client.post("/trips", json={"name": "Validation", "destination": "Lisbon", "days": 1}).json()["id"]
    client.post(f"/trips/{trip_id}/demo-profiles")
    bad = client.post(f"/trips/{trip_id}/generate", json={"music_mode": "vibes", "vibes": []})
    assert bad.status_code == 422 and "at least one vibe" in bad.json()["detail"]
    assert client.get(f"/trips/{trip_id}").json()["status"] == "waiting"           # nothing started


def test_playlist_endpoint_switches_modes_and_persists_the_choice(client, monkeypatch):
    trip_id = _lisbon_trip_with_plan(client, monkeypatch)
    monkeypatch.setenv("QLOO_MOCK", "false")
    acts = [rec(i, f"Act {i}", (f"Genre {i}",), aff=0.99) for i in range(8)]
    with qloo(get_artist_insights=MagicMock(return_value=acts)):
        resp = client.post(f"/trips/{trip_id}/playlist", json={"mode": "vibes", "vibes": ["chill", "indie"]})
        local = client.post(f"/trips/{trip_id}/playlist", json={"mode": "local"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "vibes" and body["status"] == "ok" and body["selection"]["vibes"] == ["chill", "indie"]
    assert local.json()["mode"] == "local"
    saved = client.get(f"/trips/{trip_id}/plan").json()["extras"]["music"]
    assert saved["mode"] == "local"                                                  # latest choice is stored in the plan


def test_playlist_endpoint_errors(client, monkeypatch):
    assert client.post("/trips/nope/playlist", json={"mode": "local"}).status_code == 404
    trip_id = client.post("/trips", json={"name": "No plan", "destination": "Lisbon", "days": 1}).json()["id"]
    assert client.post(f"/trips/{trip_id}/playlist", json={"mode": "local"}).status_code == 404   # no plan yet
    full = _lisbon_trip_with_plan(client, monkeypatch)
    assert client.post(f"/trips/{full}/playlist", json={"mode": "vibes", "vibes": []}).status_code == 422
    assert client.post(f"/trips/{full}/playlist", json={"mode": "vibes", "vibes": ["bogus"]}).status_code == 422
    assert client.post(f"/trips/{full}/playlist", json={"mode": "karaoke"}).status_code == 422


def test_music_options_endpoint(client):
    body = client.get("/music/options").json()
    assert [m["id"] for m in body["modes"]] == ["vibes", "favourites", "local"]
    assert {v["id"] for v in body["vibes"]} == set(VIBES)


def test_slow_playlist_is_abandoned_instead_of_delaying_generation():
    import time

    def slow(*a, **k):
        time.sleep(2)
        return {}

    with patch("backend.music.build_playlist", side_effect=slow):
        started = time.time()
        result = safe_build_playlist("favourites", [], "Lisbon", timeout_seconds=0.2)
    assert time.time() - started < 1.5
    assert result["status"] == "unavailable" and "took longer than" in result["message"]
    assert result["entries"] == []


def test_fast_playlist_is_returned_normally_with_a_time_budget():
    with qloo(get_artist_insights=MagicMock(return_value=[rec(1, "Only Act", ("Ambient",))])):
        result = safe_build_playlist("vibes", [], "Lisbon", vibes=["chill"], timeout_seconds=30)
    assert result["status"] == "sparse" and result["entries"][0]["artist"] == "Only Act"


def test_one_failed_affinity_request_degrades_the_playlist_but_is_reported(monkeypatch):
    import threading
    monkeypatch.setattr(music, "AFFINITY_CHUNK", 6)          # force several requests per member
    lock, calls = threading.Lock(), {"n": 0}

    def flaky(signal_ids, entity_ids, entity_type=None, **limits):
        with lock:
            calls["n"] += 1
            if calls["n"] == 2:
                raise QlooNetworkError("Failed to connect to Qloo API")
        return affinities(signal_ids, entity_ids)

    result, _ = run_favourites(get_place_affinities=MagicMock(side_effect=flaky))
    assert calls["n"] > 3                                                      # chunked into several requests
    assert result["status"] == "ok" and len(result["entries"]) == 12           # still a usable playlist
    assert "Some Qloo requests failed" in result["message"]
    assert len(result["summary"]["members_affinity_unavailable"]) == 1


def test_candidate_pool_is_trimmed_to_each_querys_best_results():
    many = [rec(1000 + i, f"Found {i}", (f"G{i % 9}",), aff=0.99 - i / 1000) for i in range(80)]
    seen = {"largest_chunk": 0}

    def tracking(signal_ids, entity_ids, entity_type=None, **limits):
        seen["largest_chunk"] = max(seen["largest_chunk"], len(entity_ids))
        return affinities(signal_ids, [i for i in entity_ids if i in {r["id"] for r in POOL + list(SEEDS.values())}])

    result, m = run_favourites(get_artist_insights=MagicMock(return_value=many),
                               get_place_affinities=MagicMock(side_effect=tracking))
    assert seen["largest_chunk"] <= 50
    assert result["summary"]["pool_size"] <= 14 * 3 + 20 + 3                    # per-call caps + seeds, not 80 x 4
    ids_requested = {i for call in m["get_place_affinities"].call_args_list for i in call.args[1]}
    assert "ID-1079" not in ids_requested                                       # lowest-ranked candidates never reach scoring


def test_music_requests_use_short_timeouts():
    from backend import qloo_client
    assert qloo_client.MUSIC_TIMEOUT <= 20 and qloo_client.MUSIC_RETRIES <= 2
    _, m = run_favourites()
    calls = m["get_place_affinities"].call_args_list
    assert calls, "affinity requests were expected"
    assert all(c.kwargs.get("timeout") == qloo_client.MUSIC_TIMEOUT and c.kwargs.get("max_retries") == qloo_client.MUSIC_RETRIES
               for c in calls)


def test_concurrent_qloo_logging_loses_no_entries(tmp_path, monkeypatch):
    """Without a write lock, simultaneous appends overwrite each other (about 15% of 300 entries were lost)."""
    import json
    from concurrent.futures import ThreadPoolExecutor
    from backend import qloo_client

    log = tmp_path / "qloo_log.jsonl"
    monkeypatch.setattr(qloo_client, "LOG_FILE_PATH", log)
    body = {"blob": "y" * 2000}
    with ThreadPoolExecutor(16) as pool:
        list(pool.map(lambda i: qloo_client._log_interaction("GET", "/v2/insights", {"i": i}, 200, body, from_cache=True), range(300)))
    lines = [line for line in log.read_bytes().decode("utf-8").splitlines() if line.strip()]
    assert sorted(json.loads(line)["params"]["i"] for line in lines) == list(range(300))
