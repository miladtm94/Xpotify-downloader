import type {
  AppSettings,
  DownloadJob,
  DownloadOptions,
  FolderSelectionResponse,
  ProviderCapability,
  SettingsResponse,
  ValidationResult,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8800";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function updatesWebSocketUrl(): string {
  const base = new URL(API_BASE);
  base.protocol = base.protocol === "https:" ? "wss:" : "ws:";
  base.pathname = "/api/downloads/ws";
  return base.toString();
}

export function validateDownload(url: string): Promise<ValidationResult> {
  return request<ValidationResult>("/api/downloads/validate", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export function createDownload(
  url: string,
  options: DownloadOptions,
): Promise<DownloadJob> {
  return request<DownloadJob>("/api/downloads", {
    method: "POST",
    body: JSON.stringify({ url, options }),
  });
}

export function listDownloads(): Promise<DownloadJob[]> {
  return request<DownloadJob[]>("/api/downloads");
}

export function cancelDownload(jobId: string): Promise<DownloadJob> {
  return request<DownloadJob>(`/api/downloads/${jobId}/cancel`, {
    method: "POST",
  });
}

export function retryDownload(jobId: string): Promise<DownloadJob> {
  return request<DownloadJob>(`/api/downloads/${jobId}/retry`, {
    method: "POST",
  });
}

export function getSettings(): Promise<SettingsResponse> {
  return request<SettingsResponse>("/api/settings");
}

export function updateSettings(settings: AppSettings): Promise<SettingsResponse> {
  return request<SettingsResponse>("/api/settings", {
    method: "PUT",
    body: JSON.stringify(settings),
  });
}

export function selectOutputDirectory(): Promise<FolderSelectionResponse> {
  return request<FolderSelectionResponse>("/api/settings/select-output-directory", {
    method: "POST",
  });
}

export function getProviders(): Promise<ProviderCapability[]> {
  return request<ProviderCapability[]>("/api/providers");
}
