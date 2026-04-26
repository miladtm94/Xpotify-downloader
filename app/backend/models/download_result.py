"""Shared result and provider contract models."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StructuredError(BaseModel):
    """Error payloads that are safe to display in the UI."""

    code: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class ProviderCapability(BaseModel):
    """User-facing capability summary for one provider."""

    name: str
    display_name: str
    source_types: List[str]
    supports_metadata: bool = True
    supports_progress: bool = True
    supports_cancel: bool = False
    supported_formats: List[str] = Field(default_factory=list)
    supported_qualities: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


class MediaMetadata(BaseModel):
    """Provider-neutral media metadata."""

    source_url: str
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    duration_seconds: Optional[int] = None
    media_type: str = "unknown"
    thumbnail_url: Optional[str] = None
    provider: Optional[str] = None
    raw: Dict[str, Any] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    """Result returned when a provider validates a URL."""

    ok: bool
    provider: Optional[str] = None
    source_type: Optional[str] = None
    message: str
    supported_formats: List[str] = Field(default_factory=list)
    supported_qualities: List[str] = Field(default_factory=list)
    metadata: Optional[MediaMetadata] = None
    error: Optional[StructuredError] = None


class DownloadResult(BaseModel):
    """Final result for a completed or failed download."""

    job_id: str
    success: bool
    file_path: Optional[Path] = None
    metadata: Optional[MediaMetadata] = None
    error: Optional[StructuredError] = None
