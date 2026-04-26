# LynkOo

LynkOo is a local-first media manager for downloading and organizing media from
links you are allowed to access. It combines Spotify metadata workflows through
spotDL, direct public media file downloads, and yt-dlp-supported public video
pages in one clean dashboard.

## Highlights

- Spotify track, album, playlist, and artist links through spotDL metadata and
  audio matching.
- Public video pages supported by yt-dlp, including common platforms such as
  YouTube, Instagram, Facebook, X/Twitter, TikTok, and Vimeo.
- Direct public audio/video file URLs such as `.mp3`, `.m4a`, `.flac`, `.wav`,
  `.ogg`, `.opus`, `.mp4`, `.webm`, and `.mov`.
- Link validation and metadata preview before starting a download.
- Video quality selection when source formats are available.
- Queue, progress updates, completed Library view, and “Open folder” action.
- Optional playlist/download subfolders inside a main library folder.
- Docker development setup with backend reload and Vite hot module reload.

## Boundaries

LynkOo is intended for media you own, have permission to download, or can
lawfully access. It does not bypass DRM, paywalls, login requirements, private
content controls, cookies, or anti-bot protections. It also does not use
yt-dlp's generic webpage scraper or piracy catchall extractor.

## Supported Sources

| Source | Support | Notes |
| --- | --- | --- |
| Spotify | Metadata and audio matching | Audio is matched through spotDL providers; LynkOo does not download audio directly from Spotify. |
| Direct media files | Download | Supports common public audio/video file extensions. |
| Public video pages | Download | Supports pages with a specific yt-dlp extractor and no login/cookie/DRM requirement. |

## Requirements

- Python `>=3.10,<3.14`
- Node.js 20+ or 22+
- FFmpeg on `PATH`
- uv for Python dependency management

macOS setup:

```bash
python -m pip install uv
uv sync
brew install ffmpeg
```

If you do not use Homebrew, install FFmpeg from your preferred trusted source
and make sure `ffmpeg` is available on `PATH`.

## Run With Docker

```bash
make docker-up
```

Open:

```text
http://127.0.0.1:5173
```

The backend runs on port `8800`; the frontend runs on port `5173`. Source files
are bind-mounted, so backend changes reload through `uvicorn --reload` and
frontend changes reload through Vite HMR.

Docker downloads are written to the host `./downloads` folder by default. Inside
the container, the folder is mounted as `/downloads` and exposed through
`LYNKOO_OUTPUT_DIR`.

## Run Locally

Backend:

```bash
uv run lynkoo-api
```

Alternative backend command:

```bash
uv run uvicorn app.backend.main:app --host 127.0.0.1 --port 8800 --reload
```

Frontend:

```bash
cd app/frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

## Useful Commands

```bash
make setup          # install backend and frontend dependencies
make backend        # run backend with reload
make frontend       # run frontend dev server
make docker-up      # run full dev stack in Docker
make docker-down    # stop Docker services
make test           # run backend app tests
make build          # build frontend
make check          # run test, build, and npm audit
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

## Troubleshooting

- `FFmpeg was not found`: install FFmpeg and ensure it is on `PATH`.
- `Unsupported link`: use a Spotify URL, direct public media file URL, or a
  yt-dlp-supported public video page.
- `Could not read a downloadable video`: the site may require login/cookies, be
  geoblocked, be removed, have changed its page format, or block non-browser
  access.
- `Spotify metadata failed`: retry later or paste individual track links.
- `uv: command not found`: install uv with `python -m pip install uv`.

## License

LynkOo is released under the MIT License. See [LICENSE](LICENSE).

## Attribution

LynkOo is derived from and preserves substantial functionality from
[spotDL](https://github.com/spotDL/spotify-downloader), licensed under the MIT
License.
