# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Domain events — facts that happened in the domain.

Events are immutable data bags that entities emit.  Adapters subscribe
to them via the ``EventBus`` port (ports/output.py) to react in the UI
or trigger side-effects without coupling the domain to infrastructure.

All events are frozen dataclasses so they are safe to pass across
thread boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mythos.domain.value_objects import Progress


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events."""
    occurred_at: datetime = field(default_factory=datetime.now, compare=False)


# ------------------------------------------------------------------ #
# Authentication events                                                #
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class UserLoggedIn(DomainEvent):
    display_name: str = ""
    account_id: str = ""


@dataclass(frozen=True)
class UserLoggedOut(DomainEvent):
    pass


# ------------------------------------------------------------------ #
# Library events                                                       #
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class LibraryRefreshStarted(DomainEvent):
    pass


@dataclass(frozen=True)
class LibraryRefreshCompleted(DomainEvent):
    total_games: int = 0


# ------------------------------------------------------------------ #
# Game lifecycle events                                                #
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class GameInstalled(DomainEvent):
    app_name: str = ""
    title: str = ""


@dataclass(frozen=True)
class GameUninstalled(DomainEvent):
    app_name: str = ""
    title: str = ""


@dataclass(frozen=True)
class GameLaunched(DomainEvent):
    app_name: str = ""
    title: str = ""
    pid: int = 0


@dataclass(frozen=True)
class GameStopped(DomainEvent):
    app_name: str = ""
    title: str = ""


# ------------------------------------------------------------------ #
# Download events                                                      #
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class DownloadEnqueued(DomainEvent):
    task_id: str = ""
    app_name: str = ""
    kind: str = "install"   # "install" | "update" | "repair"
    title: str = ""
    total_bytes: int = 0


@dataclass(frozen=True)
class DownloadStarted(DomainEvent):
    task_id: str = ""
    app_name: str = ""
    title: str = ""
    total_bytes: int = 0
    kind: str = "install"


@dataclass(frozen=True)
class DownloadProgressed(DomainEvent):
    task_id: str = ""
    app_name: str = ""
    progress: "Progress | None" = None


@dataclass(frozen=True)
class DownloadCompleted(DomainEvent):
    task_id: str = ""
    app_name: str = ""


@dataclass(frozen=True)
class DownloadFailed(DomainEvent):
    task_id: str = ""
    app_name: str = ""
    reason: str = ""


# ------------------------------------------------------------------ #
# Cloud save events                                                    #
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class SavesSyncStarted(DomainEvent):
    app_name: str = ""


@dataclass(frozen=True)
class SavesSyncCompleted(DomainEvent):
    app_name: str = ""


@dataclass(frozen=True)
class SavesSyncFailed(DomainEvent):
    app_name: str = ""
    reason: str = ""
