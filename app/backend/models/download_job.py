"""Download job models and state transitions."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from app.backend.models.download_result import (
    DownloadResult,
    MediaMetadata,
    StructuredError,
)


class JobState(str, Enum):
    """Lifecycle states exposed to the API and UI."""

    QUEUED = "queued"
    VALIDATING = "validating"
    FETCHING_METADATA = "fetching_metadata"
    DOWNLOADING = "downloading"
    POSTPROCESSING = "postprocessing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_STATES = {JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED}


class DownloadOptions(BaseModel):
    """Per-job options selected by the user."""

    output_directory: Optional[Path] = None
    output_subfolder: Optional[str] = None
    media_mode: str = "auto"
    format: Optional[str] = None
    quality: Optional[str] = None
    overwrite: bool = False

    @field_validator("output_directory", mode="before")
    @classmethod
    def normalize_output_directory(cls, value: object) -> Optional[Path]:
        if value in (None, ""):
            return None
        return Path(value).expanduser()

    @field_validator("output_subfolder", mode="before")
    @classmethod
    def normalize_output_subfolder(cls, value: object) -> Optional[str]:
        if value in (None, ""):
            return None
        subfolder = str(value).strip().strip("/\\")
        if not subfolder:
            return None
        path = Path(subfolder)
        if path.is_absolute() or any(part in {"..", "."} for part in path.parts):
            raise ValueError("Output subfolder must be a relative folder name.")
        return subfolder

    @field_validator("media_mode")
    @classmethod
    def validate_media_mode(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in {"auto", "audio", "video"}:
            raise ValueError(f"Unsupported media mode: {value}")
        return normalized


class DownloadJob(BaseModel):
    """A single managed download job."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    url: str
    provider: Optional[str] = None
    state: JobState = JobState.QUEUED
    options: DownloadOptions = Field(default_factory=DownloadOptions)
    progress: int = Field(default=0, ge=0, le=100)
    status_message: str = "Queued"
    metadata: Optional[MediaMetadata] = None
    result: Optional[DownloadResult] = None
    error: Optional[StructuredError] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def transition(self, state: JobState, message: Optional[str] = None) -> None:
        """Move the job to a new state with a UI-safe status message."""

        self.state = state
        self.updated_at = datetime.utcnow()
        if state == JobState.DOWNLOADING and self.started_at is None:
            self.started_at = self.updated_at
        if state in TERMINAL_STATES:
            self.completed_at = self.updated_at
        if message:
            self.status_message = message

    def set_progress(self, progress: int, message: Optional[str] = None) -> None:
        self.progress = max(0, min(100, progress))
        self.updated_at = datetime.utcnow()
        if message:
            self.status_message = message
