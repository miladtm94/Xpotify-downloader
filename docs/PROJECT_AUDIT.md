# Project Audit

This audit was created before cleanup or implementation work. It is intended to
preserve useful spotDL functionality while guiding the project toward a polished
local media manager with a separate app layer, explicit provider boundaries, and
clear lawful-use limitations.

## Repository Diagnosis

The original checkout was a Python-only spotDL source tree with documentation,
tests, packaging metadata, Docker support, and upstream GitHub automation. During
the follow-up cleanup, Git was initialized by the project owner on `main` and the
new project began replacing upstream-only surfaces with Xpotify-specific app
code and documentation.

Top-level structure:

- `spotdl/`: existing spotDL Python package and CLI/web implementation.
- `tests/`: pytest suite with VCR cassettes for Spotify/search/provider tests.
- `docs/`: MkDocs documentation and images from upstream spotDL.
- `scripts/`: upstream build, binary-zip, Termux, and documentation scripts.
- `.github/`: upstream issue templates, funding metadata, stale config, and CI/CD
  workflows.
- `pyproject.toml`: PEP 621 package metadata, uv dependency groups, Hatch build
  backend, pytest/isort/pylint configuration.
- `uv.lock`: uv lockfile.
- `README.md`, `LICENSE`, `mkdocs.yml`, `.readthedocs.yaml`, `Dockerfile`,
  `docker-compose.yml`: upstream project metadata and deployment/docs support.

Detected dependency and build tools:

- Python package manager/build flow: `uv` lockfile and dependency groups,
  Hatchling build backend.
- Python version constraint: `>=3.10,<3.14`.
- CLI entry point: `spotdl = "spotdl:console_entry_point"`.
- Existing API/web dependencies: `fastapi`, `uvicorn`, `websockets`,
  `pydantic`.
- Existing media dependencies: `yt-dlp`, `spotipy`, `ytmusicapi`, `pytube`,
  `mutagen`, `python-slugify`, `rapidfuzz`, `beautifulsoup4`, `requests`,
  `syncedlyrics`, `soundcloud-v2`, `pykakasi`.
- Frontend package managers: no `package.json`, `package-lock.json`,
  `pnpm-lock.yaml`, or `yarn.lock` is currently present.
- Local tooling status observed during audit: `uv` is not installed on this
  machine, `python` is 3.10.14, `python3` is 3.14.3, `ffmpeg` is available at
  `/opt/homebrew/bin/ffmpeg`, Node is v18.17.1, npm is 9.6.7.

Current entry points and app surfaces:

- `spotdl/__main__.py` runs `console_entry_point()`.
- `spotdl/__init__.py` exposes `Spotdl`, `console_entry_point`, and
  `__version__`.
- `spotdl/console/entry_point.py` supports operations: `download`, `sync`,
  `save`, `meta`, `url`, and `web`.
- `spotdl/console/web.py` starts an existing FastAPI server and serves a cached
  or downloaded external web UI.
- `spotdl/utils/web.py` defines existing web routes such as `/api/ws`,
  `/api/url`, `/api/download/url`, `/api/download/file`, `/api/settings`,
  `/api/settings/update`, `/api/check_update`, and `/api/options_model`.

## Core Modules To Preserve

These modules contain the useful spotDL engine and should be treated as
upstream-derived core until the new app wrapper is stable:

- `spotdl/__init__.py`: public `Spotdl` API wrapping Spotify metadata search and
  downloader operations.
- `spotdl/console/entry_point.py`: current CLI behavior and operation dispatch.
- `spotdl/console/download.py`, `save.py`, `sync.py`, `meta.py`, `url.py`,
  `web.py`: existing CLI operation implementations.
- `spotdl/download/downloader.py`: core search/download/postprocess pipeline,
  provider selection, metadata embedding, FFmpeg conversion, archives, M3U,
  duplicate handling, and progress tracking.
- `spotdl/download/progress_handler.py`: existing CLI/web progress bridge.
- `spotdl/providers/audio/*`: audio search/download providers built around
  YouTube, YouTube Music, Piped, SoundCloud, Bandcamp, and yt-dlp.
- `spotdl/providers/lyrics/*`: lyrics provider integrations.
- `spotdl/types/*`: Song, Album, Artist, Playlist, Saved, Result, and options
  models used throughout the downloader.
- `spotdl/utils/spotify.py`, `search.py`, `matching.py`, `formatter.py`,
  `metadata.py`, `ffmpeg.py`, `config.py`, `arguments.py`, `downloader.py`,
  `archive.py`, `m3u.py`, `lrc.py`, `logging.py`: supporting metadata,
  matching, formatting, configuration, FFmpeg, and utility behavior.

Initial strategy: keep `spotdl/` import-compatible and build the local media
manager under a new `app/` package. The new app should call the public `Spotdl`
class or a narrow wrapper around `Downloader`, `Song`, and `parse_query` instead
of duplicating matching, metadata, tagging, or FFmpeg logic.

## Tests And Verification Assets To Preserve

The existing test suite is valuable because it documents current spotDL behavior
and protects against breaking the audio workflow.

Keep:

- `tests/test_init.py`, `tests/test_main.py`, `tests/test_matching.py`.
- `tests/console/test_entry_point.py`.
- `tests/utils/*`.
- `tests/types/*`.
- `tests/providers/audio/*`.
- `tests/providers/lyrics/*`.
- VCR cassettes under `tests/**/cassettes`.
- `tests/conftest.py`, including Spotify test initialization and FFmpeg fakes.
- `tests/README.md`.

Future app tests should be additive rather than replacing upstream tests:

- URL detection and provider routing tests.
- Job state transition tests.
- Filename sanitization tests.
- Settings validation tests.
- Backend health/settings/download route tests.
- Mock provider tests that never download copyrighted media.

## Files That Must Be Kept

These should not be removed as part of cleanup:

- `LICENSE`: required MIT license and upstream attribution.
- `README.md`: should be rewritten for the new app while acknowledging spotDL.
- `pyproject.toml`: package/dependency/build source of truth.
- `uv.lock`: current reproducibility artifact unless a replacement lock strategy
  is adopted.
- `spotdl/`: existing audio/metadata/download core.
- `tests/`: existing behavioral safety net.
- `docs/installation.md`, `docs/usage.md`, `docs/troubleshooting.md`: useful
  upstream user knowledge that should be preserved or archived if superseded.
- `docs/index.md`: MkDocs home page until documentation is reorganized.
- `mkdocs.yml`: keep until the docs site strategy is replaced.
- `.editorconfig`, `.pylintrc`: useful local style/tooling configuration.

## Candidate Cleanup Files And Folders

The initial audit identified the following cleanup candidates. The project owner
then approved removing previous-author/upstream-only project surfaces before the
first commit. Actual removals are recorded in `docs/archive-notes.md`.

Safe/generated candidates:

- `.DS_Store`: macOS generated metadata. Candidate for deletion and `.gitignore`
  coverage.

Upstream repository workflow candidates:

- `.github/workflows/python-publish.yml`: upstream PyPI/release publishing for
  `spotdl`; likely obsolete for a local app unless this project continues
  publishing the same package.
- `.github/workflows/docker-hub-image-publish.yml`: upstream Docker Hub release
  automation; likely obsolete unless new Docker publishing is desired.
- `.github/workflows/build-docs.yml`: upstream docs publishing; can be kept if
  MkDocs remains, but should be retargeted before any public repo usage.
- `.github/workflows/tests.yml` and `.github/workflows/standard-checks.yml`:
  keep or rewrite for the new app. They are useful templates but currently
  target only `spotdl/` and upstream assumptions.
- `.github/FUNDING.yml`, `.github/stale.yml`,
  `.github/ISSUE_TEMPLATE/*`, `.github/PULL_REQUEST_TEMPLATE.yml`: upstream
  community maintenance files. Candidate for archive or replacement with local
  project versions, but not urgent.

Upstream distribution candidates:

- `scripts/build.py`: PyInstaller build script for spotDL CLI binary. Candidate
  for archive if desktop packaging moves to Tauri/Electron or a different build
  flow.
- `scripts/make_binzip.sh`: spotDL zipapp/binary helper. Candidate for archive.
- `scripts/termux.sh`: upstream Termux installer. Likely unrelated to the local
  desktop/web app and candidate for archive.
- `Dockerfile`, `docker-compose.yml`, `.dockerignore`: useful if we keep a
  containerized backend/dev flow, but currently branded around spotDL CLI.
  Candidate for rewrite, not blind deletion.
- `.readthedocs.yaml`: candidate for rewrite or removal if ReadTheDocs is no
  longer used.

Editor/local candidates:

- `.vscode/settings.json`: project-local editor settings. Keep if desired, or
  remove if the project should avoid editor-specific files.

Documentation candidates:

- `docs/CODE_OF_CONDUCT.md` and `docs/CONTRIBUTING.md`: upstream community docs.
  Keep until replaced with new project-specific docs or archive notes.
- `docs/images/*`: upstream spotDL docs screenshots. Candidate for replacement
  once the new UI exists.
- `docs/index.md`: currently mirrors upstream README. Rewrite rather than delete.

Cleanup process before deletion:

- Search references with `rg`.
- Confirm packaging/build/docs references in `pyproject.toml`, `mkdocs.yml`,
  `.readthedocs.yaml`, `Dockerfile`, and workflows.
- Move rationale into `docs/archive-notes.md` before or during removal.
- Run import checks and available tests afterward.

## Dependency Risks

- `uv` is the current project workflow, but it is not installed locally in this
  audit environment. Install instructions should include `pip install uv` or a
  fallback `pip install -e ".[dev]"` style path if dependency groups are
  adjusted.
- The current package supports Python `>=3.10,<3.14`. The local `python3`
  command is Python 3.14.3 and is outside the declared support range; use
  `python` 3.10.14 or a managed virtual environment.
- `pytest --version` exited with no output in this environment, while importing
  `pytest` directly succeeded. This should be revisited once the environment is
  normalized with `uv`.
- The existing `fastapi>=0.103.0,<0.104` and `uvicorn>=0.23.2,<0.24` pins are
  old relative to the planned backend. We can build on them initially, but
  modern FastAPI/Pydantic behavior should be checked before expanding the API.
- `yt-dlp`, `pytube`, `ytmusicapi`, `spotipy`, and provider APIs are
  fast-moving and may break due to upstream service changes.
- FFmpeg is required for audio conversion and tagging workflows. The app needs
  explicit dependency-status reporting and graceful failure.
- Existing default Spotify/Genius client values are embedded in upstream config.
  The local app must not add new secrets, persist user credentials, or imply
  privileged Spotify access.
- Direct video/audio URL support must avoid DRM bypass, private content,
  account cookies, anti-bot circumvention, and unsupported platform scraping.

## Known Upstream Risks

- spotDL does not download audio directly from Spotify. It uses Spotify metadata
  and matches audio from other providers, commonly YouTube/YouTube Music.
- Existing web mode downloads or serves a separate external spotDL web UI cache
  from GitHub by default. A local media manager should avoid that behavior and
  serve its own frontend.
- Existing web routes are client/session oriented and coupled to spotDL settings,
  not a general provider/job architecture.
- Some tests rely on VCR cassettes and may become stale when third-party
  responses change.
- Search/matching quality and provider availability are inherently variable.
- SponsorBlock/cookie/yt-dlp settings can raise legal and policy questions; the
  new UI should expose only lawful, conservative defaults.

## Recommended App Architecture

Add a separate app layer and keep spotDL core intact:

```text
app/
  backend/
    main.py
    api/
      routes_downloads.py
      routes_settings.py
      routes_health.py
    services/
      download_manager.py
      job_queue.py
      file_manager.py
      metadata_service.py
    providers/
      base.py
      spotdl_provider.py
      direct_media_provider.py
      video_provider.py
    models/
      download_job.py
      download_result.py
      settings.py
    utils/
      logging.py
      validation.py
      filenames.py
  frontend/
    package.json
    src/
      App.tsx
      components/
      pages/
      lib/
      styles/
tests/
  app/
```

Backend design:

- Use FastAPI for the new app backend.
- Introduce a `DownloadProvider` protocol or abstract base class with:
  `can_handle(url)`, `validate(url)`, `get_metadata(url)`, and `download(job)`.
- Keep job state explicit: `queued`, `validating`, `fetching_metadata`,
  `downloading`, `postprocessing`, `completed`, `failed`, `cancelled`.
- `DownloadManager` owns provider routing, job creation, state transitions, and
  error normalization.
- `JobQueue` handles concurrency limits and cancellation.
- Progress updates should use WebSockets first, with Server-Sent Events as a
  possible simpler alternative if the UI does not need bidirectional messages.
- `Settings` should validate output directory, format, quality, and concurrency
  limits through Pydantic.
- `FileManager` should sanitize filenames and prevent path traversal.
- Dependency status should check Python version, FFmpeg availability, and
  optional downloader capabilities.

Provider plan:

- `SpotDLProvider`: handles Spotify track/album/playlist/artist URLs using the
  existing spotDL engine. It should state clearly that Spotify is metadata-only
  and audio matching comes from legal configured providers.
- `DirectMediaProvider`: handles direct public media files such as `.mp3`,
  `.flac`, `.wav`, `.m4a`, `.ogg`, `.mp4`, `.webm`, and `.mov` when URL headers
  or extensions indicate downloadable media.
- `VideoProvider`: initial abstraction for future video-capable providers. It
  should return clear unsupported-source errors until a lawful backend is
  intentionally enabled.
- `MockProvider`: test-only provider for deterministic queue/job tests.

Frontend design:

- React + TypeScript + Vite.
- Tailwind CSS for styling, with shadcn/ui considered only if it stays light.
- Pages: Home/Download, Queue, Library/Completed, Settings, About/Legal.
- Use generated or shared TypeScript types where practical for API contracts.
- Capability matrix should be visible in README and About/Legal UI.
- Desktop packaging should be deferred. Start with FastAPI + React web app, then
  evaluate Tauri only after local backend/frontend behavior is stable.

## Proposed Implementation Plan

1. Normalize project control:
   create or restore a Git repository, then create
   `feature/local-media-manager`.
2. Add `.gitignore` if missing and remove only generated local artifacts such as
   `.DS_Store` after approval.
3. Add backend app scaffold, provider interfaces, Pydantic models, manager,
   queue, health/settings/download APIs, and WebSocket progress route.
4. Add tests for provider routing, URL validation, job states, settings,
   filename sanitization, health route, and mocked downloads.
5. Wrap existing spotDL behavior with `SpotDLProvider` using public or narrow
   internal APIs after focused integration tests.
6. Add conservative direct-media support without DRM bypass, cookies, private
   content scraping, or platform circumvention.
7. Add React/Vite/Tailwind frontend connected to backend validation, job create,
   progress, settings, and completed-job APIs.
8. Rewrite README and create/update `docs/ARCHITECTURE.md`,
   `docs/DEVELOPMENT.md`, and `docs/LEGAL_AND_USAGE.md`.
9. Revisit cleanup candidates, archive rationale in `docs/archive-notes.md`,
   update docs/build/CI references, and run tests/import checks.
