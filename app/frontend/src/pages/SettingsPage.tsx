import { FormEvent, useEffect, useState } from "react";

import { getSettings, selectOutputDirectory, updateSettings } from "../lib/api";
import type { AppSettings, DependencyStatus } from "../lib/types";

type SettingsPageProps = {
  settings?: AppSettings;
  onSettingsChange: (settings: AppSettings) => void;
};

export function SettingsPage({ settings, onSettingsChange }: SettingsPageProps) {
  const [draft, setDraft] = useState<AppSettings | undefined>(settings);
  const [dependencies, setDependencies] = useState<DependencyStatus[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    setDraft(settings);
  }, [settings]);

  useEffect(() => {
    getSettings().then((response) => {
      setDraft(response.settings);
      setDependencies(response.dependencies);
      onSettingsChange(response.settings);
    });
  }, [onSettingsChange]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft) {
      return;
    }
    const response = await updateSettings(draft);
    setDraft(response.settings);
    setDependencies(response.dependencies);
    onSettingsChange(response.settings);
    setMessage("Settings saved.");
  }

  async function handleChooseFolder() {
    const response = await selectOutputDirectory();
    setMessage(response.message);
    if (response.selected && response.path && draft) {
      setDraft({ ...draft, output_directory: response.path });
    }
  }

  if (!draft) {
    return <div className="glass-panel rounded-[2rem] p-8">Loading settings...</div>;
  }

  return (
    <section className="grid gap-6 lg:grid-cols-[1fr_0.8fr]">
      <form className="glass-panel rounded-[2rem] p-6" onSubmit={handleSubmit}>
        <p className="text-xs uppercase tracking-[0.35em] text-tide">Settings</p>
        <h2 className="display-font mt-2 text-4xl font-semibold">Local defaults</h2>
        <div className="mt-7 grid gap-4">
          <label>
            <span className="mb-2 block text-sm font-semibold">Default output folder</span>
            <div className="flex flex-col gap-3 md:flex-row">
              <input
                className="field"
                onChange={(event) => setDraft({ ...draft, output_directory: event.target.value })}
                value={draft.output_directory}
              />
              <button
                className="rounded-[1.1rem] border border-ink/15 px-5 py-3 text-sm font-semibold text-ink transition hover:bg-ink/5"
                onClick={handleChooseFolder}
                type="button"
              >
                Choose folder
              </button>
            </div>
          </label>
          <div className="grid gap-4 md:grid-cols-2">
            <label>
              <span className="mb-2 block text-sm font-semibold">Audio format</span>
              <select
                className="field"
                onChange={(event) => setDraft({ ...draft, default_audio_format: event.target.value })}
                value={draft.default_audio_format}
              >
                {["mp3", "m4a", "opus", "flac", "wav", "ogg"].map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span className="mb-2 block text-sm font-semibold">Video format</span>
              <select
                className="field"
                onChange={(event) => setDraft({ ...draft, default_video_format: event.target.value })}
                value={draft.default_video_format}
              >
                {["mp4", "webm", "mov"].map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label>
            <span className="mb-2 block text-sm font-semibold">Quality</span>
            <select
              className="field"
              onChange={(event) => setDraft({ ...draft, default_quality: event.target.value })}
              value={draft.default_quality}
            >
              {["best", "high", "medium", "low"].map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="mb-2 block text-sm font-semibold">Theme</span>
            <select
              className="field"
              onChange={(event) => setDraft({ ...draft, theme: event.target.value as AppSettings["theme"] })}
              value={draft.theme}
            >
              <option value="system">System</option>
              <option value="light">Light</option>
              <option value="dark">Dark</option>
            </select>
          </label>
        </div>
        <button className="mt-7 rounded-full bg-ink px-6 py-3 text-paper" type="submit">
          Save settings
        </button>
        {message ? <p className="mt-4 text-sm text-moss">{message}</p> : null}
      </form>

      <aside className="glass-panel rounded-[2rem] p-6">
        <p className="text-xs uppercase tracking-[0.35em] text-clay">Dependencies</p>
        <h3 className="display-font mt-2 text-3xl font-semibold">Readiness check</h3>
        <div className="mt-5 space-y-3">
          {dependencies.map((dependency) => (
            <div className="rounded-2xl bg-ink/5 px-4 py-3" key={dependency.name}>
              <div className="flex items-center justify-between gap-3">
                <span className="font-semibold">{dependency.name}</span>
                <span className={dependency.available ? "text-moss" : "text-clay"}>
                  {dependency.available ? "available" : "missing"}
                </span>
              </div>
              <p className="mt-1 text-sm text-ink/60">{dependency.message}</p>
              {dependency.version ? <p className="mt-1 text-xs text-ink/45">{dependency.version}</p> : null}
            </div>
          ))}
        </div>
      </aside>
    </section>
  );
}
