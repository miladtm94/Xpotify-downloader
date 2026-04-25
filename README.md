# Xpotify Local Media Manager

Xpotify is a local-first media manager built from the open-source spotDL codebase.
It preserves the useful spotDL audio workflow and adds a modern FastAPI backend,
a React frontend, and a provider architecture for future lawful media sources.

## What It Does

- Accepts Spotify links for the existing spotDL metadata and audio-matching workflow.
- Accepts direct public audio/video file URLs such as `.mp3`, `.m4a`, `.flac`,
  `.wav`, `.ogg`, `.opus`, `.mp4`, `.webm`, and `.mov`.
- Validates links before jobs run.
- Tracks jobs through queued, validating, fetching metadata, downloading,
  post-processing, completed, failed, and cancelled states.
- Streams progress updates to the frontend with WebSockets.
- Shows settings, dependency status, provider capabilities, completed jobs, and
  clear failure messages.

## What It Does Not Do

- It does not download audio directly from Spotify.
- It does not bypass DRM, paywalls, private-content controls, account logins, or
  anti-bot protections.
- It does not extract cookies, scrape private content, or claim support for
  unsupported platforms.
- It does not currently ship a desktop wrapper. Tauri can be evaluated after the
  web backend and frontend stabilize.

## Lawful Use

Use this project only with media you own, have permission to download, or can
lawfully access. Direct media URL support is intended for public files where
downloading is permitted. Platform URLs such as X/Twitter are recognized only so
the app can return a clear unsupported-source message until a lawful provider is
intentionally added.

## Supported Providers

| Provider | Status | Sources | Notes |
| --- | --- | --- | --- |
| spotDL | Preserved core workflow | Spotify track, album, playlist, artist links | Spotify is used for metadata; audio is matched through spotDL's configured providers. |
| Direct media | Enabled | Public direct media files | Supports common audio/video file extensions without platform scraping. |
| Video platform | Placeholder | Public video platform URLs | Recognizes some sources but returns unsupported until a lawful backend is enabled. |

## Installation

macOS first-time setup:

```bash
python -m pip install uv
uv sync
brew install ffmpeg
```

If you do not use Homebrew, install FFmpeg from your preferred trusted source and
ensure `ffmpeg` is available on `PATH`.

Python compatibility is currently `>=3.10,<3.14`. Use `python`, `pyenv`, or `uv`
to select a compatible interpreter if your system `python3` is 3.14 or newer.

## Development Setup

Backend:

```bash
uv run xpotify-api
```

Alternative without installing the console script:

```bash
uv run uvicorn app.backend.main:app --host 127.0.0.1 --port 8800 --reload
```

Frontend:

```bash
cd app/frontend
npm install
npm run dev
```

The frontend defaults to `http://127.0.0.1:8800` for the API. Override with
`VITE_API_BASE_URL` if needed.

## Testing

Python tests:

```bash
uv run pytest tests/app_backend
```

The preserved upstream spotDL tests are still available under `tests/`. They use
mocking and VCR cassettes where practical; avoid adding tests that download
copyrighted media.

Frontend build:

```bash
cd app/frontend
npm run build
```

## Troubleshooting

- `FFmpeg was not found`: install FFmpeg and ensure it is on `PATH`.
- `Unsupported link`: use a Spotify URL or a direct public media file URL.
- `Spotify metadata failed`: check network access, provider availability, and
  any Spotify API/rate-limit issues.
- `uv: command not found`: install uv with `python -m pip install uv`.
- `python3` is too new: use Python 3.10, 3.11, 3.12, or 3.13.

## Attribution

Xpotify is derived from and preserves substantial functionality from
[spotDL](https://github.com/spotDL/spotify-downloader), licensed under the MIT
License. The original MIT license notice is retained in `LICENSE`.

