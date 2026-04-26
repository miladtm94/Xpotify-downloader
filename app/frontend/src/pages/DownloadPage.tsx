import { FormEvent, useEffect, useState } from "react";

import { createDownload, inspectDownload, selectOutputDirectory, validateDownload } from "../lib/api";
import type { AppSettings, AvailableQuality, DownloadJob, MediaMetadata, ValidationResult } from "../lib/types";

type DownloadPageProps = {
  settings?: AppSettings;
  onJobCreated: (job: DownloadJob) => void;
};

const DEFAULT_FORMAT_OPTIONS = ["mp3", "m4a", "opus", "flac", "wav", "ogg", "mp4", "webm", "mov"];
const DEFAULT_QUALITY_OPTIONS = ["best", "high", "medium", "low", "128k", "192k", "256k", "320k", "source"];

export function DownloadPage({ settings, onJobCreated }: DownloadPageProps) {
  const [url, setUrl] = useState("");
  const [mediaMode, setMediaMode] = useState<"auto" | "audio" | "video">("auto");
  const [format, setFormat] = useState(settings?.default_audio_format ?? "mp3");
  const [quality, setQuality] = useState(settings?.default_quality ?? "best");
  const [outputDirectory, setOutputDirectory] = useState(settings?.output_directory ?? "");
  const [outputDirectoryTouched, setOutputDirectoryTouched] = useState(false);
  const [outputSubfolder, setOutputSubfolder] = useState("");
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [validatedUrl, setValidatedUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [folderMessage, setFolderMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!settings) {
      return;
    }
    setFormat((current) => current || settings.default_audio_format);
    setQuality((current) => current || settings.default_quality);
    if (!outputDirectoryTouched) {
      setOutputDirectory(settings.output_directory);
    }
  }, [outputDirectoryTouched, settings]);

  async function handleValidate() {
    if (!url.trim()) {
      setValidation(null);
      setValidatedUrl(null);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      let result = await validateDownload(url.trim());
      if (result.ok && result.provider === "video_platform") {
        try {
          const metadata = await inspectDownload(url.trim());
          const availableQualities = qualityOptionsFromMetadata(metadata);
          result = {
            ...result,
            metadata,
            supported_qualities: availableQualities.length
              ? availableQualities.map((item) => item.id)
              : result.supported_qualities,
          };
        } catch (exc) {
          result = {
            ...result,
            ok: false,
            message: exc instanceof Error ? exc.message : "Could not inspect this video link.",
            error: {
              code: "platform_metadata_failed",
              message: exc instanceof Error ? exc.message : "Could not inspect this video link.",
            },
          };
        }
      }
      setValidation(result);
      setValidatedUrl(url.trim());
      if (result.ok && result.source_type === "video") {
        setMediaMode("video");
        setFormat(result.supported_formats.includes("mp4") ? "mp4" : result.supported_formats[0] ?? "mp4");
        setQuality(result.supported_qualities.includes("best") ? "best" : result.supported_qualities[0] ?? "best");
      }
      if (result.ok && (result.source_type === "audio" || result.source_type === "spotify_metadata")) {
        setMediaMode("audio");
        setFormat(result.supported_formats.includes("mp3") ? "mp3" : result.supported_formats[0] ?? "mp3");
        setQuality(result.supported_qualities.includes("best") ? "best" : result.supported_qualities[0] ?? "best");
      }
    } catch (exc) {
      setValidation(null);
      setValidatedUrl(null);
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
        output_subfolder: outputSubfolder.trim() || null,
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
        setOutputDirectoryTouched(true);
        setOutputDirectory(response.path);
      }
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Could not open folder picker");
    } finally {
      setBusy(false);
    }
  }

  const hasValidatedUrl = validation?.ok === true && validatedUrl === url.trim();
  const formatOptions = validation?.ok && validation.supported_formats.length
    ? validation.supported_formats
    : DEFAULT_FORMAT_OPTIONS;
  const qualityOptions = qualityOptionsFor(validation);
  const previewTitle = validation?.metadata?.title || (validation?.ok ? "Ready to download" : "No preview yet");
  const previewMeta = [
    validation?.metadata?.artist,
    validation?.metadata?.media_type,
    qualityOptionsFromMetadata(validation?.metadata).length
      ? `${qualityOptionsFromMetadata(validation?.metadata).length - 1} qualities`
      : null,
  ].filter(Boolean).join(" / ");
  const destination = destinationPath(outputDirectory, outputSubfolder);

  return (
    <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <form className="glass-panel rounded-[1.5rem] p-6" onSubmit={handleSubmit}>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs uppercase text-clay">Dashboard</p>
            <h2 className="display-font mt-1 text-4xl font-semibold text-ink">
              Paste your link below and enjoy!
            </h2>
          </div>
        </div>

        <div className="mt-6 space-y-4">
          <label className="block">
            <span className="mb-2 block text-sm font-semibold">Media URL</span>
            <input
              className="field"
              onBlur={handleValidate}
              onChange={(event) => {
                setUrl(event.target.value);
                setValidation(null);
                setValidatedUrl(null);
              }}
              placeholder="Spotify, direct media, or yt-dlp-supported public video URL"
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
                {formatOptions.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span className="mb-2 block text-sm font-semibold">Quality</span>
              <select className="field" onChange={(event) => setQuality(event.target.value)} value={quality}>
                {qualityOptions.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <label className="block">
            <span className="mb-2 block text-sm font-semibold">
              Library folder
            </span>
            <div className="flex flex-col gap-3 md:flex-row">
              <input
                className="field"
                onChange={(event) => {
                  setOutputDirectoryTouched(true);
                  setOutputDirectory(event.target.value);
                }}
                placeholder="~/Music/LynkOo"
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
          <label className="block">
            <span className="mb-2 block text-sm font-semibold">Subfolder</span>
            <input
              className="field"
              onChange={(event) => setOutputSubfolder(event.target.value)}
              placeholder="Daily Mix 2 or Playlists/Daily Mix 2"
              value={outputSubfolder}
            />
          </label>
        </div>

        {validation ? (
          <div
            className={`mt-5 rounded-[1.4rem] px-4 py-3 text-sm ${
              validation.ok ? "bg-moss/10 text-moss" : "bg-clay/10 text-clay"
            }`}
          >
            {validation.message}
            {validation.metadata ? (
              <div className="mt-3 flex gap-3 text-ink/75">
                {validation.metadata.thumbnail_url ? (
                  <img
                    alt=""
                    className="h-14 w-14 shrink-0 rounded-xl object-cover"
                    src={validation.metadata.thumbnail_url}
                  />
                ) : null}
                <div>
                  <p className="font-semibold text-ink">{validation.metadata.title}</p>
                  {validation.metadata.artist ? <p>{validation.metadata.artist}</p> : null}
                </div>
              </div>
            ) : null}
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
            disabled={busy || !hasValidatedUrl}
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

      <aside className="glass-panel rounded-[1.5rem] p-5">
        <p className="text-xs uppercase text-tide">Preview</p>
        <div className="mt-4 overflow-hidden rounded-[1rem] bg-ink/5">
          {validation?.metadata?.thumbnail_url ? (
            <img
              alt=""
              className="aspect-video w-full object-cover"
              src={validation.metadata.thumbnail_url}
            />
          ) : (
            <div className="flex aspect-video items-center justify-center text-sm text-ink/45">
              Validate a link
            </div>
          )}
        </div>
        <h3 className="mt-4 text-lg font-semibold leading-snug">{previewTitle}</h3>
        {previewMeta ? <p className="mt-1 text-sm text-ink/55">{previewMeta}</p> : null}
        <dl className="mt-5 grid grid-cols-2 gap-3 text-sm">
          <div className="rounded-[1rem] bg-ink/5 p-3">
            <dt className="text-ink/45">Format</dt>
            <dd className="mt-1 font-semibold">{format}</dd>
          </div>
          <div className="rounded-[1rem] bg-ink/5 p-3">
            <dt className="text-ink/45">Quality</dt>
            <dd className="mt-1 font-semibold">{qualityLabel(quality)}</dd>
          </div>
          <div className="col-span-2 rounded-[1rem] bg-ink/5 p-3">
            <dt className="text-ink/45">Destination</dt>
            <dd className="mt-1 truncate font-semibold" title={destination}>
              {destination}
            </dd>
          </div>
        </dl>
      </aside>
    </section>
  );
}

function destinationPath(libraryFolder: string, subfolder: string): string {
  const base = libraryFolder.trim() || "Default library";
  const child = subfolder.trim().replace(/^[/\\]+|[/\\]+$/g, "");
  if (!child) {
    return base;
  }
  const separator = base.endsWith("/") || base.endsWith("\\") ? "" : "/";
  return `${base}${separator}${child}`;
}

function qualityOptionsFor(validation: ValidationResult | null): AvailableQuality[] {
  const inspectedQualities = qualityOptionsFromMetadata(validation?.metadata);
  if (inspectedQualities.length) {
    return inspectedQualities;
  }

  const qualities = validation?.ok && validation.supported_qualities.length
    ? validation.supported_qualities
    : DEFAULT_QUALITY_OPTIONS;
  return qualities.map((item) => ({
    id: item,
    label: qualityLabel(item),
  }));
}

function qualityOptionsFromMetadata(metadata?: MediaMetadata | null): AvailableQuality[] {
  const raw = metadata?.raw as { available_qualities?: unknown } | undefined;
  if (!Array.isArray(raw?.available_qualities)) {
    return [];
  }
  return raw.available_qualities
    .filter(isAvailableQuality)
    .map((item) => ({
      ...item,
      detail: item.detail ?? sizeDetail(item.estimated_bytes),
    }));
}

function isAvailableQuality(value: unknown): value is AvailableQuality {
  return (
    typeof value === "object" &&
    value !== null &&
    "id" in value &&
    "label" in value &&
    typeof (value as { id: unknown }).id === "string" &&
    typeof (value as { label: unknown }).label === "string"
  );
}

function qualityLabel(value: string): string {
  if (value === "best") return "Best available";
  if (value === "source") return "Source";
  if (value.endsWith("k")) return `${value.replace("k", "")} kbps`;
  return value;
}

function sizeDetail(size?: number | null): string | null {
  if (!size) return null;
  if (size >= 1024 * 1024 * 1024) return `~${(size / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  if (size >= 1024 * 1024) return `~${Math.round(size / (1024 * 1024))} MB`;
  if (size >= 1024) return `~${Math.round(size / 1024)} KB`;
  return `~${size} B`;
}
