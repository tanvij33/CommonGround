"use client";

import React, { useState } from "react";
import {
  Music,
  Loader2,
  AlertCircle,
  ExternalLink,
  Info,
  Disc3,
  Sparkles,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Chip } from "@/components/ui/Chip";
import {
  api,
  MusicEntry,
  MusicMode,
  MusicPlaylist,
  MUSIC_MODES,
  MUSIC_VIBES,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const MAX_VIBES = 4;

const ROLE_LABELS: Record<string, { label: string; variant: "brand" | "spotlight" | "bridge" | "success" | "default" }> = {
  spotlight: { label: "Member spotlight", variant: "spotlight" },
  shared: { label: "Shared pick", variant: "bridge" },
  discovery: { label: "New discovery", variant: "brand" },
  vibe_match: { label: "Matches several vibes", variant: "bridge" },
  vibe_pick: { label: "Vibe pick", variant: "brand" },
  local: { label: "Local", variant: "success" },
};

const EVIDENCE_LABELS: Record<string, { label: string; variant: "success" | "warning" | "default" }> = {
  born_in_city: { label: "Born in this city", variant: "success" },
  born_in_country: { label: "Born in this country", variant: "success" },
  local_genre: { label: "Local sound", variant: "success" },
  popular_here: { label: "Popular here · origin unconfirmed", variant: "warning" },
};

function fmt(value?: number | null): string {
  return typeof value === "number" ? value.toFixed(2) : "—";
}

function selectionSummary(music: MusicPlaylist): string | null {
  if (music.mode === "vibes" && music.selection.vibe_labels?.length) return music.selection.vibe_labels.join(" + ");
  if (music.mode === "local" && music.selection.destination) return `Artists tied to ${music.selection.destination}`;
  if (music.mode === "favourites" && music.selection.members?.length) {
    const n = music.selection.members.length;
    return n === 1 ? `${music.selection.members[0]}'s favourites` : `${n} members' favourites`;
  }
  return null;
}

function EntryCard({ entry, index, mode }: { entry: MusicEntry; index: number; mode: MusicMode }) {
  const role = ROLE_LABELS[entry.role];
  const evidence = entry.local_evidence ? EVIDENCE_LABELS[entry.local_evidence] : null;
  const art = entry.track?.artwork_url || entry.image_url || null;
  const memberFit = Object.entries(entry.scores.member_fit);
  const hasMemberDetail = mode === "favourites" && (memberFit.length > 0 || entry.scores.fit_unknown_members.length > 0);

  return (
    <div className="p-3.5 rounded-2xl bg-white border border-borderline/70 space-y-2.5">
      <div className="flex items-start gap-3">
        <div className="w-14 h-14 rounded-xl bg-subtle border border-borderline/60 overflow-hidden shrink-0 flex items-center justify-center text-ink-400">
          {art ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={art} alt="" className="w-full h-full object-cover" referrerPolicy="no-referrer" />
          ) : (
            <Disc3 className="w-6 h-6" />
          )}
        </div>

        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="text-[11px] font-mono text-ink-400">{String(index + 1).padStart(2, "0")}</span>
            <h4 className="text-sm font-bold text-nearblack tracking-tight break-words">{entry.artist}</h4>
            {role && (
              <Chip variant={role.variant} size="sm">
                {role.label}
              </Chip>
            )}
            {evidence && (
              <Chip variant={evidence.variant} size="sm">
                {evidence.label}
              </Chip>
            )}
          </div>

          {entry.genres.length > 0 && (
            <p className="text-[11px] font-mono text-ink-500 truncate">{entry.genres.slice(0, 3).join(" • ")}</p>
          )}

          {entry.track ? (
            <p className="text-xs text-nearblack flex items-center gap-1.5">
              <Music className="w-3 h-3 text-brand-violet shrink-0" />
              <span className="font-semibold truncate">{entry.track.title}</span>
              {entry.track.album && <span className="text-ink-400 truncate hidden sm:inline">· {entry.track.album}</span>}
            </p>
          ) : (
            <p className="text-[11px] text-ink-500">
              No verified track found.
              {entry.known_for.length > 0 && <> Known for (per Qloo, unverified): {entry.known_for.slice(0, 3).join(", ")}.</>}
            </p>
          )}
        </div>
      </div>

      {entry.track?.preview_url && (
        <audio
          controls
          preload="none"
          src={entry.track.preview_url}
          className="w-full h-8"
          aria-label={`Preview of ${entry.track.title}`}
          onPlay={(e) => {
            // one preview at a time
            document.querySelectorAll("audio").forEach((other) => {
              if (other !== e.currentTarget) other.pause();
            });
          }}
        />
      )}

      <p className="text-[11px] text-ink-500 leading-relaxed">{entry.why}</p>

      {entry.links.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {entry.links.map((link) => (
            <a
              key={link.url}
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[11px] font-medium px-2.5 py-1 rounded-pill bg-subtle border border-borderline/70 text-ink-700 hover:bg-borderline transition-colors"
            >
              {link.kind === "track" ? "Play on " : "Artist on "}
              {link.label}
              <ExternalLink className="w-3 h-3" />
            </a>
          ))}
        </div>
      )}

      <div className="pt-2 border-t border-borderline/50 grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1 text-[10px] font-mono text-ink-500">
        <div>
          <span className="text-ink-400 uppercase">Qloo (API)</span>
          <div>
            affinity {fmt(entry.scores.qloo_affinity)} · popularity {fmt(entry.scores.qloo_popularity)}
          </div>
        </div>
        <div>
          <span className="text-ink-400 uppercase">Common Ground (calculated)</span>
          <div>
            {mode === "vibes"
              ? `matches ${entry.vibes.length} selected vibe${entry.vibes.length === 1 ? "" : "s"}`
              : entry.scores.group_fit != null
              ? `group fit ${fmt(entry.scores.group_fit)}`
              : "not scored for the group"}
          </div>
        </div>
        {hasMemberDetail && (
          <div className="sm:col-span-2 flex flex-wrap gap-x-3 gap-y-0.5">
            {memberFit.map(([name, value]) => (
              <span key={name}>
                {name} {fmt(value)}
              </span>
            ))}
            {entry.scores.fit_unknown_members.map((name) => (
              <span key={name} className="text-ink-400">
                {name} —
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export interface MusicPlaylistPanelProps {
  tripId: string;
  music?: MusicPlaylist;
  onChange?: (music: MusicPlaylist) => void;
}

export const MusicPlaylistPanel: React.FC<MusicPlaylistPanelProps> = ({ tripId, music, onChange }) => {
  const [mode, setMode] = useState<MusicMode>(music?.mode ?? "favourites");
  const [vibes, setVibes] = useState<string[]>(music?.mode === "vibes" ? music.selection.vibes ?? [] : []);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const modeInfo = MUSIC_MODES.find((m) => m.id === mode)!;
  const needsVibes = mode === "vibes" && vibes.length === 0;

  const toggleVibe = (id: string) => {
    setVibes((current) =>
      current.includes(id) ? current.filter((v) => v !== id) : current.length >= MAX_VIBES ? current : [...current, id]
    );
  };

  const build = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.buildPlaylist(tripId, { mode, vibes: mode === "vibes" ? vibes : [] });
      onChange?.(result);
    } catch (err: any) {
      setError(err?.message || "Could not reach the server.");
    } finally {
      setLoading(false);
    }
  };

  const summary = music ? selectionSummary(music) : null;
  const verified = music?.catalog?.verified_tracks ?? 0;
  const checked = music?.catalog?.artists_checked ?? 0;
  const avgFit = music?.mode === "favourites" ? (music.summary?.average_member_fit as Record<string, number> | undefined) : undefined;

  return (
    <Card variant="default" padding="md" className="space-y-5 sm:p-8">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-brand-violet flex items-center justify-center text-white">
            <Music className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-base font-bold text-nearblack tracking-tight">Group Soundtrack</h3>
            <p className="text-[11px] font-mono text-ink-500">Artists and tracks from Qloo, verified in a music catalogue</p>
          </div>
        </div>
        {music && (
          <Chip variant="brand" size="md" icon={<Sparkles className="w-3 h-3" />}>
            {music.mode_label}
            {summary ? ` · ${summary}` : ""}
          </Chip>
        )}
      </div>

      {/* Mode selector */}
      <div className="space-y-3">
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Playlist mode">
          {MUSIC_MODES.map((m) => (
            <button
              key={m.id}
              type="button"
              role="tab"
              aria-selected={mode === m.id}
              onClick={() => setMode(m.id)}
              className={cn(
                "text-xs px-3.5 py-1.5 rounded-pill border transition-colors font-medium",
                mode === m.id
                  ? "bg-brand-violet text-white border-brand-violet"
                  : "bg-subtle text-ink-700 border-borderline hover:bg-borderline"
              )}
            >
              {m.label}
            </button>
          ))}
        </div>
        <p className="text-[11px] text-ink-500">{modeInfo.blurb}</p>

        {mode === "vibes" && (
          <div className="space-y-1.5">
            <div className="flex flex-wrap gap-1.5">
              {MUSIC_VIBES.map((v) => {
                const active = vibes.includes(v.id);
                return (
                  <button
                    key={v.id}
                    type="button"
                    aria-pressed={active}
                    onClick={() => toggleVibe(v.id)}
                    className={cn(
                      "text-xs px-2.5 py-0.5 rounded-pill border transition-colors",
                      active
                        ? "bg-brand-violet text-white border-brand-violet font-semibold"
                        : "bg-subtle text-ink-700 border-borderline hover:bg-borderline"
                    )}
                  >
                    {v.label}
                  </button>
                );
              })}
            </div>
            <p className="text-[10px] font-mono text-ink-400">
              Choose 1–{MAX_VIBES} vibes ({vibes.length} selected)
            </p>
          </div>
        )}

        <Button
          variant="primary"
          size="sm"
          onClick={build}
          disabled={loading || needsVibes}
          icon={loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Music className="w-3.5 h-3.5" />}
        >
          {loading ? "Building from Qloo…" : music && music.mode === mode ? `Rebuild ${modeInfo.label} playlist` : `Build ${modeInfo.label} playlist`}
        </Button>
        {needsVibes && <p className="text-[11px] text-amber-700">Pick at least one vibe to continue.</p>}
      </div>

      {error && (
        <div className="p-3 rounded-2xl bg-rose-50 border border-rose-200 text-xs text-rose-700 flex items-start gap-2" role="alert">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* Nothing built yet */}
      {!music && !error && !loading && (
        <p className="text-xs text-ink-500 p-4 rounded-2xl bg-subtle/60 border border-borderline/50">
          No playlist has been built for this trip yet. Choose a mode above and build one.
        </p>
      )}

      {music && (
        <div className={cn("space-y-4 transition-opacity", loading && "opacity-50")}>
          {music.message && (
            <div
              className={cn(
                "p-3 rounded-2xl text-xs flex items-start gap-2 border",
                music.status === "ok"
                  ? "bg-subtle/60 border-borderline/60 text-ink-700"
                  : "bg-amber-50 border-amber-200 text-amber-900"
              )}
            >
              <Info className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{music.message}</span>
            </div>
          )}

          {music.entries.length === 0 && (
            <p className="text-xs text-ink-500">
              {music.status === "unavailable"
                ? "No playlist is shown because the music services could not be used."
                : "No artists to show for this selection."}
            </p>
          )}

          {avgFit && Object.keys(avgFit).length > 0 && (
            <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono text-ink-500">
              <span className="uppercase text-ink-400">Average fit per member (calculated)</span>
              {Object.entries(avgFit).map(([name, value]) => (
                <Chip key={name} variant="default" size="sm">
                  {name} {fmt(value)}
                </Chip>
              ))}
            </div>
          )}

          {music.mode === "local" && Array.isArray(music.summary?.local_sound) && music.summary.local_sound.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono text-ink-500">
              <span className="uppercase text-ink-400">Sounds that stand out here (from Qloo)</span>
              {(music.summary.local_sound as string[]).map((g) => (
                <Chip key={g} variant="success" size="sm">
                  {g}
                </Chip>
              ))}
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {music.entries.map((entry, i) => (
              <EntryCard key={entry.qloo_id} entry={entry} index={i} mode={music.mode} />
            ))}
          </div>

          {music.entries.length > 0 && (
            <div className="text-[10px] font-mono text-ink-400 space-y-0.5 pt-1">
              <p>
                {music.catalog.status === "ok" || music.catalog.status === "partial"
                  ? `${verified} of ${checked} artists have a track verified in the ${music.catalog.provider === "apple_music" ? "Apple Music" : "music"} catalogue.`
                  : "Track lookup was not available; only artist links are shown."}
              </p>
              <p>Qloo supplies artists, genres, popularity and affinity. Fit and match scores are calculated by Common Ground. Playback links open the artist or track on the listed service.</p>
            </div>
          )}
        </div>
      )}
    </Card>
  );
};
