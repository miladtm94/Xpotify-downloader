"""Provider for direct public media file URLs."""

from __future__ import annotations

import asyncio
from pathlib import PurePosixPath
from urllib.parse import unquote, urlparse

import requests

from app.backend.models.download_job import DownloadJob
from app.backend.models.download_result import (
    DownloadResult,
    MediaMetadata,
    ProviderCapability,
    StructuredError,
    ValidationResult,
)
from app.backend.models.settings import (
    SUPPORTED_AUDIO_FORMATS,
    SUPPORTED_VIDEO_FORMATS,
    AppSettings,
)
from app.backend.providers.base import DownloadProvider, ProgressCallback, ProviderError
from app.backend.services.file_manager import FileManager
from app.backend.utils.validation import (
    DIRECT_AUDIO_EXTENSIONS,
    DIRECT_VIDEO_EXTENSIONS,
    direct_media_type,
    get_url_extension,
    is_direct_media_url,
    parse_http_url,
)


class DirectMediaProvider(DownloadProvider):
    """Downloads direct, public media file URLs without platform scraping."""

    name = "direct_media"
    display_name = "Direct media URL"

    def __init__(self, settings: AppSettings):
        self.settings = settings
        self.file_manager = FileManager(settings)

    @property
    def capability(self) -> ProviderCapability:
        return ProviderCapability(
            name=self.name,
            display_name=self.display_name,
            source_types=["direct audio file", "direct video file"],
            supported_formats=SUPPORTED_AUDIO_FORMATS + SUPPORTED_VIDEO_FORMATS,
            supported_qualities=["source"],
            limitations=[
                "Only direct public media files are supported.",
                "No DRM bypass, login cookies, private scraping, or anti-bot circumvention.",
            ],
        )

    def can_handle(self, url: str) -> bool:
        return is_direct_media_url(url)

    async def validate(self, url: str) -> ValidationResult:
        if parse_http_url(url) is None:
            return ValidationResult(
                ok=False,
                provider=self.name,
                message="Only http(s) direct media URLs are supported.",
                error=StructuredError(
                    code="invalid_url",
                    message="Enter a valid http(s) media URL.",
                ),
            )

        extension = get_url_extension(url)
        if extension not in DIRECT_AUDIO_EXTENSIONS | DIRECT_VIDEO_EXTENSIONS:
            return ValidationResult(
                ok=False,
                provider=self.name,
                message="This URL does not point to a supported direct media file.",
                error=StructuredError(
                    code="unsupported_format",
                    message="Use a direct .mp3, .m4a, .flac, .wav, .ogg, .opus, .mp4, .webm, or .mov URL.",
                ),
            )

        return ValidationResult(
            ok=True,
            provider=self.name,
            source_type=direct_media_type(url),
            message="Direct public media URL is supported.",
            supported_formats=[extension.lstrip(".")],
            supported_qualities=["source"],
        )

    async def get_metadata(self, url: str) -> MediaMetadata:
        parsed = urlparse(url)
        title = PurePosixPath(unquote(parsed.path)).name or "download"
        return MediaMetadata(
            source_url=url,
            title=title,
            media_type=direct_media_type(url),
            provider=self.name,
        )

    async def download(
        self, job: DownloadJob, progress_callback: ProgressCallback
    ) -> DownloadResult:
        return await asyncio.to_thread(self._download_sync, job, progress_callback)

    def _download_sync(
        self, job: DownloadJob, progress_callback: ProgressCallback
    ) -> DownloadResult:
        extension = get_url_extension(job.url)
        if extension is None:
            raise ProviderError("unsupported_format", "Could not determine media extension.")

        metadata = job.metadata or MediaMetadata(
            source_url=job.url,
            title="download",
            media_type=direct_media_type(job.url),
            provider=self.name,
        )
        output_path = self.file_manager.available_path(
            metadata.title or "download",
            extension,
            job.options.output_directory,
        )

        try:
            with requests.get(job.url, stream=True, timeout=30) as response:
                response.raise_for_status()
                total = int(response.headers.get("content-length", "0") or "0")
                downloaded = 0
                with output_path.open("wb") as media_file:
                    for chunk in response.iter_content(chunk_size=1024 * 256):
                        if job.state.value == "cancelled":
                            raise ProviderError("cancelled", "Download was cancelled.")
                        if not chunk:
                            continue
                        media_file.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            percent = int(downloaded / total * 100)
                            progress_callback(percent, "Downloading direct media")

            progress_callback(100, "Download complete")
            return DownloadResult(
                job_id=job.id,
                success=True,
                file_path=output_path,
                metadata=metadata,
            )
        except ProviderError:
            if output_path.exists():
                output_path.unlink()
            raise
        except requests.RequestException as exc:
            if output_path.exists():
                output_path.unlink()
            return DownloadResult(
                job_id=job.id,
                success=False,
                metadata=metadata,
                error=StructuredError(
                    code="download_failed",
                    message=f"Direct media download failed: {exc}",
                ),
            )

