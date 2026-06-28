"""SQLite-backed queue for long-running lecture processing jobs."""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional
from uuid import uuid4

import cv2
import numpy as np

from .config import DATA_DIR
from .db import (audit, claim_next_processing_task, complete_processing_task,
                 create_processing_task, fail_interrupted_processing_tasks,
                 fail_processing_task)
from .pipeline import process_image

log = logging.getLogger(__name__)

QUEUE_DIR = DATA_DIR / "queue"


def _task_payload(*, image_path: Path, course_name: Optional[str],
                  owner_user_id: Optional[int], created_by_user_id: Optional[int],
                  visibility: str, course_id: Optional[int]) -> dict:
    return {
        "image_path": str(image_path),
        "course_name": course_name,
        "owner_user_id": owner_user_id,
        "created_by_user_id": created_by_user_id,
        "visibility": visibility,
        "course_id": course_id,
    }


class ProcessingQueue:
    """Small in-process worker over a durable SQLite task table.

    The queue state lives in SQLite so page refreshes and API restarts can show
    what happened. A single worker claims the oldest queued task and runs the
    expensive OpenCV/OCR/NLP/export pipeline in a thread so the FastAPI event
    loop stays responsive.
    """

    def __init__(self) -> None:
        self._runner: asyncio.Task | None = None
        self._wake_event: asyncio.Event | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stopping = False

    def start(self) -> None:
        if self._runner and not self._runner.done():
            return
        fail_interrupted_processing_tasks()
        self._loop = asyncio.get_running_loop()
        self._wake_event = asyncio.Event()
        self._stopping = False
        self._runner = asyncio.create_task(self._run(), name="processing-queue")

    async def stop(self) -> None:
        self._stopping = True
        self.wake()
        if not self._runner:
            return
        try:
            await asyncio.wait_for(self._runner, timeout=5)
        except asyncio.TimeoutError:
            log.warning("processing queue did not stop before timeout")

    def wake(self) -> None:
        if not self._loop or not self._wake_event:
            return
        self._loop.call_soon_threadsafe(self._wake_event.set)

    async def _run(self) -> None:
        assert self._wake_event is not None
        while not self._stopping:
            task = await asyncio.to_thread(claim_next_processing_task)
            if task is None:
                try:
                    await asyncio.wait_for(self._wake_event.wait(), timeout=2)
                except asyncio.TimeoutError:
                    pass
                self._wake_event.clear()
                continue
            await asyncio.to_thread(self._process, dict(task))

    def _process(self, task: dict) -> None:
        task_id = str(task["id"])
        try:
            payload = json.loads(task["payload"])
            image_path = Path(payload["image_path"])
            image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError("decode failed")

            result = process_image(
                image,
                course_name=payload.get("course_name"),
                owner_user_id=payload.get("owner_user_id"),
                visibility=payload.get("visibility") or "public",
                course_id=payload.get("course_id"),
            )
            lecture_id = result["lecture_id"]
            complete_processing_task(task_id, lecture_id=lecture_id)
            audit(
                payload.get("created_by_user_id", payload.get("owner_user_id")),
                f"{task['kind']}:complete",
                lecture_id,
                None,
            )
            try:
                image_path.unlink(missing_ok=True)
            except OSError:
                pass
        except Exception as exc:  # noqa: BLE001 - task failures are persisted.
            log.exception("processing task %s failed", task_id)
            fail_processing_task(task_id, error=str(exc) or exc.__class__.__name__)
            try:
                payload = json.loads(task["payload"])
                audit(
                    payload.get("created_by_user_id", payload.get("owner_user_id")),
                    f"{task['kind']}:failed",
                    task_id,
                    None,
                )
            except Exception:
                pass


processing_queue = ProcessingQueue()


def enqueue_upload_bytes(*, raw: bytes, extension: str, filename: Optional[str],
                         course_name: Optional[str], course_id: Optional[int],
                         owner_user_id: Optional[int], created_by_user_id: Optional[int],
                         visibility: str):
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    task_id = uuid4().hex
    suffix = extension if extension.startswith(".") else f".{extension}"
    image_path = QUEUE_DIR / f"{task_id}{suffix}"
    image_path.write_bytes(raw)
    row = create_processing_task(
        task_id=task_id,
        kind="upload",
        created_by_user_id=created_by_user_id,
        course_name=course_name,
        course_id=course_id,
        filename=filename,
        payload=_task_payload(
            image_path=image_path,
            course_name=course_name,
            owner_user_id=owner_user_id,
            created_by_user_id=created_by_user_id,
            visibility=visibility,
            course_id=course_id,
        ),
    )
    processing_queue.wake()
    return row


def enqueue_capture_frame(*, frame: np.ndarray, filename: str,
                          course_name: Optional[str], course_id: Optional[int],
                          owner_user_id: Optional[int], created_by_user_id: Optional[int],
                          visibility: str):
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    task_id = uuid4().hex
    image_path = QUEUE_DIR / f"{task_id}.jpg"
    if not cv2.imwrite(str(image_path), frame):
        raise ValueError("frame encode failed")
    row = create_processing_task(
        task_id=task_id,
        kind="capture",
        created_by_user_id=created_by_user_id,
        course_name=course_name,
        course_id=course_id,
        filename=filename,
        payload=_task_payload(
            image_path=image_path,
            course_name=course_name,
            owner_user_id=owner_user_id,
            created_by_user_id=created_by_user_id,
            visibility=visibility,
            course_id=course_id,
        ),
    )
    processing_queue.wake()
    return row
