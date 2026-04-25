"""Provider wrapper around the existing spotDL audio workflow."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urlparse

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
            message=(
                "Spotify metadata URL is supported. Audio will be matched "
                "through spotDL providers."
            ),
            supported_formats=SUPPORTED_AUDIO_FORMATS,
            supported_qualities=["best", "128k", "256k"],
        )

    async def get_metadata(self, url: str) -> MediaMetadata:
        return self._get_metadata_from_url(url)

    async def download(
        self, job: DownloadJob, progress_callback: ProgressCallback
    ) -> DownloadResult:
        return await asyncio.to_thread(self._download_sync, job, progress_callback)

    def _spotdl_settings(
        self, job: DownloadJob
    ) -> Tuple[Dict[str, object], Dict[str, object]]:
        from spotdl.utils.config import DOWNLOADER_OPTIONS, SPOTIFY_OPTIONS

        spotify_settings: Dict[str, object] = dict(SPOTIFY_OPTIONS)
        if self.settings.spotify_client_id:
            spotify_settings["client_id"] = self.settings.spotify_client_id
        if self.settings.spotify_client_secret:
            spotify_settings["client_secret"] = self.settings.spotify_client_secret

        output_directory = job.options.output_directory or self.settings.output_directory
        output_template = str(
            Path(output_directory).expanduser() / "{artists} - {title}.{output-ext}"
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
                "threads": 1,
            }
        )
        return spotify_settings, downloader_settings

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
                raise ProviderError(
                    "no_spotify_results",
                    "No Spotify tracks were found for this URL.",
                )

            progress_callback(20, "Downloading matched audio")
            results = spotdl_client.download_songs(songs)
            successful: List[Path] = [path for _song, path in results if path is not None]
            if songs and job.metadata:
                first_song = songs[0]
                job.metadata.title = first_song.name
                job.metadata.artist = first_song.artist
                job.metadata.album = first_song.album_name
                job.metadata.duration_seconds = first_song.duration
                job.metadata.thumbnail_url = first_song.cover_url
                job.metadata.raw = first_song.json
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
