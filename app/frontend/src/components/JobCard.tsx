import type { DownloadJob } from "../lib/types";

type JobCardProps = {
  job: DownloadJob;
  onCancel?: (jobId: string) => void;
  onRetry?: (jobId: string) => void;
};

const terminalStates = new Set(["completed", "failed", "cancelled"]);

export function JobCard({ job, onCancel, onRetry }: JobCardProps) {
  const title = job.metadata?.title ?? job.url;
  const isTerminal = terminalStates.has(job.state);

  return (
    <article className="glass-panel rounded-[1.6rem] p-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-moss">
            {job.provider ?? "detecting"} / {job.state.replace("_", " ")}
          </p>
          <h3 className="mt-1 text-lg font-semibold text-ink">{title}</h3>
          <p className="mt-1 break-all text-sm text-ink/60">{job.url}</p>
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

