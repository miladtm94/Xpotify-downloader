# Architecture

Xpotify is organized as a thin local application around a preserved spotDL core.
The goal is to keep upstream-derived audio behavior stable while giving the new
app a clean provider boundary, job model, and frontend.

## Layers

```text
app/
  backend/
    api/          FastAPI routes
    models/       Pydantic API and job models
    providers/    Provider interface and implementations
    services/     Download manager, queue, file, metadata services
    utils/        Logging, URL validation, filename safety
  frontend/       React + TypeScript + Vite UI
spotdl/           Preserved spotDL package and CLI workflow
tests/
  app_backend/    New app-layer tests
  ...             Preserved spotDL tests
```

## Backend

The backend is a FastAPI app exposed by `app.backend.main:create_app`.

Important routes:

- `GET /api/health`
- `GET /api/dependencies`
- `GET /api/providers`
- `GET /api/settings`
- `PUT /api/settings`
- `POST /api/downloads/validate`
- `POST /api/downloads`
- `GET /api/downloads`
- `GET /api/downloads/{job_id}`
- `POST /api/downloads/{job_id}/cancel`
- `POST /api/downloads/{job_id}/retry`
- `WS /api/downloads/ws`

`DownloadManager` is the orchestration point. It detects the provider, creates
jobs, drives state transitions, publishes WebSocket updates, and normalizes
errors into UI-safe payloads.

## Job States

Jobs move through these explicit states:

- `queued`
- `validating`
- `fetching_metadata`
- `downloading`
- `postprocessing`
- `completed`
- `failed`
- `cancelled`

The frontend treats `completed`, `failed`, and `cancelled` as terminal.

## Providers

Every provider implements:

- `can_handle(url: str) -> bool`
- `validate(url: str) -> ValidationResult`
- `get_metadata(url: str) -> MediaMetadata`
- `download(job: DownloadJob, progress_callback: ProgressCallback) -> DownloadResult`

Current providers:

- `SpotDLProvider`: wraps the existing spotDL workflow. Spotify is metadata-only;
  audio matching is handled by spotDL's configured providers.
- `DirectMediaProvider`: downloads direct public media files by extension.
- `VideoProvider`: placeholder for future lawful public video support. It
  returns clear unsupported/provider-not-enabled messages today.

## Frontend

The frontend is a Vite React app. It has pages for downloads, queue, library,
settings, and legal/about. It communicates with the backend through JSON routes
and receives job updates over WebSocket.

Desktop packaging is intentionally deferred. Once the web app is stable, Tauri
can provide native folder picking and open-file/open-folder actions without
rewriting the backend.

