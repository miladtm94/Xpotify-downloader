"""Provider wrapper around the existing spotDL audio workflow."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Dict, List, Tuple

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
from app.backend.utils.validation import is_spotify_url


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
            supported_qualities=["best", "128k", "256k"],
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

        return ValidationResult(
            ok=True,
            provider=self.name,
            source_type="spotify_metadata",
            message="Spotify metadata URL is supported. Audio will be matched through spotDL providers.",
            supported_formats=SUPPORTED_AUDIO_FORMATS,
            supported_qualities=["best", "128k", "256k"],
        )

    async def get_metadata(self, url: str) -> MediaMetadata:
        return await asyncio.to_thread(self._get_metadata_sync, url)

    async def download(
        self, job: DownloadJob, progress_callback: ProgressCallback
    ) -> DownloadResult:
        return await asyncio.to_thread(self._download_sync, job, progress_callback)

    def _spotdl_settings(self, job: DownloadJob) -> Tuple[Dict[str, object], Dict[str, object]]:
        from spotdl.utils.config import DOWNLOADER_OPTIONS, SPOTIFY_OPTIONS

        spotify_settings: Dict[str, object] = dict(SPOTIFY_OPTIONS)
        if self.settings.spotify_client_id:
            spotify_settings["client_id"] = self.settings.spotify_client_id
        if self.settings.spotify_client_secret:
            spotify_settings["client_secret"] = self.settings.spotify_client_secret

        output_directory = job.options.output_directory or self.settings.output_directory
        output_template = str(Path(output_directory).expanduser() / "{artists} - {title}.{output-ext}")

        downloader_settings: Dict[str, object] = dict(DOWNLOADER_OPTIONS)
        downloader_settings.update(
            {
                "output": output_template,
                "format": job.options.format or self.settings.default_audio_format,
                "bitrate": job.options.quality or self.settings.default_quality,
                "simple_tui": True,
                "threads": 1,
            }
        )
        return spotify_settings, downloader_settings

    def _get_metadata_sync(self, url: str) -> MediaMetadata:
        try:
            from spotdl.types.album import Album
            from spotdl.types.artist import Artist
            from spotdl.types.playlist import Playlist
            from spotdl.types.song import Song
            from spotdl.utils.config import SPOTIFY_OPTIONS
            from spotdl.utils.spotify import SpotifyClient

            SpotifyClient.init(
                client_id=self.settings.spotify_client_id or SPOTIFY_OPTIONS["client_id"],
                client_secret=self.settings.spotify_client_secret or SPOTIFY_OPTIONS["client_secret"],
                user_auth=False,
                headless=True,
            )

            if "track" in url or url.startswith("spotify:track"):
                song = Song.from_url(url)
                return MediaMetadata(
                    source_url=url,
                    title=song.name,
                    artist=song.artist,
                    album=song.album_name,
                    duration_seconds=song.duration,
                    media_type="audio",
                    thumbnail_url=song.cover_url,
                    provider=self.name,
                    raw=song.json,
                )
            if "album" in url or url.startswith("spotify:album"):
                album = Album.from_url(url, fetch_songs=False)
                return MediaMetadata(source_url=url, title=album.name, media_type="album", provider=self.name)
            if "playlist" in url or url.startswith("spotify:playlist"):
                playlist = Playlist.from_url(url, fetch_songs=False)
                return MediaMetadata(source_url=url, title=playlist.name, media_type="playlist", provider=self.name)
            if "artist" in url or url.startswith("spotify:artist"):
                artist = Artist.from_url(url, fetch_songs=False)
                return MediaMetadata(source_url=url, title=artist.name, media_type="artist", provider=self.name)
        except Exception as exc:
            raise ProviderError(
                "spotify_metadata_failed",
                f"Could not fetch Spotify metadata: {exc}",
            ) from exc

        return MediaMetadata(source_url=url, title="Spotify media", media_type="audio", provider=self.name)

    def _download_sync(
        self, job: DownloadJob, progress_callback: ProgressCallback
    ) -> DownloadResult:
        try:
            from spotdl import Spotdl

            spotify_settings, downloader_settings = self._spotdl_settings(job)
            spotdl_client = Spotdl(
                client_id=str(spotify_settings["client_id"]),
                client_secret=str(spotify_settings["client_secret"]),
                user_auth=False,
                headless=True,
                downloader_settings=downloader_settings,  # type: ignore[arg-type]
            )

            progress_callback(5, "Resolving Spotify metadata")
            songs = spotdl_client.search([job.url])
            if not songs:
                raise ProviderError("no_spotify_results", "No Spotify tracks were found for this URL.")

            progress_callback(20, "Downloading matched audio")
            results = spotdl_client.download_songs(songs)
            successful: List[Path] = [path for _song, path in results if path is not None]
            if not successful:
                return DownloadResult(
                    job_id=job.id,
                    success=False,
                    metadata=job.metadata,
                    error=StructuredError(
                        code="spotdl_download_failed",
                        message="spotDL did not return a downloaded file.",
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
            return DownloadResult(
                job_id=job.id,
                success=False,
                metadata=job.metadata,
                error=StructuredError(
                    code="spotdl_download_failed",
                    message=f"spotDL workflow failed: {exc}",
                ),
            )

