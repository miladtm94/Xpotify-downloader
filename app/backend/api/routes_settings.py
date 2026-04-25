"""Settings routes."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.backend.api.deps import get_download_manager
from app.backend.api.routes_health import dependency_statuses
from app.backend.models.settings import AppSettings, SettingsResponse
from app.backend.services.download_manager import DownloadManager

router = APIRouter(prefix="/api/settings", tags=["settings"])


class FolderSelectionResponse(BaseModel):
    selected: bool
    path: Optional[Path] = None
    message: str


@router.get("", response_model=SettingsResponse)
def get_settings(
    manager: DownloadManager = Depends(get_download_manager),
) -> SettingsResponse:
    return SettingsResponse(settings=manager.settings, dependencies=dependency_statuses())


@router.put("", response_model=SettingsResponse)
def update_settings(
    settings: AppSettings,
    manager: DownloadManager = Depends(get_download_manager),
) -> SettingsResponse:
    manager.update_settings(settings)
    return SettingsResponse(settings=manager.settings, dependencies=dependency_statuses())


@router.post("/select-output-directory", response_model=FolderSelectionResponse)
async def select_output_directory() -> FolderSelectionResponse:
    """Open a native folder picker from the local backend process."""

    return await asyncio.to_thread(_select_output_directory_sync)


def _select_output_directory_sync() -> FolderSelectionResponse:
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askdirectory(title="Choose Xpotify output folder")
        root.destroy()

        if not selected:
            return FolderSelectionResponse(
                selected=False,
                message="Folder selection was cancelled.",
            )

        return FolderSelectionResponse(
            selected=True,
            path=Path(selected).expanduser(),
            message="Output folder selected.",
        )
    except Exception as exc:  # pylint: disable=broad-except
        return FolderSelectionResponse(
            selected=False,
            message=(
                "Could not open the native folder picker. "
                f"You can still type a local folder path manually. Details: {exc}"
            ),
        )
