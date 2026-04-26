"""Download orchestration and provider routing."""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, Iterable, List, Optional

from app.backend.models.download_job import (
    TERMINAL_STATES,
    DownloadJob,
    DownloadOptions,
    JobState,
)
from app.backend.models.download_result import (
    MediaMetadata,
    ProviderCapability,
    StructuredError,
    ValidationResult,
)
from app.backend.models.settings import AppSettings
from app.backend.providers import (
    DirectMediaProvider,
    DownloadProvider,
    SpotDLProvider,
    VideoProvider,
)
from app.backend.providers.base import ProviderError
from app.backend.services.job_queue import JobQueue
from app.backend.services.metadata_service import MetadataService

logger = logging.getLogger(__name__)
DEFAULT_MAX_CONCURRENT_DOWNLOADS = 4


class DownloadManager:
    """Routes URLs to providers and owns in-memory job state."""

    def __init__(
        self,
        settings: Optional[AppSettings] = None,
        providers: Optional[Iterable[DownloadProvider]] = None,
    ):
        self.settings = settings or AppSettings()
        self.providers = list(providers) if providers is not None else self._default_providers()
        self.jobs: Dict[str, DownloadJob] = {}
        self.queue = JobQueue(DEFAULT_MAX_CONCURRENT_DOWNLOADS)
        self.metadata_service = MetadataService()
        self._subscribers: List[asyncio.Queue[DownloadJob]] = []
        self._publish_loop: Optional[asyncio.AbstractEventLoop] = None

    def _default_providers(self) -> List[DownloadProvider]:
        return [
            SpotDLProvider(self.settings),
            DirectMediaProvider(self.settings),
            VideoProvider(self.settings),
        ]

    def update_settings(self, settings: AppSettings) -> None:
        self.settings = settings
        self.queue = JobQueue(DEFAULT_MAX_CONCURRENT_DOWNLOADS)
        self.providers = self._default_providers()

    def capabilities(self) -> List[ProviderCapability]:
        return [provider.capability for provider in self.providers]

    def list_jobs(self) -> List[DownloadJob]:
        return sorted(self.jobs.values(), key=lambda job: job.created_at, reverse=True)

    def get_job(self, job_id: str) -> Optional[DownloadJob]:
        return self.jobs.get(job_id)

    def detect_provider(self, url: str) -> Optional[DownloadProvider]:
        return next((provider for provider in self.providers if provider.can_handle(url)), None)

    async def validate_url(self, url: str) -> ValidationResult:
        provider = self.detect_provider(url)
        if provider is None:
            return ValidationResult(
                ok=False,
                message=(
                    "Unsupported link. Try a Spotify URL, a direct public media file URL, "
                    "or a yt-dlp-supported public video page."
                ),
                error=StructuredError(
                    code="unsupported_source",
                    message="No provider can handle this URL.",
                ),
            )
        return await provider.validate(url)

    async def inspect_url(self, url: str) -> MediaMetadata:
        provider = self.detect_provider(url)
        if provider is None:
            raise ProviderError("unsupported_source", "No provider can handle this URL.")
        return self.metadata_service.normalize(await provider.get_metadata(url))

    async def create_job(self, url: str, options: Optional[DownloadOptions] = None) -> DownloadJob:
        provider = self.detect_provider(url)
        if provider is None:
            job = DownloadJob(url=url, options=options or DownloadOptions())
            job.transition(JobState.FAILED, "Unsupported link")
            job.error = StructuredError(
                code="unsupported_source",
                message="No provider can handle this URL.",
            )
            self.jobs[job.id] = job
            await self._publish(job)
            return job

        job = DownloadJob(
            url=url,
            provider=provider.name,
            options=options or DownloadOptions(),
        )
        job.set_progress(1, "Queued for download")
        self.jobs[job.id] = job
        await self._publish(job)
        self.queue.enqueue(job, self._process_job)
        return job

    async def cancel_job(self, job_id: str) -> Optional[DownloadJob]:
        job = self.jobs.get(job_id)
        if job is None:
            return None
        if job.state in TERMINAL_STATES:
            return job
        cancelled_task = self.queue.cancel(job)
        if not cancelled_task:
            job.transition(JobState.CANCELLED, "Cancelled")
        await self._publish(job)
        return job

    async def retry_job(self, job_id: str) -> Optional[DownloadJob]:
        original = self.jobs.get(job_id)
        if original is None:
            return None
        return await self.create_job(original.url, original.options)

    async def subscribe(self) -> asyncio.Queue[DownloadJob]:
        queue: asyncio.Queue[DownloadJob] = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[DownloadJob]) -> None:
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    async def _process_job(self, job: DownloadJob) -> None:
        provider = self.detect_provider(job.url)
        if provider is None:
            await self._fail(job, "unsupported_source", "No provider can handle this URL.")
            return

        self._publish_loop = asyncio.get_running_loop()
        try:
            job.transition(JobState.VALIDATING, "Validating URL")
            await self._publish(job)
            validation = await provider.validate(job.url)
            if validation.metadata is not None:
                job.metadata = self.metadata_service.normalize(validation.metadata)
                await self._publish(job)
            if not validation.ok:
                error = validation.error or StructuredError(
                    code="validation_failed",
                    message=validation.message,
                )
                await self._fail(job, error.code, error.message)
                return

            job.transition(JobState.FETCHING_METADATA, "Fetching metadata")
            await self._publish(job)
            job.metadata = self.metadata_service.normalize(await provider.get_metadata(job.url))

            job.transition(JobState.DOWNLOADING, "Downloading")
            job.set_progress(max(job.progress, 1))
            await self._publish(job)

            result = await provider.download(
                job,
                lambda progress, message: self._update_progress(
                    job, progress, message
                ),
            )
            job.result = result
            if not result.success:
                error = result.error or StructuredError(
                    code="download_failed",
                    message="The provider could not complete this download.",
                )
                await self._fail(job, error.code, error.message)
                return

            job.transition(JobState.POSTPROCESSING, "Finalizing")
            job.set_progress(100)
            await self._publish(job)
            job.transition(JobState.COMPLETED, "Completed")
            await self._publish(job)
        except asyncio.CancelledError:
            job.transition(JobState.CANCELLED, "Cancelled")
            await self._publish(job)
        except ProviderError as exc:
            await self._fail(job, exc.code, exc.message)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Unhandled download job failure")
            await self._fail(job, "internal_error", str(exc))

    def _update_progress(self, job: DownloadJob, progress: int, message: str) -> None:
        if job.state == JobState.CANCELLED:
            return
        job.set_progress(progress, message)
        if self._publish_loop and self._publish_loop.is_running():
            self._publish_loop.call_soon_threadsafe(
                lambda: asyncio.create_task(self._publish(job))
            )

    async def _fail(self, job: DownloadJob, code: str, message: str) -> None:
        job.error = StructuredError(code=code, message=message)
        job.transition(JobState.FAILED, message)
        await self._publish(job)

    async def _publish(self, job: DownloadJob) -> None:
        for subscriber in list(self._subscribers):
            await subscriber.put(job.model_copy(deep=True))
