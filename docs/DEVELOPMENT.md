# Development

## Requirements

- Python `>=3.10,<3.14`
- FFmpeg on `PATH`
- uv for Python dependency management
- Node.js and npm for the frontend

macOS setup:

```bash
python -m pip install uv
brew install ffmpeg
uv sync
```

Frontend setup:

```bash
cd app/frontend
npm install
```

## Running Locally

Backend:

```bash
uv run xpotify-api
```

Development backend with reload:

```bash
uv run uvicorn app.backend.main:app --host 127.0.0.1 --port 8800 --reload
```

Frontend:

```bash
cd app/frontend
npm run dev
```

Open the Vite URL, usually `http://127.0.0.1:5173`.

## Tests

Run new backend app tests:

```bash
uv run pytest tests/app_backend
```

Run the preserved spotDL tests when working near the `spotdl/` package:

```bash
uv run pytest tests
```

Do not add tests that download copyrighted media. Use mocks, local fixtures, or
public-domain/direct sample files where necessary.

## Project Rules

- Keep `spotdl/` import-compatible unless intentionally upgrading the preserved
  engine.
- Add new app behavior under `app/`.
- Keep provider errors structured and safe for the UI.
- Do not add secrets or store user credentials.
- Do not add DRM bypass, private-content scraping, cookie extraction, or
  anti-bot circumvention.

## Dependency Notes

`uv.lock` should be regenerated after dependency changes:

```bash
uv lock
```

If `python3` points to Python 3.14 or newer, select a compatible interpreter with
uv or pyenv.

