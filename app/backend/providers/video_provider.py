"""Placeholder provider for public video platform URLs."""

from __future__ import annotations

from urllib.parse import urlparse

from app.backend.models.download_job import DownloadJob
from app.backend.models.download_result import (
    DownloadResult,
    MediaMetadata,
    ProviderCapability,
    StructuredError,
    ValidationResult,
)
from app.backend.providers.base import DownloadProvider, ProgressCallback, ProviderError

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


class VideoProvider(DownloadProvider):
    """Future seam for lawful public video providers."""

    name = "video_platform"
    display_name = "Public video platform"

    @property
    def capability(self) -> ProviderCapability:
        return ProviderCapability(
            name=self.name,
            display_name=self.display_name,
            source_types=["public video platform URL"],
            supports_metadata=False,
            supports_progress=False,
            supported_formats=["mp4", "webm"],
            supported_qualities=["best", "high", "medium", "low"],
            limitations=[
                "Platform video downloads are not enabled yet.",
                "The app will not bypass DRM, private content, account cookies, or access controls.",
            ],
        )

    def can_handle(self, url: str) -> bool:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and parsed.netloc.lower() in KNOWN_PLATFORM_HOSTS

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
            ok=False,
            provider=self.name,
            source_type="video",
            message="This public platform URL is recognized, but platform downloads are not enabled yet.",
            supported_formats=["mp4", "webm"],
            supported_qualities=["best", "high", "medium", "low"],
            error=StructuredError(
                code="provider_not_enabled",
                message="Only direct public media file URLs are currently enabled for video.",
            ),
        )

    async def get_metadata(self, url: str) -> MediaMetadata:
        return MediaMetadata(
            source_url=url,
            title="Unsupported video source",
            media_type="video",
            provider=self.name,
        )

    async def download(
        self, job: DownloadJob, progress_callback: ProgressCallback
    ) -> DownloadResult:
        raise ProviderError(
            "provider_not_enabled",
            "Platform video downloads are not enabled for this project yet.",
        )

