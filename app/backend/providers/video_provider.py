"""Provider for lawful public video platform URLs through yt-dlp."""

from __future__ import annotations

import asyncio
from pathlib import Path
from urllib.parse import urlparse

from app.backend.models.download_job import DownloadJob
from app.backend.models.download_result import (
    DownloadResult,
    MediaMetadata,
    ProviderCapability,
    StructuredError,
    ValidationResult,
)
from app.backend.models.settings import AppSettings
from app.backend.providers.base import DownloadProvider, ProgressCallback, ProviderError
from app.backend.services.file_manager import FileManager

KNOWN_PLATFORM_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
    "x.com",
    "twitter.com",
    "www.x.com",
    "www.twitter.com",
    "vimeo.com",
    "www.vimeo.com",
    "tiktok.com",
    "www.tiktok.com",
}

QUALITY_FORMATS = {
    "best": "bestvideo+bestaudio/best",
    "high": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
    "medium": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
    "low": "bestvideo[height<=480]+bestaudio/best[height<=480]/best",
}
VIDEO_FORMATS = {"mp4", "webm", "mov"}


class VideoProvider(DownloadProvider):
    """Downloads public, non-DRM platform videos when yt-dlp can access them."""

    name = "video_platform"
    display_name = "Public video platform"

    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.file_manager = FileManager(settings)

    @property
    def capability(self) -> ProviderCapability:
        return ProviderCapability(
            name=self.name,
            display_name=self.display_name,
            source_types=["public video platform URL"],
            supports_metadata=True,
            supports_progress=True,
            supported_formats=["mp4", "webm", "mov"],
            supported_qualities=["best", "high", "medium", "low"],
            limitations=[
                "Only public media that yt-dlp can access without credentials is supported.",
                "No cookies, DRM bypass, private content, login-gated media, "
                "or anti-bot circumvention.",
            ],
        )

    def can_handle(self, url: str) -> bool:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        return parsed.scheme in {"http", "https"} and (
            host in KNOWN_PLATFORM_HOSTS
            or host.endswith(".youtube.com")
            or host.endswith(".x.com")
            or host.endswith(".twitter.com")
            or host.endswith(".vimeo.com")
            or host.endswith(".tiktok.com")
        )

    async def validate(self, url: str) -> ValidationResult:
        if not self.can_handle(url):
            return ValidationResult(
                ok=False,
                provider=self.name,
                message="Unsupported video source.",
                error=StructuredError(
                    code="unsupported_source",
                    message="This source is not supported by the video provider.",
                ),
            )

        return ValidationResult(
            ok=True,
            provider=self.name,
            source_type="video",
            message=(
                "Public platform URL is supported when media is publicly accessible "
                "and permitted."
            ),
            supported_formats=["mp4", "webm", "mov"],
            supported_qualities=["best", "high", "medium", "low"],
        )

    async def get_metadata(self, url: str) -> MediaMetadata:
        return await asyncio.to_thread(self._get_metadata_sync, url)

    async def download(
        self, job: DownloadJob, progress_callback: ProgressCallback
    ) -> DownloadResult:
        return await asyncio.to_thread(self._download_sync, job, progress_callback)

    def _ydl_options(
        self,
        job: DownloadJob | None = None,
        output_template: str | None = None,
    ):
        quality = (job.options.quality if job else None) or self.settings.default_quality
        selected_format = self.settings.default_video_format
        if job and job.options.format and job.options.format in VIDEO_FORMATS:
            selected_format = job.options.format

        options = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": False,
            "ignoreerrors": False,
            "format": QUALITY_FORMATS.get(quality, QUALITY_FORMATS["best"]),
            "merge_output_format": selected_format,
            "restrictfilenames": False,
            "cookiefile": None,
            "retries": 3,
            "fragment_retries": 3,
        }
        if output_template is not None:
            options["outtmpl"] = output_template
        return options

    def _get_metadata_sync(self, url: str) -> MediaMetadata:
        try:
            from yt_dlp import YoutubeDL

            with YoutubeDL(self._ydl_options()) as ydl:
                info = ydl.extract_info(url, download=False)

            if info is None:
                raise ProviderError(
                    "metadata_unavailable",
                    "yt-dlp could not read metadata for this URL.",
                )

            entries = info.get("entries") or []
            first_entry = next((entry for entry in entries if entry), None)
            source = first_entry or info
            return MediaMetadata(
                source_url=url,
                title=source.get("title") or info.get("title") or "Platform video",
                artist=source.get("uploader") or source.get("channel"),
                duration_seconds=source.get("duration"),
                media_type="playlist" if entries else "video",
                thumbnail_url=source.get("thumbnail"),
                provider=self.name,
                raw={
                    "extractor": source.get("extractor_key") or info.get("extractor_key"),
                    "webpage_url": source.get("webpage_url") or info.get("webpage_url"),
                    "entry_count": len(entries),
                },
            )
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(
                "platform_metadata_failed",
                f"Could not inspect this public video URL: {exc}",
            ) from exc

    def _download_sync(
        self, job: DownloadJob, progress_callback: ProgressCallback
    ) -> DownloadResult:
        try:
            from yt_dlp import YoutubeDL

            output_dir = self.file_manager.output_directory(job.options.output_directory)
            output_template = str(output_dir / "%(title).180B [%(id)s].%(ext)s")

            def hook(status):
                if status.get("status") == "downloading":
                    total = status.get("total_bytes") or status.get("total_bytes_estimate")
                    downloaded = status.get("downloaded_bytes") or 0
                    if total:
                        progress_callback(
                            int(downloaded / total * 95),
                            "Downloading platform video",
                        )
                    else:
                        progress_callback(max(job.progress, 5), "Downloading platform video")
                elif status.get("status") == "finished":
                    progress_callback(96, "Merging and post-processing")

            options = self._ydl_options(job, output_template)
            options["progress_hooks"] = [hook]

            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(job.url, download=True)

            entries = info.get("entries") if info else None
            downloaded_files = []
            if entries:
                for entry in entries:
                    if not entry:
                        continue
                    path = entry.get("requested_downloads", [{}])[0].get("filepath")
                    if path:
                        downloaded_files.append(Path(path))
            else:
                for download in (info or {}).get("requested_downloads", []):
                    path = download.get("filepath")
                    if path:
                        downloaded_files.append(Path(path))

            progress_callback(100, "Platform video download complete")
            return DownloadResult(
                job_id=job.id,
                success=True,
                file_path=downloaded_files[0] if downloaded_files else None,
                metadata=job.metadata,
            )
        except Exception as exc:
            return DownloadResult(
                job_id=job.id,
                success=False,
                metadata=job.metadata,
                error=StructuredError(
                    code="platform_download_failed",
                    message=f"Public video download failed: {exc}",
                ),
            )
