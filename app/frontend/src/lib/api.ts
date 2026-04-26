import type {
  AppSettings,
  DownloadJob,
  DownloadOptions,
  FolderSelectionResponse,
  MediaMetadata,
  OpenFolderResponse,
  ProviderCapability,
  SettingsResponse,
  ValidationResult,
} from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      ...init,
    });
  } catch (exc) {
    throw new Error(
      `Could not reach the LynkOo backend at ${API_BASE || "the Vite /api proxy"}. ` +
        "Make sure make backend is running.",
    );
  }
  if (!response.ok) {
    const message = await errorMessage(response);
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function errorMessage(response: Response): Promise<string> {
  const body = await response.text();
  if (!body) {
    return "";
  }
  try {
    const payload = JSON.parse(body) as { detail?: unknown };
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
    if (Array.isArray(payload.detail)) {
      return payload.detail
        .map((item) => {
          if (typeof item === "string") return item;
          if (item && typeof item === "object" && "msg" in item) {
            return String((item as { msg: unknown }).msg);
          }
          return null;
        })
        .filter(Boolean)
        .join("; ");
    }
  } catch {
    return body;
  }
  return body;
}

export function updatesWebSocketUrl(): string {
  const base = new URL(API_BASE || window.location.origin);
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

export function inspectDownload(url: string): Promise<MediaMetadata> {
  return request<MediaMetadata>("/api/downloads/inspect", {
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

export function openDownloadFolder(jobId: string): Promise<OpenFolderResponse> {
  return request<OpenFolderResponse>(`/api/downloads/${jobId}/open-folder`, {
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
