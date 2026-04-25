import { JobCard } from "../components/JobCard";
import type { DownloadJob } from "../lib/types";

type QueuePageProps = {
  jobs: DownloadJob[];
  onCancel: (jobId: string) => void;
  onRetry: (jobId: string) => void;
};

export function QueuePage({ jobs, onCancel, onRetry }: QueuePageProps) {
  const activeJobs = jobs.filter((job) => !["completed", "failed", "cancelled"].includes(job.state));

  return (
    <section className="space-y-5">
      <div className="glass-panel rounded-[2rem] p-6">
        <p className="text-xs uppercase tracking-[0.35em] text-moss">Queue</p>
        <h2 className="display-font mt-2 text-4xl font-semibold">Active workbench</h2>
        <p className="mt-3 text-ink/65">
          Jobs move through validation, metadata, download, post-processing, and terminal states.
        </p>
      </div>
      {activeJobs.length ? (
        activeJobs.map((job) => (
          <JobCard job={job} key={job.id} onCancel={onCancel} onRetry={onRetry} />
        ))
      ) : (
        <div className="glass-panel rounded-[2rem] p-8 text-ink/65">
          No active jobs yet. The bench is clear, which is its own tiny luxury.
        </div>
      )}
    </section>
  );
}

