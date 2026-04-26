"""Download job routes and progress WebSocket."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.backend.api.deps import get_download_manager
from app.backend.models.download_job import DownloadJob, DownloadOptions, JobState
from app.backend.models.download_result import MediaMetadata, ValidationResult
from app.backend.providers.base import ProviderError
from app.backend.services.download_manager import DownloadManager
from app.backend.services.file_manager import FileManager

router = APIRouter(prefix="/api/downloads", tags=["downloads"])


class ValidateRequest(BaseModel):
    url: str


class InspectRequest(BaseModel):
    url: str


class CreateDownloadRequest(BaseModel):
    url: str
    options: Optional[DownloadOptions] = None


class OpenFolderResponse(BaseModel):
    opened: bool
    path: Path
    message: str


@router.post("/validate", response_model=ValidationResult)
async def validate_download(
    request: ValidateRequest,
    manager: DownloadManager = Depends(get_download_manager),
) -> ValidationResult:
    return await manager.validate_url(request.url)


@router.post("/inspect", response_model=MediaMetadata)
async def inspect_download(
    request: InspectRequest,
    manager: DownloadManager = Depends(get_download_manager),
) -> MediaMetadata:
    try:
        return await manager.inspect_url(request.url)
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc


@router.post("", response_model=DownloadJob)
async def create_download(
    request: CreateDownloadRequest,
    manager: DownloadManager = Depends(get_download_manager),
) -> DownloadJob:
    return await manager.create_job(request.url, request.options)


@router.get("", response_model=List[DownloadJob])
def list_downloads(
    manager: DownloadManager = Depends(get_download_manager),
) -> List[DownloadJob]:
    return manager.list_jobs()


@router.get("/{job_id}", response_model=DownloadJob)
def get_download(
    job_id: str,
    manager: DownloadManager = Depends(get_download_manager),
) -> DownloadJob:
    job = manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Download job not found")
    return job


@router.post("/{job_id}/cancel", response_model=DownloadJob)
async def cancel_download(
    job_id: str,
    manager: DownloadManager = Depends(get_download_manager),
) -> DownloadJob:
    job = await manager.cancel_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Download job not found")
    return job


@router.post("/{job_id}/retry", response_model=DownloadJob)
async def retry_download(
    job_id: str,
    manager: DownloadManager = Depends(get_download_manager),
) -> DownloadJob:
    job = await manager.retry_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Download job not found")
    return job


@router.post("/{job_id}/open-folder", response_model=OpenFolderResponse)
def open_download_folder(
    job_id: str,
    manager: DownloadManager = Depends(get_download_manager),
) -> OpenFolderResponse:
    job = manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Download job not found")
    if job.state != JobState.COMPLETED:
        raise HTTPException(status_code=400, detail="Download is not completed yet")

    folder = _download_folder(job, manager)
    if not folder.exists():
        raise HTTPException(status_code=404, detail=f"Folder does not exist: {folder}")

    opened, message = _open_folder_sync(folder)
    return OpenFolderResponse(opened=opened, path=folder, message=message)


def _download_folder(job: DownloadJob, manager: DownloadManager) -> Path:
    if job.result and job.result.file_path:
        result_path = Path(job.result.file_path).expanduser()
        if result_path.exists():
            return result_path if result_path.is_dir() else result_path.parent

    return FileManager(manager.settings).output_directory(
        job.options.output_directory,
        job.options.output_subfolder,
    )


def _open_folder_sync(folder: Path) -> tuple[bool, str]:
    try:
        if sys.platform == "darwin":
            completed = subprocess.run(
                ["open", str(folder)],
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode == 0:
                return True, "Folder opened."
            return False, completed.stderr.strip() or "Could not open folder."

        if sys.platform == "win32":
            os.startfile(str(folder))  # type: ignore[attr-defined]  # pylint: disable=no-member
            return True, "Folder opened."

        completed = subprocess.run(
            ["xdg-open", str(folder)],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0:
            return True, "Folder opened."
        return False, completed.stderr.strip() or "Could not open folder."
    except Exception as exc:  # pylint: disable=broad-except
        return False, f"Could not open folder: {exc}"


@router.websocket("/ws")
async def download_updates(
    websocket: WebSocket,
    manager: DownloadManager = Depends(get_download_manager),
):
    await websocket.accept()
    queue = await manager.subscribe()
    try:
        while True:
            job = await queue.get()
            await websocket.send_json(job.model_dump(mode="json"))
    except WebSocketDisconnect:
        manager.unsubscribe(queue)
