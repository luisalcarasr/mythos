# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Download queue use cases."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Optional

from mythos.domain.entities import DownloadTask
from mythos.domain.events import DownloadCancelled, DownloadEnqueued, DownloadPaused, DownloadResumed
from mythos.domain.value_objects import AppName, GameStatus, Platform
from mythos.ports.input import CancelDownloadUseCase, EnqueueDownloadUseCase, PauseDownloadUseCase, ResumeDownloadUseCase
from mythos.ports.output import DownloadQueuePort, EpicStorePort, EventBus
from mythos.application.install import InstallGame, UpdateGame

logger = logging.getLogger(__name__)


class EnqueueDownload(EnqueueDownloadUseCase):
    """
    Add an install or update task to the download queue.

    This use case does NOT start the download immediately; it creates
    the task record and relies on the queue processor (driven by the
    event bus and GLib main loop) to pick it up.
    """

    def __init__(
        self,
        install_use_case: InstallGame,
        update_use_case: UpdateGame,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self._install = install_use_case
        self._update = update_use_case
        self._bus = event_bus

    def execute(
        self,
        app_name: AppName,
        kind: str = "install",
        install_path: Optional[Path] = None,
        platform: Optional[Platform] = None,
    ) -> DownloadTask:
        task = DownloadTask(
            id=str(uuid.uuid4()),
            app_name=app_name,
            kind=kind,
            status=GameStatus.QUEUED,
        )

        logger.info("Enqueuing %s task for %s", kind, app_name)

        if self._bus:
            self._bus.publish(
                DownloadEnqueued(
                    task_id=task.id,
                    app_name=str(app_name),
                    kind=kind,
                )
            )

        return task


class CancelDownload(CancelDownloadUseCase):
    def __init__(self, epic_store: EpicStorePort, event_bus: Optional[EventBus] = None) -> None:
        self._store = epic_store
        self._bus = event_bus

    def execute(self, task_id: str) -> None:
        logger.info("Cancelling download task %s", task_id)
        if self._bus:
            self._bus.publish(DownloadCancelled(task_id=task_id, app_name=""))


class PauseDownload(PauseDownloadUseCase):
    def __init__(
        self,
        queue: Optional[DownloadQueuePort] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self._queue = queue
        self._bus = event_bus

    def execute(self, task_id: str) -> None:
        logger.info("Pausing download task %s", task_id)
        if self._queue:
            self._queue.pause(task_id)
        if self._bus:
            self._bus.publish(DownloadPaused(task_id=task_id, app_name=""))


class ResumeDownload(ResumeDownloadUseCase):
    def __init__(
        self,
        queue: Optional[DownloadQueuePort] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self._queue = queue
        self._bus = event_bus

    def execute(self, task_id: str) -> None:
        logger.info("Resuming download task %s", task_id)
        if self._queue:
            self._queue.resume(task_id)
        if self._bus:
            self._bus.publish(DownloadResumed(task_id=task_id, app_name=""))
