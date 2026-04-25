"""FastAPI dependencies."""

from __future__ import annotations

from starlette.requests import HTTPConnection

from app.backend.services.download_manager import DownloadManager


def get_download_manager(connection: HTTPConnection) -> DownloadManager:
    return connection.app.state.download_manager
