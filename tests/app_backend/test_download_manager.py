import asyncio

import pytest

from app.backend.models.download_job import DownloadJob, JobState
from app.backend.models.download_result import (
    DownloadResult,
    MediaMetadata,
    ProviderCapability,
    ValidationResult,
)
from app.backend.models.settings import AppSettings
from app.backend.providers.base import DownloadProvider, ProgressCallback
from app.backend.services.download_manager import DownloadManager


class MockProvider(DownloadProvider):
    name = "mock"
    display_name = "Mock Provider"

    @property
    def capability(self):
        return ProviderCapability(
            name=self.name,
            display_name=self.display_name,
            source_types=["test"],
            supported_formats=["mp3"],
            supported_qualities=["source"],
        )

    def can_handle(self, url: str) -> bool:
        return url.startswith("mock://")

    async def validate(self, url: str) -> ValidationResult:
        return ValidationResult(ok=True, provider=self.name, message="ok")

    async def get_metadata(self, url: str) -> MediaMetadata:
        return MediaMetadata(source_url=url, title="Mock Song", media_type="audio", provider=self.name)

    async def download(
        self, job: DownloadJob, progress_callback: ProgressCallback
    ) -> DownloadResult:
        progress_callback(50, "Halfway")
        await asyncio.sleep(0)
        progress_callback(100, "Done")
        return DownloadResult(job_id=job.id, success=True, metadata=job.metadata)


@pytest.mark.asyncio
async def test_job_completes_with_mock_provider():
    manager = DownloadManager(settings=AppSettings(), providers=[MockProvider()])
    job = await manager.create_job("mock://song")

    for _ in range(25):
        if job.state == JobState.COMPLETED:
            break
        await asyncio.sleep(0.01)

    assert job.state == JobState.COMPLETED
    assert job.progress == 100
    assert job.metadata is not None
    assert job.metadata.title == "Mock Song"


@pytest.mark.asyncio
async def test_unsupported_job_fails_gracefully():
    manager = DownloadManager(settings=AppSettings(), providers=[MockProvider()])
    job = await manager.create_job("https://example.com/not-supported")
    assert job.state == JobState.FAILED
    assert job.error is not None
    assert job.error.code == "unsupported_source"

