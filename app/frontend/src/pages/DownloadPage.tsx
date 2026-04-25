import { FormEvent, useState } from "react";

import { createDownload, selectOutputDirectory, validateDownload } from "../lib/api";
import type { AppSettings, DownloadJob, ValidationResult } from "../lib/types";

type DownloadPageProps = {
  settings?: AppSettings;
  onJobCreated: (job: DownloadJob) => void;
};

export function DownloadPage({ settings, onJobCreated }: DownloadPageProps) {
  const [url, setUrl] = useState("");
  const [mediaMode, setMediaMode] = useState<"auto" | "audio" | "video">("auto");
  const [format, setFormat] = useState(settings?.default_audio_format ?? "mp3");
  const [quality, setQuality] = useState(settings?.default_quality ?? "best");
  const [outputDirectory, setOutputDirectory] = useState(settings?.output_directory ?? "");
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [folderMessage, setFolderMessage] = useState<string | null>(null);

  async function handleValidate() {
    if (!url.trim()) {
      setValidation(null);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result = await validateDownload(url.trim());
      setValidation(result);
      if (result.ok && result.source_type === "video") {
        setMediaMode("video");
        setFormat(result.supported_formats.includes("mp4") ? "mp4" : result.supported_formats[0] ?? "mp4");
        setQuality(result.supported_qualities.includes("best") ? "best" : result.supported_qualities[0] ?? "best");
      }
      if (result.ok && (result.source_type === "audio" || result.source_type === "spotify_metadata")) {
        setMediaMode("audio");
        setFormat(result.supported_formats.includes("mp3") ? "mp3" : result.supported_formats[0] ?? "mp3");
      }
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Validation failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const job = await createDownload(url.trim(), {
        output_directory: outputDirectory || null,
        media_mode: mediaMode,
        format,
        quality,
        overwrite: false,
      });
      onJobCreated(job);
      setValidation(null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Could not start download");
    } finally {
      setBusy(false);
    }
  }

  async function handleChooseFolder() {
    setBusy(true);
    setError(null);
    setFolderMessage(null);
    try {
      const response = await selectOutputDirectory();
      setFolderMessage(response.message);
      if (response.selected && response.path) {
        setOutputDirectory(response.path);
      }
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Could not open folder picker");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="grid gap-6 lg:grid-cols-[1.25fr_0.75fr]">
      <form className="glass-panel rounded-[2rem] p-6" onSubmit={handleSubmit}>
        <p className="text-xs uppercase tracking-[0.35em] text-clay">New download</p>
        <h2 className="display-font mt-2 text-4xl font-semibold text-ink">
          Paste a link, keep the workflow honest.
        </h2>
        <p className="mt-3 max-w-2xl text-ink/65">
          Xpotify supports Spotify metadata workflows through spotDL and direct public
          media URLs. Unsupported or blocked sources fail clearly instead of pretending.
        </p>

        <div className="mt-7 space-y-4">
          <label className="block">
            <span className="mb-2 block text-sm font-semibold">Media URL</span>
            <input
              className="field"
              onBlur={handleValidate}
              onChange={(event) => setUrl(event.target.value)}
              placeholder="https://open.spotify.com/track/... or https://example.com/file.mp4"
              value={url}
            />
          </label>

          <div className="grid gap-4 md:grid-cols-3">
            <label>
              <span className="mb-2 block text-sm font-semibold">Mode</span>
              <select
                className="field"
                onChange={(event) => setMediaMode(event.target.value as "auto" | "audio" | "video")}
                value={mediaMode}
              >
                <option value="auto">Auto detect</option>
                <option value="audio">Audio</option>
                <option value="video">Video</option>
              </select>
            </label>
            <label>
              <span className="mb-2 block text-sm font-semibold">Format</span>
              <select className="field" onChange={(event) => setFormat(event.target.value)} value={format}>
                {["mp3", "m4a", "opus", "flac", "wav", "ogg", "mp4", "webm", "mov"].map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span className="mb-2 block text-sm font-semibold">Quality</span>
              <select className="field" onChange={(event) => setQuality(event.target.value)} value={quality}>
                {["best", "high", "medium", "low", "128k", "256k", "source"].map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <label className="block">
            <span className="mb-2 block text-sm font-semibold">
              Output folder
              <span className="ml-2 font-normal text-ink/50">
                Choose a local folder or type a path manually.
              </span>
            </span>
            <div className="flex flex-col gap-3 md:flex-row">
              <input
                className="field"
                onChange={(event) => setOutputDirectory(event.target.value)}
                placeholder="~/Music/Xpotify"
                value={outputDirectory}
              />
              <button
                className="rounded-[1.1rem] border border-ink/15 px-5 py-3 text-sm font-semibold text-ink transition hover:bg-ink/5 disabled:cursor-not-allowed disabled:opacity-55"
                disabled={busy}
                onClick={handleChooseFolder}
                type="button"
              >
                Choose folder
              </button>
            </div>
          </label>
        </div>

        {validation ? (
          <div
            className={`mt-5 rounded-[1.4rem] px-4 py-3 text-sm ${
              validation.ok ? "bg-moss/10 text-moss" : "bg-clay/10 text-clay"
            }`}
          >
            {validation.message}
          </div>
        ) : null}
        {error ? (
          <div className="mt-5 rounded-[1.4rem] bg-clay/10 px-4 py-3 text-sm text-clay">
            {error}
          </div>
        ) : null}
        {folderMessage ? (
          <div className="mt-5 rounded-[1.4rem] bg-tide/10 px-4 py-3 text-sm text-tide">
            {folderMessage}
          </div>
        ) : null}

        <div className="mt-7 flex flex-wrap gap-3">
          <button
            className="rounded-full bg-ink px-6 py-3 text-paper shadow-panel transition hover:bg-ink/85 disabled:cursor-not-allowed disabled:opacity-55"
            disabled={busy || !url.trim()}
            type="submit"
          >
            {busy ? "Working..." : "Start download"}
          </button>
          <button
            className="rounded-full border border-ink/15 px-6 py-3 text-ink transition hover:bg-ink/5 disabled:cursor-not-allowed disabled:opacity-55"
            disabled={busy || !url.trim()}
            onClick={handleValidate}
            type="button"
          >
            Validate link
          </button>
        </div>
      </form>

      <aside className="glass-panel rounded-[2rem] p-6">
        <p className="text-xs uppercase tracking-[0.35em] text-tide">Source rules</p>
        <h3 className="display-font mt-2 text-3xl font-semibold">What happens here?</h3>
        <div className="mt-5 space-y-3 text-sm text-ink/70">
          <p>Spotify links are metadata inputs. spotDL matches audio through configured external providers.</p>
          <p>Direct media URLs are downloaded only when they point to public media files.</p>
          <p>Public platform URLs such as YouTube or X are handled by yt-dlp when no login, cookies, DRM bypass, or private access is required.</p>
        </div>
      </aside>
    </section>
  );
}
