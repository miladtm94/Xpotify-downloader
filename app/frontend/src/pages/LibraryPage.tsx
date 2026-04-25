import { JobCard } from "../components/JobCard";
import type { DownloadJob } from "../lib/types";

type LibraryPageProps = {
  jobs: DownloadJob[];
};

export function LibraryPage({ jobs }: LibraryPageProps) {
  const completedJobs = jobs.filter((job) => job.state === "completed");
  const failedJobs = jobs.filter((job) => job.state === "failed" || job.state === "cancelled");

  return (
    <section className="space-y-5">
      <div className="glass-panel rounded-[2rem] p-6">
        <p className="text-xs uppercase tracking-[0.35em] text-brass">Library</p>
        <h2 className="display-font mt-2 text-4xl font-semibold">Completed downloads</h2>
        <p className="mt-3 text-ink/65">
          Browser mode can show file paths. Native open-file/open-folder actions are reserved for a future desktop wrapper.
        </p>
      </div>
      {completedJobs.map((job) => (
        <JobCard job={job} key={job.id} />
      ))}
      {!completedJobs.length ? (
        <div className="glass-panel rounded-[2rem] p-8 text-ink/65">
          Completed downloads will appear here.
        </div>
      ) : null}
      {failedJobs.length ? (
        <div className="glass-panel rounded-[2rem] p-6">
          <h3 className="text-lg font-semibold">Recent failures</h3>
          <div className="mt-4 space-y-3">
            {failedJobs.slice(0, 5).map((job) => (
              <p className="rounded-2xl bg-clay/10 px-4 py-3 text-sm text-clay" key={job.id}>
                {job.error?.message ?? job.status_message}
              </p>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}

