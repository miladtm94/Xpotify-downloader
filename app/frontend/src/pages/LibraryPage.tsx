import { JobCard } from "../components/JobCard";
import { openDownloadFolder } from "../lib/api";
import type { DownloadJob } from "../lib/types";

type LibraryPageProps = {
  jobs: DownloadJob[];
};

export function LibraryPage({ jobs }: LibraryPageProps) {
  const completedJobs = jobs.filter((job) => job.state === "completed");

  async function handleOpenFolder(jobId: string) {
    await openDownloadFolder(jobId);
  }

  return (
    <section className="space-y-5">
      <div className="glass-panel rounded-[2rem] p-6">
        <p className="text-xs uppercase tracking-[0.35em] text-brass">Library</p>
        <h2 className="display-font mt-2 text-4xl font-semibold">Completed downloads</h2>
        <p className="mt-3 text-ink/65">
          Finished downloads appear here. Open folder jumps to the saved album, playlist, or file location.
        </p>
      </div>
      {completedJobs.map((job) => (
        <JobCard job={job} key={job.id} onOpenFolder={handleOpenFolder} />
      ))}
      {!completedJobs.length ? (
        <div className="glass-panel rounded-[2rem] p-8 text-ink/65">
          Completed downloads will appear here.
        </div>
      ) : null}
    </section>
  );
}
