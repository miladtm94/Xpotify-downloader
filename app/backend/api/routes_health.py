"""Health and capability routes."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.backend.api.deps import get_download_manager
from app.backend.models.download_result import ProviderCapability
from app.backend.models.settings import DependencyStatus
from app.backend.services.download_manager import DownloadManager

router = APIRouter(prefix="/api", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    app: str
    python_version: str
    platform: str


def dependency_statuses() -> List[DependencyStatus]:
    ffmpeg_path = shutil.which("ffmpeg")
    ffmpeg_version = None
    if ffmpeg_path:
        try:
            completed = subprocess.run(
                [ffmpeg_path, "-version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=3,
            )
            ffmpeg_version = completed.stdout.splitlines()[0] if completed.stdout else None
        except Exception:  # pylint: disable=broad-except
            ffmpeg_version = None

    return [
        DependencyStatus(
            name="Python",
            available=True,
            version=sys.version.split()[0],
            message="Python runtime is available.",
        ),
        DependencyStatus(
            name="FFmpeg",
            available=ffmpeg_path is not None,
            version=ffmpeg_version,
            path=ffmpeg_path,
            message="FFmpeg is available." if ffmpeg_path else "FFmpeg was not found on PATH.",
        ),
        DependencyStatus(
            name="yt-dlp",
            available=shutil.which("yt-dlp") is not None,
            path=shutil.which("yt-dlp"),
            message="yt-dlp CLI is optional; spotDL also uses the Python package internally.",
        ),
    ]


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app="Xpotify Local Media Manager",
        python_version=sys.version.split()[0],
        platform=platform.platform(),
    )


@router.get("/dependencies", response_model=List[DependencyStatus])
def dependencies() -> List[DependencyStatus]:
    return dependency_statuses()


@router.get("/providers", response_model=List[ProviderCapability])
def providers(
    manager: DownloadManager = Depends(get_download_manager),
) -> List[ProviderCapability]:
    return manager.capabilities()

