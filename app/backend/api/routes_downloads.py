"""Download job routes and progress WebSocket."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.backend.api.deps import get_download_manager
from app.backend.models.download_job import DownloadJob, DownloadOptions
from app.backend.models.download_result import ValidationResult
from app.backend.services.download_manager import DownloadManager

router = APIRouter(prefix="/api/downloads", tags=["downloads"])


class ValidateRequest(BaseModel):
    url: str


class CreateDownloadRequest(BaseModel):
    url: str
    options: Optional[DownloadOptions] = None


@router.post("/validate", response_model=ValidationResult)
async def validate_download(
    request: ValidateRequest,
    manager: DownloadManager = Depends(get_download_manager),
) -> ValidationResult:
    return await manager.validate_url(request.url)


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

