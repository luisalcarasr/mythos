# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for download use cases and Progress formatters."""

from __future__ import annotations

import pytest

from mythos.adapters.output.fakes.fake_download_queue import FakeDownloadQueue
from mythos.adapters.output.fakes.fake_event_bus import FakeEventBus
from mythos.application.downloads import PauseDownload, ResumeDownload
from mythos.domain.events import DownloadPaused, DownloadResumed
from mythos.domain.value_objects import Progress


# ---------------------------------------------------------------------------
# Progress formatters
# ---------------------------------------------------------------------------


def test_progress_downloaded_human() -> None:
    p = Progress(fraction=0.5, downloaded_bytes=512 * 1024 * 1024, total_bytes=1024 * 1024 * 1024)
    assert p.downloaded_human == "512.0 MiB"


def test_progress_total_human() -> None:
    p = Progress(fraction=0.0, total_bytes=int(65 * 1024 ** 3))
    assert "GiB" in p.total_human


def test_progress_eta_human_minutes() -> None:
    p = Progress(fraction=0.5, eta_seconds=450)
    assert p.eta_human == "7m 30s"


def test_progress_eta_human_hours() -> None:
    p = Progress(fraction=0.1, eta_seconds=3900)
    assert p.eta_human == "1h 5m"


def test_progress_eta_human_done() -> None:
    p = Progress(fraction=1.0, eta_seconds=0)
    assert p.eta_human == "—"


def test_progress_eta_human_seconds_only() -> None:
    p = Progress(fraction=0.9, eta_seconds=45)
    assert p.eta_human == "45s"


# ---------------------------------------------------------------------------
# PauseDownload use case
# ---------------------------------------------------------------------------


def test_pause_publishes_event() -> None:
    queue = FakeDownloadQueue()
    bus = FakeEventBus()
    uc = PauseDownload(queue=queue, event_bus=bus)

    uc.execute("task-abc")

    events = bus.events_of(DownloadPaused)
    assert len(events) == 1
    assert events[0].task_id == "task-abc"


def test_pause_calls_queue() -> None:
    queue = FakeDownloadQueue()
    bus = FakeEventBus()
    uc = PauseDownload(queue=queue, event_bus=bus)

    uc.execute("task-abc")

    assert queue.is_paused("task-abc")


# ---------------------------------------------------------------------------
# ResumeDownload use case
# ---------------------------------------------------------------------------


def test_resume_publishes_event() -> None:
    queue = FakeDownloadQueue()
    bus = FakeEventBus()
    uc = ResumeDownload(queue=queue, event_bus=bus)

    uc.execute("task-xyz")

    events = bus.events_of(DownloadResumed)
    assert len(events) == 1
    assert events[0].task_id == "task-xyz"


def test_resume_clears_paused_state() -> None:
    queue = FakeDownloadQueue()
    bus = FakeEventBus()
    queue.pause("task-xyz")
    assert queue.is_paused("task-xyz")

    ResumeDownload(queue=queue, event_bus=bus).execute("task-xyz")

    assert not queue.is_paused("task-xyz")
