import type { DownloadJob } from "../lib/types";

type JobCardProps = {
  job: DownloadJob;
  onCancel?: (jobId: string) => void;
  onOpenFolder?: (jobId: string) => void;
  onRetry?: (jobId: string) => void;
};

const terminalStates = new Set(["completed", "failed", "cancelled"]);

export function JobCard({ job, onCancel, onOpenFolder, onRetry }: JobCardProps) {
  const title = job.metadata?.title ?? job.url;
  const isTerminal = terminalStates.has(job.state);
  const raw = job.metadata?.raw ?? {};
  const trackCount = typeof raw.track_count === "number" ? raw.track_count : null;
  const tracks = Array.isArray(raw.tracks) ? (raw.tracks as Array<Record<string, unknown>>) : [];

  return (
    <article className="glass-panel rounded-[1.6rem] p-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0 flex-1">
          <p className="text-xs uppercase tracking-[0.25em] text-moss">
            {job.provider ?? "detecting"} / {job.state.replace("_", " ")}
          </p>
          <div className="mt-2 flex gap-4">
            {job.metadata?.thumbnail_url ? (
              <img
                alt=""
                className="h-16 w-16 shrink-0 rounded-xl object-cover"
                src={job.metadata.thumbnail_url}
              />
            ) : null}
            <div className="min-w-0">
              <h3 className="text-lg font-semibold text-ink">{title}</h3>
              {job.metadata?.artist ? (
                <p className="mt-1 text-sm text-ink/70">{job.metadata.artist}</p>
              ) : null}
              {trackCount ? (
                <p className="mt-1 text-sm text-ink/60">{trackCount} Spotify track(s) resolved</p>
              ) : null}
            </div>
          </div>
          <p className="mt-1 break-all text-sm text-ink/60">{job.url}</p>
          {tracks.length ? (
            <div className="mt-4 rounded-2xl bg-ink/5 p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-ink/50">
                Tracks
              </p>
              <div className="mt-2 grid gap-2">
                {tracks.slice(0, 5).map((track, index) => (
                  <div className="text-sm text-ink/70" key={`${track.title ?? "track"}-${index}`}>
                    <span className="font-semibold text-ink">
                      {String(track.position ?? index + 1)}. {String(track.title ?? "Untitled")}
                    </span>
                    {track.artist ? <span> by {String(track.artist)}</span> : null}
                  </div>
                ))}
              </div>
              {tracks.length > 5 ? (
                <p className="mt-2 text-xs text-ink/45">Showing 5 of {tracks.length} loaded tracks.</p>
              ) : null}
            </div>
          ) : null}
          {job.error ? (
            <p className="mt-3 rounded-2xl bg-clay/10 px-3 py-2 text-sm text-clay">
              {job.error.message}
            </p>
          ) : null}
          {job.result?.file_path ? (
            <p className="mt-3 rounded-2xl bg-moss/10 px-3 py-2 text-sm text-moss">
              Saved to {job.result.file_path}
            </p>
          ) : null}
        </div>
        <div className="flex gap-2">
          {!isTerminal ? (
            <button
              className="rounded-full border border-ink/15 px-4 py-2 text-sm text-ink hover:bg-ink/5"
              onClick={() => onCancel?.(job.id)}
              type="button"
            >
              Cancel
            </button>
          ) : null}
          {job.state === "failed" || job.state === "cancelled" ? (
            <button
              className="rounded-full bg-ink px-4 py-2 text-sm text-paper hover:bg-ink/85"
              onClick={() => onRetry?.(job.id)}
              type="button"
            >
              Retry
            </button>
          ) : null}
          {job.state === "completed" && onOpenFolder ? (
            <button
              className="rounded-full bg-ink px-4 py-2 text-sm text-paper hover:bg-ink/85"
              onClick={() => onOpenFolder(job.id)}
              type="button"
            >
              Open folder
            </button>
          ) : null}
        </div>
      </div>
      <div className="mt-5 h-3 overflow-hidden rounded-full bg-ink/10">
        <div
          className="h-full rounded-full bg-gradient-to-r from-tide via-moss to-brass transition-all"
          style={{ width: `${job.progress}%` }}
        />
      </div>
      <p className="mt-2 text-sm text-ink/65">{job.status_message}</p>
    </article>
  );
}
