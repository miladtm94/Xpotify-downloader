"""Provider interface for media sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

from app.backend.models.download_job import DownloadJob
from app.backend.models.download_result import (
    DownloadResult,
    MediaMetadata,
    ProviderCapability,
    StructuredError,
    ValidationResult,
)

ProgressCallback = Callable[[int, str], None]


class ProviderError(Exception):
    """Provider failure that can be mapped to a structured UI error."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message

    def to_structured_error(self) -> StructuredError:
        return StructuredError(code=self.code, message=self.message)


class DownloadProvider(ABC):
    """Base contract for current and future download providers."""

    name: str
    display_name: str

    @property
    @abstractmethod
    def capability(self) -> ProviderCapability:
        """Return the provider's user-visible capabilities."""

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Return whether this provider should validate and process a URL."""

    @abstractmethod
    async def validate(self, url: str) -> ValidationResult:
        """Validate a URL without downloading media."""

    @abstractmethod
    async def get_metadata(self, url: str) -> MediaMetadata:
        """Fetch or infer metadata for a URL."""

    @abstractmethod
    async def download(
        self, job: DownloadJob, progress_callback: ProgressCallback
    ) -> DownloadResult:
        """Download media for a job."""

