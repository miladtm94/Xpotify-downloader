"""Application settings and dependency status models."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

SUPPORTED_AUDIO_FORMATS = ["mp3", "m4a", "opus", "flac", "wav", "ogg"]
SUPPORTED_VIDEO_FORMATS = ["mp4", "webm", "mov"]
SUPPORTED_QUALITIES = ["best", "high", "medium", "low"]


class AppSettings(BaseModel):
    """Runtime settings for the local media manager."""

    model_config = ConfigDict(validate_assignment=True)

    output_directory: Path = Field(
        default_factory=lambda: Path.home() / "Music" / "Xpotify"
    )
    default_audio_format: str = "mp3"
    default_video_format: str = "mp4"
    default_quality: str = "best"
    max_concurrent_downloads: int = Field(default=2, ge=1, le=8)
    theme: str = "system"
    spotify_client_id: Optional[str] = None
    spotify_client_secret: Optional[str] = None

    @field_validator("output_directory", mode="before")
    @classmethod
    def normalize_output_directory(cls, value: object) -> Path:
        return Path(value).expanduser()

    @field_validator("default_audio_format")
    @classmethod
    def validate_audio_format(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in SUPPORTED_AUDIO_FORMATS:
            raise ValueError(f"Unsupported audio format: {value}")
        return normalized

    @field_validator("default_video_format")
    @classmethod
    def validate_video_format(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in SUPPORTED_VIDEO_FORMATS:
            raise ValueError(f"Unsupported video format: {value}")
        return normalized

    @field_validator("default_quality")
    @classmethod
    def validate_quality(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in SUPPORTED_QUALITIES:
            raise ValueError(f"Unsupported quality: {value}")
        return normalized

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in {"system", "light", "dark"}:
            raise ValueError(f"Unsupported theme: {value}")
        return normalized


class DependencyStatus(BaseModel):
    """A single dependency status row for the Settings page."""

    name: str
    available: bool
    version: Optional[str] = None
    path: Optional[str] = None
    message: str


class SettingsResponse(BaseModel):
    """Settings plus computed dependency status."""

    settings: AppSettings
    dependencies: List[DependencyStatus]

