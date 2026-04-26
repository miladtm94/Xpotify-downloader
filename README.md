# LynkOo

LynkOo is a local-first media manager built from the open-source spotDL
codebase. It preserves spotDL's Spotify metadata/audio matching workflow and
adds a FastAPI backend, React dashboard, direct media downloads, and
yt-dlp-backed public video page support.

## What It Does

- Accepts Spotify links for spotDL metadata and audio matching.
- Accepts direct public audio/video file URLs such as `.mp3`, `.m4a`, `.flac`,
  `.wav`, `.ogg`, `.opus`, `.mp4`, `.webm`, and `.mov`.
- Accepts public video pages that have a specific yt-dlp extractor.
- Validates and inspects links before jobs run.
- Shows available video quality options when yt-dlp exposes them.
- Tracks queued, active, completed, failed, and cancelled jobs.
- Opens completed download folders from the Library.

## What It Does Not Do

- It does not download audio directly from Spotify.
- It does not bypass DRM, paywalls, private-content controls, account logins,
  cookies, or anti-bot protections.
- It does not use yt-dlp's generic webpage scraper or piracy catchall extractor.
- It does not grant permission to download media. Use LynkOo only for media you
  own, have permission to download, or can lawfully access.

## Supported Providers

| Provider | Status | Sources | Notes |
| --- | --- | --- | --- |
| spotDL | Enabled | Spotify track, album, playlist, artist links | Spotify is metadata only; audio is matched through spotDL's configured providers. |
| Direct media | Enabled | Public direct media files | Supports common audio/video file extensions without platform scraping. |
| Public video | Enabled with limits | Public video pages with a specific yt-dlp extractor | No login, cookies, DRM bypass, generic webpage scraping, piracy catchall, or private access. |

## Installation

macOS first-time setup:

```bash
python -m pip install uv
uv sync
brew install ffmpeg
```

If you do not use Homebrew, install FFmpeg from your preferred trusted source
and ensure `ffmpeg` is available on `PATH`.

Python compatibility is currently `>=3.10,<3.14`.

## Development

Docker hot-reload development:

```bash
make docker-up
```

Then open:

```text
http://127.0.0.1:5173
```

Docker Compose runs the backend on port `8800` and the Vite frontend on port
`5173`. Source files are bind-mounted, so backend code reloads through
`uvicorn --reload` and frontend code reloads through Vite HMR.

Docker downloads are written to the host `./downloads` folder by default. Inside
the container this is mounted as `/downloads` and exposed through
`LYNKOO_OUTPUT_DIR`. The older `XPOTIFY_OUTPUT_DIR` env var is still accepted as
a compatibility fallback.

Backend:

```bash
uv run lynkoo-api
```

Alternative:

```bash
uv run uvicorn app.backend.main:app --host 127.0.0.1 --port 8800 --reload
```

Frontend:

```bash
cd app/frontend
npm install
npm run dev
```

## Testing

Backend tests:

```bash
uv run pytest tests/app_backend
```

Frontend build:

```bash
cd app/frontend
npm run build
```

Full local check:

```bash
make check
```

## Donations

GitHub Sponsors is enabled through `.github/FUNDING.yml`.

Suggested donation rollout:

1. Enable GitHub Sponsors for `miladtm94`.
2. Add tiers such as Supporter, Backer, and Founding Supporter.
3. Keep donations optional for the open-source app.
4. Add Ko-fi, Buy Me a Coffee, or Open Collective later if GitHub Sponsors is
   not enough.
5. For paid desktop builds, use a separate license/subscription flow such as
   Stripe or Lemon Squeezy after the app is packaged.

## Publishing Checklist

1. Rename the GitHub repository from `Xpotify-downloader` to `LynkOo`.
2. Update the local remote:

   ```bash
   git remote set-url origin git@github.com:miladtm94/LynkOo.git
   ```

3. Push the renamed project:

   ```bash
   git add .
   git commit -m "Rename project to LynkOo"
   git push origin HEAD
   ```

4. Add repository metadata on GitHub:

   - Description: `Local media manager for Spotify metadata, direct media files, and yt-dlp-supported public video pages.`
   - Website: your future LynkOo landing page.
   - Topics: `media-manager`, `spotdl`, `yt-dlp`, `fastapi`, `react`, `desktop-app`.

5. Create a `v0.1.0` GitHub Release with macOS/Linux/Windows instructions.
6. Package a desktop build with Tauri or Electron once the web UI stabilizes.
7. Sign and notarize macOS builds before public distribution.
8. Add auto-update only after signed builds are working.
9. Publish from your own website first. App stores are higher friction for this
   category and may reject broad downloaders, adult-platform support, or unclear
   third-party media permissions.

## Monetization Options

- Best first step: donationware through GitHub Sponsors.
- Next step: paid desktop convenience build while keeping source available.
- Later: optional Pro subscription for queue history, presets, batch tools,
  metadata cleanup, and automatic updates.
- Be careful with App Store subscriptions: Apple/Google payment policies and
  third-party media/download policies can apply.

## Troubleshooting

- `FFmpeg was not found`: install FFmpeg and ensure it is on `PATH`.
- `Unsupported link`: use a Spotify URL, direct public media file URL, or a
  yt-dlp-supported public video page.
- `Could not read a downloadable video`: the site may require login/cookies, be
  geoblocked, be removed, have changed its page format, or block non-browser
  access.
- `Spotify metadata failed`: retry later or paste individual track links.
- `uv: command not found`: install uv with `python -m pip install uv`.

## Attribution

LynkOo is derived from and preserves substantial functionality from
[spotDL](https://github.com/spotDL/spotify-downloader), licensed under the MIT
License. The original MIT license notice is retained in `LICENSE`.
