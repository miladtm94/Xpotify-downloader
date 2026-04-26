"""Provider wrapper around the existing spotDL audio workflow."""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import re
from html import unescape
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urlparse

import requests

from app.backend.models.download_job import DownloadJob
from app.backend.models.download_result import (
    DownloadResult,
    MediaMetadata,
    ProviderCapability,
    StructuredError,
    ValidationResult,
)
from app.backend.models.settings import SUPPORTED_AUDIO_FORMATS, AppSettings
from app.backend.providers.base import DownloadProvider, ProgressCallback, ProviderError
from app.backend.utils.filenames import sanitize_filename
from app.backend.utils.validation import is_spotify_url

SPOTDL_BITRATES = {
    "auto",
    "disable",
    "8k",
    "16k",
    "24k",
    "32k",
    "40k",
    "48k",
    "64k",
    "80k",
    "96k",
    "112k",
    "128k",
    "160k",
    "192k",
    "224k",
    "256k",
    "320k",
}
SPOTDL_DOWNLOAD_THREADS = 4
SPOTDL_VISIBLE_QUALITIES = ["best", "128k", "192k", "256k", "320k"]


class SpotDLProvider(DownloadProvider):
    """Spotify metadata/audio matching provider backed by spotDL."""

    name = "spotdl"
    display_name = "Spotify metadata via spotDL"

    def __init__(self, settings: AppSettings):
        self.settings = settings

    @property
    def capability(self) -> ProviderCapability:
        return ProviderCapability(
            name=self.name,
            display_name=self.display_name,
            source_types=["Spotify track", "Spotify album", "Spotify playlist", "Spotify artist"],
            supported_formats=SUPPORTED_AUDIO_FORMATS,
            supported_qualities=SPOTDL_VISIBLE_QUALITIES,
            limitations=[
                "Spotify is used for metadata only.",
                "Audio is matched through spotDL's configured legal audio providers.",
                "Provider availability, rate limits, and matching quality may vary.",
            ],
        )

    def can_handle(self, url: str) -> bool:
        return is_spotify_url(url)

    async def validate(self, url: str) -> ValidationResult:
        if not self.can_handle(url):
            return ValidationResult(
                ok=False,
                provider=self.name,
                message="Only Spotify URLs or Spotify URIs are supported by this provider.",
                error=StructuredError(
                    code="invalid_spotify_url",
                    message="Enter a Spotify track, album, playlist, or artist URL.",
                ),
            )

        metadata = await asyncio.to_thread(self._get_oembed_metadata, url)
        title = metadata.title if metadata and metadata.title else None

        return ValidationResult(
            ok=True,
            provider=self.name,
            source_type="spotify_metadata",
            message=(
                f"Spotify link found: {title}. Start Download to resolve tracks "
                "and match audio through spotDL providers."
                if title
                else "Spotify metadata URL is supported. Start Download to resolve "
                "tracks and match audio through spotDL providers."
            ),
            supported_formats=SUPPORTED_AUDIO_FORMATS,
            supported_qualities=SPOTDL_VISIBLE_QUALITIES,
            metadata=metadata,
        )

    async def get_metadata(self, url: str) -> MediaMetadata:
        return await asyncio.to_thread(self._get_oembed_metadata, url)

    async def download(
        self, job: DownloadJob, progress_callback: ProgressCallback
    ) -> DownloadResult:
        return await asyncio.to_thread(self._download_sync, job, progress_callback)

    def _spotdl_settings(
        self, job: DownloadJob
    ) -> Tuple[Dict[str, object], Dict[str, object]]:
        from spotdl.utils.config import DOWNLOADER_OPTIONS, SPOTIFY_OPTIONS

        spotify_settings: Dict[str, object] = dict(SPOTIFY_OPTIONS)

        output_directory = self._resolve_output_directory(job)
        output_template = str(
            output_directory / "{artists} - {title}.{output-ext}"
        )
        selected_quality = job.options.quality or self.settings.default_quality
        bitrate = selected_quality if selected_quality in SPOTDL_BITRATES else "auto"

        downloader_settings: Dict[str, object] = dict(DOWNLOADER_OPTIONS)
        downloader_settings.update(
            {
                "output": output_template,
                "format": job.options.format or self.settings.default_audio_format,
                "bitrate": bitrate,
                "simple_tui": True,
                "threads": SPOTDL_DOWNLOAD_THREADS,
            }
        )
        return spotify_settings, downloader_settings

    def _resolve_output_directory(self, job: DownloadJob) -> Path:
        output_directory = job.options.output_directory
        base = output_directory.expanduser() if output_directory else self.settings.output_directory
        if output_directory and not base.is_absolute():
            base = self.settings.output_directory / base

        for part in Path(job.options.output_subfolder or "").parts:
            if part in {"", ".", ".."}:
                continue
            base = base / sanitize_filename(part)

        return base.expanduser()

    def _get_metadata_from_url(self, url: str) -> MediaMetadata:
        """Infer enough metadata for the UI without making a second Spotify API call."""

        parsed = urlparse(url)
        source_type = "audio"
        spotify_id = None
        if url.startswith("spotify:"):
            parts = url.split(":")
            if len(parts) >= 3:
                source_type = "audio" if parts[1] == "track" else parts[1]
                spotify_id = parts[2]
        else:
            path_parts = [part for part in parsed.path.split("/") if part]
            if len(path_parts) >= 2:
                source_type = "audio" if path_parts[0] == "track" else path_parts[0]
                spotify_id = path_parts[1]

        return MediaMetadata(
            source_url=url,
            title=f"Spotify {source_type}",
            media_type=source_type,
            provider=self.name,
            raw={"spotify_id": spotify_id},
        )

    def _download_sync(
        self, job: DownloadJob, progress_callback: ProgressCallback
    ) -> DownloadResult:
        try:
            spotify_settings, downloader_settings = self._spotdl_settings(job)

            progress_callback(5, "Resolving Spotify tracks")
            spotdl_client = None
            if self._is_spotify_track_url(job.url):
                songs = [self._song_from_preview_metadata(job.url, job.metadata)]
                progress_callback(
                    10,
                    "Using Spotify preview metadata to search YouTube",
                )
                self._attach_best_youtube_music_match(songs[0], downloader_settings)
                progress_callback(
                    15,
                    f"Matched YouTube Music result for {self._song_display_name(songs[0])}",
                )
            elif self._is_spotify_playlist_url(job.url):
                progress_callback(10, "Reading Spotify public playlist data")
                songs = self._songs_from_spotify_embed_collection(job.url, job.metadata)
                if songs:
                    progress_callback(
                        15,
                        f"Read {len(songs)} tracks from Spotify's public playlist data",
                    )
                else:
                    songs = self._songs_from_public_playlist_page(job.url, job.metadata)
                    public_track_count = self._public_playlist_track_count(songs)
                    if songs and public_track_count and len(songs) >= public_track_count:
                        progress_callback(
                            15,
                            f"Read all {len(songs)} tracks from Spotify's public playlist page",
                        )
                    elif songs and public_track_count and len(songs) < public_track_count:
                        raise ProviderError(
                            "spotify_playlist_incomplete",
                            (
                                f"Spotify's public page exposed only {len(songs)} of "
                                f"{public_track_count} playlist tracks. LynkOo could not "
                                "find a full public playlist listing, so it stopped instead "
                                "of downloading a partial playlist."
                            ),
                        )
                    elif songs:
                        raise ProviderError(
                            "spotify_playlist_incomplete",
                            (
                                "Spotify's public page exposed a partial playlist, but "
                                "not the full track count. LynkOo stopped instead of "
                                "downloading a partial playlist."
                            ),
                        )
                    else:
                        raise ProviderError(
                            "spotify_playlist_resolution_failed",
                            (
                                "Could not resolve the Spotify playlist track list from "
                                "public Spotify metadata. Try again later."
                            ),
                        )
            elif self._is_spotify_album_url(job.url):
                progress_callback(10, "Reading Spotify public album data")
                songs = self._songs_from_spotify_embed_collection(job.url, job.metadata)
                if songs:
                    progress_callback(
                        15,
                        f"Read {len(songs)} tracks from Spotify's public album data",
                    )
                else:
                    raise ProviderError(
                        "spotify_album_resolution_failed",
                        (
                            "Could not resolve the Spotify album track list from "
                            "public Spotify metadata. Try again later."
                        ),
                    )
            else:
                spotdl_client = self._create_spotdl_client(
                    spotify_settings,
                    downloader_settings,
                )
                songs = self._run_with_timeout(
                    lambda: spotdl_client.search([job.url]),
                    45,
                    "Spotify metadata resolution timed out. LynkOo could not read the track list quickly enough; try again later or paste individual track links.",
                )
            if not songs:
                raise ProviderError(
                    "no_spotify_results",
                    "No Spotify tracks were found for this URL.",
                )

            progress_callback(15, f"Resolved {len(songs)} Spotify track(s)")
            if songs:
                job.metadata = self._metadata_from_songs(job.url, songs)

            successful, provider_errors = self._download_songs_concurrently(
                songs,
                downloader_settings,
                progress_callback,
            )

            if not successful:
                return DownloadResult(
                    job_id=job.id,
                    success=False,
                    metadata=job.metadata,
                    error=StructuredError(
                        code="spotdl_download_failed",
                        message=provider_errors
                        or "spotDL did not return a downloaded file.",
                    ),
                )

            progress_callback(100, "spotDL download complete")
            return DownloadResult(
                job_id=job.id,
                success=True,
                file_path=successful[0],
                metadata=job.metadata,
            )
        except ProviderError:
            raise
        except Exception as exc:
            rate_limit_error = self._rate_limit_error(exc)
            if rate_limit_error is not None:
                return DownloadResult(
                    job_id=job.id,
                    success=False,
                    metadata=job.metadata,
                    error=rate_limit_error,
                )

            return DownloadResult(
                job_id=job.id,
                success=False,
                metadata=job.metadata,
                error=StructuredError(
                    code="spotdl_download_failed",
                    message=f"spotDL workflow failed: {exc}",
                ),
            )

    def _create_spotdl_client(
        self,
        spotify_settings: Dict[str, object],
        downloader_settings: Dict[str, object],
    ):
        from spotdl import Spotdl
        from spotdl.download.downloader import Downloader
        from spotdl.utils.spotify import SpotifyError

        try:
            return Spotdl(
                client_id=str(spotify_settings["client_id"]),
                client_secret=str(spotify_settings["client_secret"]),
                user_auth=False,
                headless=True,
                downloader_settings=downloader_settings,  # type: ignore[arg-type]
            )
        except SpotifyError as exc:
            if "already been initialized" not in str(exc):
                raise
            spotdl_client = Spotdl.__new__(Spotdl)
            spotdl_client.downloader = Downloader(
                settings=downloader_settings,  # type: ignore[arg-type]
            )
            return spotdl_client

    def _run_with_timeout(self, func, timeout_seconds: int, timeout_message: str):
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(func)
        try:
            return future.result(timeout=timeout_seconds)
        except concurrent.futures.TimeoutError as exc:
            future.cancel()
            raise ProviderError("spotify_resolution_timeout", timeout_message) from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _try_spotdl_playlist_resolution(
        self,
        url: str,
        spotify_settings: Dict[str, object],
        downloader_settings: Dict[str, object],
    ) -> Tuple[List[object], str]:
        try:
            spotdl_client = self._create_spotdl_client(
                spotify_settings,
                downloader_settings,
            )
            return self._run_with_timeout(
                lambda: spotdl_client.search([url]),
                45,
                "Spotify playlist resolution timed out.",
            ), ""
        except Exception as exc:  # pylint: disable=broad-except
            return [], str(exc)

    def _public_playlist_track_count(self, songs: List[object]) -> int | None:
        if not songs:
            return None
        first_json = getattr(songs[0], "json", {}) or {}
        value = first_json.get("list_length")
        return int(value) if value else None

    def _download_songs_concurrently(
        self,
        songs: List[object],
        downloader_settings: Dict[str, object],
        progress_callback: ProgressCallback,
    ) -> Tuple[List[Path], str]:
        successful: List[Path] = []
        errors: List[str] = []
        total = len(songs)
        max_workers = min(SPOTDL_DOWNLOAD_THREADS, total)

        progress_callback(
            15,
            f"Searching YouTube and downloading {total} track(s)",
        )
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_song = {
                executor.submit(
                    self._download_single_song,
                    song,
                    downloader_settings,
                ): song
                for song in songs
            }
            for completed_count, future in enumerate(
                concurrent.futures.as_completed(future_to_song),
                start=1,
            ):
                song = future_to_song[future]
                song_name = self._song_display_name(song)
                progress = 15 + int((completed_count / total) * 80)
                try:
                    path, downloader_errors, skipped = future.result()
                except Exception as exc:  # pylint: disable=broad-except
                    message = f"{song_name} - {exc}"
                    errors.append(message)
                    progress_callback(
                        progress,
                        f"Failed {song_name} ({completed_count}/{total})",
                    )
                    continue

                if path is not None:
                    successful.append(path)
                    progress_callback(
                        progress,
                        (
                            f"Skipped {song_name}; already in library ({completed_count}/{total})"
                            if skipped
                            else f"Downloaded {song_name} ({completed_count}/{total})"
                        ),
                    )
                else:
                    if downloader_errors:
                        errors.append(downloader_errors)
                    progress_callback(
                        progress,
                        downloader_errors
                        or f"No downloadable match for {song_name} ({completed_count}/{total})",
                    )

        return successful, " | ".join(errors[-3:])

    def _download_single_song(
        self,
        song: object,
        downloader_settings: Dict[str, object],
    ) -> Tuple[Path | None, str, bool]:
        from spotdl.download.downloader import Downloader

        existing_path = self._find_existing_library_file(song, downloader_settings)
        if existing_path is not None:
            return existing_path, "", True

        if getattr(song, "download_url", None) is None:
            self._attach_best_youtube_music_match(song, downloader_settings)

        single_song_settings = dict(downloader_settings)
        single_song_settings["threads"] = 1
        downloader = Downloader(settings=single_song_settings)
        _, path = downloader.download_song(song)
        provider_errors = self._provider_errors(downloader)
        if path is not None and not Path(path).exists():
            provider_errors = (
                f"spotDL reported {self._song_display_name(song)} as downloaded, "
                f"but the file is missing at {path}."
            )
            return None, provider_errors, False
        return path, provider_errors, False

    def _find_existing_library_file(
        self,
        song: object,
        downloader_settings: Dict[str, object],
    ) -> Path | None:
        from spotdl.utils.search import get_song_from_file_metadata

        master_directory = self.settings.output_directory.expanduser()
        if not master_directory.exists():
            return None

        selected_format = str(downloader_settings.get("format") or "").lower().lstrip(".")
        extensions = [selected_format, *SUPPORTED_AUDIO_FORMATS]
        extensions = [extension for index, extension in enumerate(extensions) if extension and extension not in extensions[:index]]
        expected_keys = self._local_song_keys(song)
        spotify_url = getattr(song, "url", None)

        for extension in extensions:
            for path in master_directory.glob(f"**/*.{extension}"):
                if not path.is_file():
                    continue
                try:
                    metadata_song = get_song_from_file_metadata(path)
                except Exception:  # pylint: disable=broad-except
                    metadata_song = None

                if spotify_url and metadata_song and getattr(metadata_song, "url", None) == spotify_url:
                    return path

                if metadata_song and self._local_song_keys(metadata_song) & expected_keys:
                    return path

                if self._normalize_local_song_key(path.stem) in expected_keys:
                    return path

        return None

    def _local_song_keys(self, song: object) -> set[str]:
        title = str(getattr(song, "name", "") or "")
        artist = str(getattr(song, "artist", "") or "")
        artists = getattr(song, "artists", None) or []
        keys = {
            self._normalize_local_song_key(self._song_display_name(song)),
            self._normalize_local_song_key(f"{artist} - {title}"),
        }
        for item in artists:
            keys.add(self._normalize_local_song_key(f"{item} - {title}"))
        return {key for key in keys if key}

    def _normalize_local_song_key(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", value.lower())

    def _attach_best_youtube_music_match(
        self,
        song: object,
        downloader_settings: Dict[str, object],
    ) -> None:
        from spotdl.providers.audio.ytmusic import YouTubeMusic

        matcher = YouTubeMusic(
            output_format=downloader_settings["format"],
            cookie_file=downloader_settings["cookie_file"],
            search_query=downloader_settings["search_query"],
            filter_results=False,
            yt_dlp_args=downloader_settings["yt_dlp_args"],
        )
        download_url = self._run_with_timeout(
            lambda: matcher.search(song), 20, "YouTube Music matching timed out."
        )
        if not download_url:
            raise ProviderError(
                "youtube_match_failed",
                f"No YouTube Music match was found for {self._song_display_name(song)}.",
        )
        song.download_url = download_url

    def _provider_errors(self, provider_or_downloader) -> str:
        downloader = getattr(provider_or_downloader, "downloader", provider_or_downloader)
        errors = getattr(downloader, "errors", [])
        if not errors:
            return ""
        return "spotDL failed: " + " | ".join(str(error) for error in errors[-3:])

    def _get_oembed_metadata(self, url: str) -> MediaMetadata:
        metadata = self._get_metadata_from_url(url)
        try:
            response = requests.get(
                "https://open.spotify.com/oembed",
                params={"url": url},
                timeout=5,
            )
            if response.status_code == 200:
                data = response.json()
                metadata.title = data.get("title") or metadata.title
                metadata.artist = data.get("author_name") or metadata.artist
                metadata.thumbnail_url = data.get("thumbnail_url") or metadata.thumbnail_url
                metadata.raw["oembed"] = {
                    "author_name": data.get("author_name"),
                    "provider_name": data.get("provider_name"),
                    "type": data.get("type"),
                }
        except requests.RequestException:
            pass

        if not metadata.artist or metadata.title == "Spotify audio":
            self._augment_metadata_from_spotify_page(url, metadata)

        return metadata

    def _augment_metadata_from_spotify_page(
        self, url: str, metadata: MediaMetadata
    ) -> None:
        try:
            response = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=5,
            )
        except requests.RequestException:
            return

        if response.status_code != 200:
            return

        html = response.text
        title = self._extract_meta_content(html, "og:title")
        description = self._extract_meta_content(html, "og:description")
        page_title = self._extract_page_title(html)

        if title:
            metadata.title = title

        if description:
            parts = [part.strip() for part in description.split("·")]
            if len(parts) >= 2:
                metadata.artist = parts[0] or metadata.artist
                metadata.title = parts[1] or metadata.title
            metadata.raw["page_description"] = description

        if page_title and not metadata.artist:
            match = re.search(r"song and lyrics by (.*?) \| Spotify", page_title)
            if match:
                metadata.artist = match.group(1).strip()

    def _extract_meta_content(self, html: str, property_name: str) -> str | None:
        patterns = (
            rf'<meta[^>]+(?:property|name)="{re.escape(property_name)}"[^>]+content="([^"]*)"',
            rf'<meta[^>]+content="([^"]*)"[^>]+(?:property|name)="{re.escape(property_name)}"',
        )
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return unescape(match.group(1)).strip()
        return None

    def _extract_page_title(self, html: str) -> str | None:
        match = re.search(r"<title>(.*?)</title>", html, re.DOTALL)
        if not match:
            return None
        return unescape(match.group(1)).strip()

    def _is_spotify_track_url(self, url: str) -> bool:
        if url.startswith("spotify:track:"):
            return True
        parsed = urlparse(url)
        return parsed.netloc.lower() == "open.spotify.com" and parsed.path.startswith("/track/")

    def _is_spotify_playlist_url(self, url: str) -> bool:
        if url.startswith("spotify:playlist:"):
            return True
        parsed = urlparse(url)
        return parsed.netloc.lower() == "open.spotify.com" and parsed.path.startswith("/playlist/")

    def _is_spotify_album_url(self, url: str) -> bool:
        if url.startswith("spotify:album:"):
            return True
        parsed = urlparse(url)
        return parsed.netloc.lower() == "open.spotify.com" and parsed.path.startswith("/album/")

    def _spotify_id_from_url(self, url: str) -> str:
        if url.startswith("spotify:"):
            parts = url.split(":")
            return parts[2] if len(parts) >= 3 else ""

        parsed = urlparse(url)
        path_parts = [part for part in parsed.path.split("/") if part]
        return path_parts[1] if len(path_parts) >= 2 else ""

    def _song_from_preview_metadata(self, url: str, metadata: MediaMetadata | None):
        preview = metadata or self._get_oembed_metadata(url)
        title = (preview.title or "").strip()
        artist = (preview.artist or "").strip()
        if not title:
            raise ProviderError(
                "spotify_preview_missing",
                "Could not read enough Spotify preview metadata to search YouTube.",
            )
        if not artist and " - " in title:
            maybe_artist, maybe_title = title.split(" - ", 1)
            artist = maybe_artist.strip()
            title = maybe_title.strip()
        artist = artist or "Unknown Artist"

        return self._song_from_basic_metadata(
            url=url,
            title=title,
            artist=artist,
            album=preview.album or title,
            cover_url=preview.thumbnail_url,
            duration_seconds=preview.duration_seconds or 0,
        )

    def _songs_from_spotify_embed_collection(
        self,
        url: str,
        metadata: MediaMetadata | None,
    ) -> List[object]:
        from bs4 import BeautifulSoup

        spotify_id = self._spotify_id_from_url(url)
        collection_type = self._spotify_collection_type(url)
        if not spotify_id or collection_type not in {"album", "playlist"}:
            return []

        embed_url = f"https://open.spotify.com/embed/{collection_type}/{spotify_id}"
        try:
            response = requests.get(
                embed_url,
                params={"utm_source": "generator"},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15,
            )
        except requests.RequestException:
            return []

        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        script = soup.find("script", id="__NEXT_DATA__")
        if script is None or not script.string:
            return []

        try:
            data = json.loads(script.string)
        except json.JSONDecodeError:
            return []

        entity = (
            data.get("props", {})
            .get("pageProps", {})
            .get("state", {})
            .get("data", {})
            .get("entity", {})
        )
        track_list = entity.get("trackList")
        if not isinstance(track_list, list):
            return []

        collection_name = (
            entity.get("title")
            or entity.get("name")
            or (metadata.title if metadata else None)
            or f"Spotify {collection_type}"
        )
        collection_artist = str(entity.get("subtitle") or "").strip()
        cover_url = self._first_cover_art_url(entity)
        songs: List[object] = []

        for index, track in enumerate(track_list, start=1):
            if not isinstance(track, dict) or track.get("entityType") != "track":
                continue

            title = str(track.get("title") or "").strip()
            artist = str(track.get("subtitle") or "").strip()
            spotify_uri = str(track.get("uri") or "")
            track_id = spotify_uri.rsplit(":", 1)[-1] if spotify_uri else ""
            if not title or not track_id:
                continue

            songs.append(
                self._song_from_basic_metadata(
                    url=f"https://open.spotify.com/track/{track_id}",
                    title=title,
                    artist=artist or "Unknown Artist",
                    album=collection_name,
                    cover_url=cover_url,
                    duration_seconds=int((track.get("duration") or 0) / 1000),
                    track_number=index,
                    tracks_count=len(track_list),
                    list_name=collection_name,
                    list_url=url,
                    list_position=index,
                    list_length=len(track_list),
                    album_artist=collection_artist or None,
                    album_type=collection_type,
                )
            )

        return songs

    def _spotify_collection_type(self, url: str) -> str:
        if url.startswith("spotify:"):
            parts = url.split(":")
            return parts[1] if len(parts) >= 2 else ""

        parsed = urlparse(url)
        path_parts = [part for part in parsed.path.split("/") if part]
        return path_parts[0] if path_parts else ""

    def _first_cover_art_url(self, entity: Dict[str, object]) -> str | None:
        cover_art = entity.get("coverArt")
        if not isinstance(cover_art, dict):
            return None
        sources = cover_art.get("sources")
        if not isinstance(sources, list) or not sources:
            return None
        first_source = sources[0]
        if not isinstance(first_source, dict):
            return None
        url = first_source.get("url")
        return str(url) if url else None

    def _songs_from_public_playlist_page(
        self,
        url: str,
        metadata: MediaMetadata | None,
    ) -> List[object]:
        from bs4 import BeautifulSoup

        try:
            response = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
        except requests.RequestException:
            return []

        if response.status_code != 200:
            return []

        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        playlist_name = (
            self._extract_meta_content(html, "og:title")
            or (metadata.title if metadata else None)
            or "Spotify playlist"
        )
        description = self._extract_meta_content(html, "og:description") or ""
        list_length = self._playlist_item_count(description)
        songs: List[object] = []
        seen_urls: set[str] = set()

        for row in soup.select('[data-testid="track-row"]'):
            track_link = next(
                (
                    link.get("href")
                    for link in row.find_all("a")
                    if (link.get("href") or "").startswith("/track/")
                ),
                None,
            )
            if not track_link:
                continue

            track_url = f"https://open.spotify.com{track_link}"
            if track_url in seen_urls:
                continue
            seen_urls.add(track_url)

            title = (row.get("aria-label") or "").strip()
            if not title:
                title_link = row.find("a", href=track_link)
                title = " ".join(title_link.stripped_strings) if title_link else ""

            artists = [
                " ".join(link.stripped_strings)
                for link in row.find_all("a")
                if (link.get("href") or "").startswith("/artist/")
            ]
            artist = ", ".join(artist for artist in artists if artist) or "Unknown Artist"
            image = row.find("img")
            cover_url = image.get("src") if image else None

            if not title:
                continue

            songs.append(
                self._song_from_basic_metadata(
                    url=track_url,
                    title=title,
                    artist=artist,
                    album=playlist_name,
                    cover_url=cover_url,
                    track_number=len(songs) + 1,
                    tracks_count=list_length or len(soup.select('[data-testid="track-row"]')),
                    list_name=playlist_name,
                    list_url=url,
                    list_position=len(songs) + 1,
                    list_length=list_length,
                )
            )

        return songs

    def _playlist_item_count(self, description: str) -> int | None:
        match = re.search(r"(\d+)\s+items?", description)
        return int(match.group(1)) if match else None

    def _song_from_basic_metadata(
        self,
        *,
        url: str,
        title: str,
        artist: str,
        album: str | None = None,
        cover_url: str | None = None,
        duration_seconds: int = 0,
        track_number: int = 1,
        tracks_count: int = 1,
        list_name: str | None = None,
        list_url: str | None = None,
        list_position: int | None = None,
        list_length: int | None = None,
        album_artist: str | None = None,
        album_type: str = "single",
    ):
        from spotdl.types.song import Song

        artists = [part.strip() for part in artist.split(",") if part.strip()]
        artists = artists or [artist or "Unknown Artist"]
        primary_artist = artists[0]

        return Song(
            name=title,
            artists=artists,
            artist=primary_artist,
            genres=[],
            disc_number=1,
            disc_count=1,
            album_name=album or title,
            album_artist=album_artist or primary_artist,
            duration=duration_seconds,
            year=0,
            date="",
            track_number=track_number,
            tracks_count=tracks_count,
            song_id=self._spotify_id_from_url(url),
            explicit=False,
            publisher="",
            url=url,
            isrc=None,
            cover_url=cover_url,
            copyright_text=None,
            album_id="",
            list_name=list_name,
            list_url=list_url,
            list_position=list_position,
            list_length=list_length,
            artist_id="",
            album_type=album_type,
        )

    def _metadata_from_songs(self, url: str, songs: List[object]) -> MediaMetadata:
        first_song = songs[0]
        first_json = getattr(first_song, "json", {}) or {}
        list_name = first_json.get("list_name")
        list_length = first_json.get("list_length") or len(songs)
        if self._is_spotify_album_url(url):
            media_type = "album"
        else:
            media_type = "playlist" if list_name or len(songs) > 1 else "audio"
        title = list_name or getattr(first_song, "name", None) or "Spotify audio"

        tracks = []
        for song in songs[:25]:
            song_json = getattr(song, "json", {}) or {}
            tracks.append(
                {
                    "title": getattr(song, "name", None),
                    "artist": getattr(song, "artist", None),
                    "album": getattr(song, "album_name", None),
                    "duration_seconds": getattr(song, "duration", None),
                    "position": song_json.get("list_position"),
                }
            )

        return MediaMetadata(
            source_url=url,
            title=title,
            artist=getattr(first_song, "artist", None) if media_type == "audio" else None,
            album=getattr(first_song, "album_name", None) if media_type == "audio" else None,
            duration_seconds=getattr(first_song, "duration", None)
            if media_type == "audio"
            else None,
            media_type=media_type,
            thumbnail_url=getattr(first_song, "cover_url", None),
            provider=self.name,
            raw={
                "spotify_id": first_json.get("list_url") or first_json.get("song_id"),
                "track_count": len(songs),
                "list_length": list_length,
                "tracks": tracks,
            },
        )

    def _song_display_name(self, song: object) -> str:
        display_name = getattr(song, "display_name", None)
        if display_name:
            return str(display_name)
        artist = getattr(song, "artist", None)
        title = getattr(song, "name", None)
        if artist and title:
            return f"{artist} - {title}"
        return str(title or "Spotify track")

    def _rate_limit_error(self, exc: Exception) -> StructuredError | None:
        message = str(exc)
        lowered = message.lower()
        is_rate_limit = any(
            marker in lowered
            for marker in ("429", "retry-after", "retry after", "rate limit", "rate/request limit", "rate-limited")
        )
        if not is_rate_limit:
            return None

        retry_after_match = re.search(r"(?:retry-after|retry after|after):?\s*(\d+)", lowered)
        retry_after = int(retry_after_match.group(1)) if retry_after_match else None
        human_retry = (
            f" Spotify asked clients to retry after {retry_after} seconds."
            if retry_after
            else ""
        )
        return StructuredError(
            code="spotify_rate_limited",
            message=(
                "Spotify rate-limited the metadata request, so LynkOo stopped "
                f"instead of waiting silently.{human_retry} LynkOo will use public "
                "preview metadata when Spotify exposes it; otherwise retry later "
                "or paste individual track links."
            ),
            details={"retry_after_seconds": retry_after} if retry_after else {},
        )
