"""Async queue for bounded download execution."""

from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Dict

from app.backend.models.download_job import DownloadJob, JobState

JobWorker = Callable[[DownloadJob], Awaitable[None]]


class JobQueue:
    """A minimal bounded background task queue."""

    def __init__(self, max_concurrent: int):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._tasks: Dict[str, asyncio.Task[None]] = {}

    def enqueue(self, job: DownloadJob, worker: JobWorker) -> None:
        task = asyncio.create_task(self._run(job, worker))
        self._tasks[job.id] = task
        task.add_done_callback(lambda _task: self._tasks.pop(job.id, None))

    def cancel(self, job: DownloadJob) -> bool:
        task = self._tasks.get(job.id)
        if task is None:
            return False
        job.transition(JobState.CANCELLED, "Cancelled")
        task.cancel()
        return True

    async def _run(self, job: DownloadJob, worker: JobWorker) -> None:
        async with self._semaphore:
            await worker(job)

