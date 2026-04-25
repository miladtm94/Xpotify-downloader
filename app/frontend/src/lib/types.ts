export type JobState =
  | "queued"
  | "validating"
  | "fetching_metadata"
  | "downloading"
  | "postprocessing"
  | "completed"
  | "failed"
  | "cancelled";

export type StructuredError = {
  code: string;
  message: string;
  details?: Record<string, unknown>;
};

export type MediaMetadata = {
  source_url: string;
  title?: string | null;
  artist?: string | null;
  album?: string | null;
  duration_seconds?: number | null;
  media_type: string;
  thumbnail_url?: string | null;
  provider?: string | null;
  raw?: Record<string, unknown>;
};

export type DownloadOptions = {
  output_directory?: string | null;
  media_mode: "auto" | "audio" | "video";
  format?: string | null;
  quality?: string | null;
  overwrite: boolean;
};

export type DownloadResult = {
  job_id: string;
  success: boolean;
  file_path?: string | null;
  metadata?: MediaMetadata | null;
  error?: StructuredError | null;
};

export type DownloadJob = {
  id: string;
  url: string;
  provider?: string | null;
  state: JobState;
  options: DownloadOptions;
  progress: number;
  status_message: string;
  metadata?: MediaMetadata | null;
  result?: DownloadResult | null;
  error?: StructuredError | null;
  created_at: string;
  updated_at: string;
  started_at?: string | null;
  completed_at?: string | null;
};

export type ValidationResult = {
  ok: boolean;
  provider?: string | null;
  source_type?: string | null;
  message: string;
  supported_formats: string[];
  supported_qualities: string[];
  error?: StructuredError | null;
};

export type ProviderCapability = {
  name: string;
  display_name: string;
  source_types: string[];
  supports_metadata: boolean;
  supports_progress: boolean;
  supports_cancel: boolean;
  supported_formats: string[];
  supported_qualities: string[];
  limitations: string[];
};

export type AppSettings = {
  output_directory: string;
  default_audio_format: string;
  default_video_format: string;
  default_quality: string;
  max_concurrent_downloads: number;
  theme: "system" | "light" | "dark";
  spotify_client_id?: string | null;
  spotify_client_secret?: string | null;
};

export type DependencyStatus = {
  name: string;
  available: boolean;
  version?: string | null;
  path?: string | null;
  message: string;
};

export type SettingsResponse = {
  settings: AppSettings;
  dependencies: DependencyStatus[];
};

export type FolderSelectionResponse = {
  selected: boolean;
  path?: string | null;
  message: string;
};
