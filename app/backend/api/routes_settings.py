"""Settings routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.backend.api.deps import get_download_manager
from app.backend.api.routes_health import dependency_statuses
from app.backend.models.settings import AppSettings, SettingsResponse
from app.backend.services.download_manager import DownloadManager

router = APIRouter(prefix="/api/settings", tags=["settings"])


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

