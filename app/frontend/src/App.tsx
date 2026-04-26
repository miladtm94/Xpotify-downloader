import { useCallback, useEffect, useState } from "react";

import { Shell, type PageId } from "./components/Shell";
import {
  cancelDownload,
  getProviders,
  getSettings,
  listDownloads,
  retryDownload,
  updatesWebSocketUrl,
} from "./lib/api";
import type { AppSettings, DownloadJob, ProviderCapability } from "./lib/types";
import { AboutPage } from "./pages/AboutPage";
import { DownloadPage } from "./pages/DownloadPage";
import { LibraryPage } from "./pages/LibraryPage";
import { QueuePage } from "./pages/QueuePage";

function mergeJob(jobs: DownloadJob[], nextJob: DownloadJob): DownloadJob[] {
  const existing = jobs.findIndex((job) => job.id === nextJob.id);
  if (existing === -1) {
    return [nextJob, ...jobs];
  }
  const copy = [...jobs];
  copy[existing] = nextJob;
  return copy;
}

export default function App() {
  const [page, setPage] = useState<PageId>("download");
  const [jobs, setJobs] = useState<DownloadJob[]>([]);
  const [settings, setSettings] = useState<AppSettings | undefined>();
  const [providers, setProviders] = useState<ProviderCapability[]>([]);

  const refreshJobs = useCallback(async () => {
    setJobs(await listDownloads());
  }, []);

  useEffect(() => {
    refreshJobs();
    getSettings().then((response) => setSettings(response.settings));
    getProviders().then(setProviders);
  }, [refreshJobs]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      refreshJobs();
    }, 2000);
    return () => window.clearInterval(interval);
  }, [refreshJobs]);

  useEffect(() => {
    const socket = new WebSocket(updatesWebSocketUrl());
    socket.onmessage = (event) => {
      const job = JSON.parse(event.data) as DownloadJob;
      setJobs((current) => mergeJob(current, job));
    };
    return () => socket.close();
  }, []);

  async function handleCancel(jobId: string) {
    const job = await cancelDownload(jobId);
    setJobs((current) => mergeJob(current, job));
  }

  async function handleRetry(jobId: string) {
    const job = await retryDownload(jobId);
    setJobs((current) => mergeJob(current, job));
    setPage("queue");
  }

  function handleJobCreated(job: DownloadJob) {
    setJobs((current) => mergeJob(current, job));
    setPage("queue");
  }

  return (
    <Shell currentPage={page} onNavigate={setPage}>
      {page === "download" ? (
        <DownloadPage settings={settings} onJobCreated={handleJobCreated} />
      ) : null}
      {page === "queue" ? (
        <QueuePage jobs={jobs} onCancel={handleCancel} onRetry={handleRetry} />
      ) : null}
      {page === "library" ? <LibraryPage jobs={jobs} /> : null}
      {page === "about" ? <AboutPage providers={providers} /> : null}
    </Shell>
  );
}
