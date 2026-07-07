# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Domain entities — the heart of the domain model.

Rules:
- No external dependencies (no gi, no legendary, no requests).
- Entities carry identity (``app_name``).
- Business rules live here, not in use cases.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from mythos.domain.value_objects import (
    AppName,
    DiskSize,
    GameStatus,
    InstallPath,
    LaunchOptions,
    Platform,
    Progress,
    WineRunnerType,
)
from mythos.domain.events import (
    DomainEvent,
    GameInstalled,
    GameUninstalled,
    GameLaunched,
    GameStopped,
)
from mythos.domain.exceptions import (
    GameAlreadyInstalledError,
    GameAlreadyRunningError,
    GameNotInstalledError,
)


# ------------------------------------------------------------------ #
# Game                                                                 #
# ------------------------------------------------------------------ #


@dataclass
class Game:
    """
    A game available in the user's Epic Games library.

    This entity represents both installed and not-installed games.
    The ``status`` value object tracks lifecycle state and the
    ``installed_info`` field is only set when the game is on disk.
    """

    # Identity
    app_name: AppName
    title: str

    # Metadata
    developer: str = ""
    publisher: str = ""
    description: str = ""
    cover_url: str = ""
    cover_local_path: Optional[Path] = None
    cover_url_wide: str = ""
    cover_local_wide_path: Optional[Path] = None
    genres: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    is_dlc: bool = False
    supports_cloud_saves: bool = False
    last_played: Optional[datetime] = None
    long_description: str = ""
    categories: list[str] = field(default_factory=list)
    release_date: Optional[datetime] = None

    # Installation info (None when not installed)
    installed_info: Optional[InstalledInfo] = None

    # Runtime state (not persisted)
    status: GameStatus = GameStatus.NOT_INSTALLED
    _pending_events: list[DomainEvent] = field(
        default_factory=list, repr=False, compare=False
    )

    # ---------------------------------------------------------------- #
    # Business rules                                                     #
    # ---------------------------------------------------------------- #

    @property
    def is_installed(self) -> bool:
        return self.installed_info is not None

    @property
    def is_running(self) -> bool:
        return self.status == GameStatus.RUNNING

    @property
    def can_launch(self) -> bool:
        return self.is_installed and self.status not in (
            GameStatus.RUNNING,
            GameStatus.INSTALLING,
            GameStatus.UPDATING,
            GameStatus.REPAIRING,
            GameStatus.UNINSTALLING,
        )

    @property
    def can_install(self) -> bool:
        return not self.is_installed and self.status not in (
            GameStatus.INSTALLING,
            GameStatus.QUEUED,
        )

    @property
    def needs_update(self) -> bool:
        if self.installed_info is None:
            return False
        return self.installed_info.update_available

    def mark_installing(self) -> None:
        if not self.can_install:
            raise GameAlreadyInstalledError(str(self.app_name))
        self.status = GameStatus.INSTALLING

    def mark_installed(self, info: InstalledInfo) -> None:
        self.installed_info = info
        self.status = GameStatus.INSTALLED
        self._pending_events.append(
            GameInstalled(app_name=str(self.app_name), title=self.title)
        )

    def mark_uninstalled(self) -> None:
        if not self.is_installed:
            raise GameNotInstalledError(str(self.app_name))
        self.installed_info = None
        self.status = GameStatus.NOT_INSTALLED
        self._pending_events.append(
            GameUninstalled(app_name=str(self.app_name), title=self.title)
        )

    def mark_launched(self, pid: int) -> None:
        if self.is_running:
            raise GameAlreadyRunningError(str(self.app_name))
        self.status = GameStatus.RUNNING
        if self.installed_info:
            self.installed_info = InstalledInfo(
                **{
                    **self.installed_info.__dict__,
                    "pid": pid,
                }
            )
        self.last_played = datetime.now()
        self._pending_events.append(
            GameLaunched(app_name=str(self.app_name), title=self.title, pid=pid)
        )

    def mark_stopped(self) -> None:
        self.status = GameStatus.INSTALLED
        if self.installed_info:
            self.installed_info = InstalledInfo(
                **{**self.installed_info.__dict__, "pid": None}
            )
        self._pending_events.append(
            GameStopped(app_name=str(self.app_name), title=self.title)
        )

    def collect_events(self) -> list[DomainEvent]:
        """Return and clear pending domain events."""
        events = list(self._pending_events)
        self._pending_events.clear()
        return events


# ------------------------------------------------------------------ #
# InstalledInfo                                                        #
# ------------------------------------------------------------------ #


@dataclass
class InstalledInfo:
    """
    Additional metadata that only exists when a game is installed locally.

    This is a value-object-like struct embedded in ``Game``.
    """
    app_name: AppName
    install_path: InstallPath
    version: str
    platform: Platform
    install_size: DiskSize
    executable: str = ""
    launch_options: LaunchOptions = field(default_factory=LaunchOptions)
    update_available: bool = False
    pid: Optional[int] = None  # set while game is running
    can_run_offline: bool = False
    launch_parameters: str = ""
    save_path: str = ""

    @property
    def is_running(self) -> bool:
        return self.pid is not None


# ------------------------------------------------------------------ #
# AppSettings                                                          #
# ------------------------------------------------------------------ #


@dataclass
class AppSettings:
    """
    User-level settings for the Mythos application.

    Stored as a JSON document via ``SettingsRepository``.
    """
    language: str = "en"
    theme: str = "system"   # "light" | "dark" | "system"
    default_install_path: Optional[Path] = None
    default_wine_runner: WineRunnerType = WineRunnerType.NONE
    default_wine_executable: Optional[Path] = None
    enable_discord_rpc: bool = False
    check_updates_on_startup: bool = True
    minimize_to_tray: bool = True
    show_dlc_in_library: bool = False
    concurrent_downloads: int = 1

    def __post_init__(self) -> None:
        if self.concurrent_downloads < 1:
            raise ValueError("concurrent_downloads must be at least 1.")
        if self.concurrent_downloads > 5:
            raise ValueError("concurrent_downloads cannot exceed 5.")
