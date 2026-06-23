"""Background data-retention sweeper.

Deletes rows that serve no further purpose so the SQLite DB does not grow
unbounded on a long-running single-worker deployment:

* used / expired single-use tokens (password resets, email verifications)
* audit_log rows older than ``settings.retention_audit_days``

The sweep runs once at startup and then every ``settings.retention_sweep_hours``.
DB work happens in a thread so the FastAPI event loop stays responsive. Like the
processing queue this is per-process state; on restart it simply sweeps again.
"""
from __future__ import annotations

import asyncio
import logging

from ..config import settings
from ..db import (purge_expired_email_verifications,
                  purge_expired_password_resets, purge_old_audit_log)

log = logging.getLogger(__name__)


def _sweep_once() -> dict[str, int]:
    return {
        "password_resets": purge_expired_password_resets(),
        "email_verifications": purge_expired_email_verifications(),
        "audit_log": purge_old_audit_log(settings.retention_audit_days),
    }


class RetentionSweeper:
    def __init__(self) -> None:
        self._runner: asyncio.Task | None = None
        self._stopping: asyncio.Event | None = None

    def start(self) -> None:
        if self._runner and not self._runner.done():
            return
        self._stopping = asyncio.Event()
        self._runner = asyncio.create_task(self._run(), name="retention-sweeper")

    async def stop(self) -> None:
        if not self._runner or not self._stopping:
            return
        self._stopping.set()
        try:
            await asyncio.wait_for(self._runner, timeout=5)
        except asyncio.TimeoutError:
            log.warning("retention sweeper did not stop before timeout")

    async def _run(self) -> None:
        assert self._stopping is not None
        interval = max(60.0, settings.retention_sweep_hours * 3600.0)
        while not self._stopping.is_set():
            try:
                deleted = await asyncio.to_thread(_sweep_once)
                if any(deleted.values()):
                    log.info("retention sweep deleted %s", deleted)
            except Exception:  # noqa: BLE001 - never let a sweep failure kill the loop
                log.exception("retention sweep failed")
            try:
                await asyncio.wait_for(self._stopping.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass


retention_sweeper = RetentionSweeper()
