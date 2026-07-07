# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""In-memory fake DownloadQueuePort."""

from __future__ import annotations

from typing import Optional

from mythos.domain.entities import DownloadTask
from mythos.ports.output import DownloadQueuePort


class FakeDownloadQueue(DownloadQueuePort):
    """
    In-memory download queue.

    The first task in the list is considered the active one.  Callers
    can pre-seed ``initial`` tasks for design mode (e.g. one in-progress
    install, one queued).
    """

    def __init__(self, initial: Optional[list[DownloadTask]] = None) -> None:
        self._tasks: list[DownloadTask] = list(initial or [])
        self._paused: set[str] = set()

    def enqueue(self, task: DownloadTask) -> None:
        self._tasks.append(task)

    def cancel(self, task_id: str) -> None:
        self._tasks = [t for t in self._tasks if t.id != task_id]

    def list_tasks(self) -> list[DownloadTask]:
        return list(self._tasks)

    def get_active(self) -> Optional[DownloadTask]:
        return self._tasks[0] if self._tasks else None

    def pause(self, task_id: str) -> None:
        self._paused.add(task_id)

    def resume(self, task_id: str) -> None:
        self._paused.discard(task_id)

    def is_paused(self, task_id: str) -> bool:
        return task_id in self._paused
