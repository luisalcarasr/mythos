# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Input ports (driving / primary adapters).

These are the use-case interfaces that the UI (GTK adapter) and any
other driving adapter (CLI, tests) depend on.  Concrete implementations
live in ``mythos/application/``.

Rules:
- Only import from ``mythos.domain``.
- Define one interface per logical use case group.
- Keep parameter and return types in the domain vocabulary.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional  # noqa: F401 (used in runner use cases)

from mythos.domain.entities import AppSettings, DownloadTask, Game, InstalledInfo
from mythos.domain.value_objects import AppName, LaunchOptions, Platform, ProtonRelease, SyncDirection, WineRunnerType


# ------------------------------------------------------------------ #
# Authentication                                                       #
# ------------------------------------------------------------------ #


class LoginUseCase(ABC):
    @abstractmethod
    def execute(self, authorization_code: str) -> dict:
        """
        Log in with an Epic Games authorisation code.

        Returns the session dict (display_name, account_id, …).
        """


class LogoutUseCase(ABC):
    @abstractmethod
    def execute(self) -> None:
        """Invalidate the current session."""


class GetSessionUseCase(ABC):
    @abstractmethod
    def execute(self) -> Optional[dict]:
        """Return the active session dict or ``None``."""


# ------------------------------------------------------------------ #
# Library                                                              #
# ------------------------------------------------------------------ #


class ListLibraryUseCase(ABC):
    @abstractmethod
    def execute(self, include_dlc: bool = False) -> list[Game]:
        """
        Return all games merging remote library with local install state.
        """


class RefreshLibraryUseCase(ABC):
    @abstractmethod
    def execute(self) -> list[Game]:
        """
        Force-refresh the library from Epic's servers and return the
        updated list of games.

        Publishes ``LibraryRefreshStarted`` and
        ``LibraryRefreshCompleted`` events via the event bus.
        """


# ------------------------------------------------------------------ #
# Install / manage                                                     #
# ------------------------------------------------------------------ #


class InstallGameUseCase(ABC):
    @abstractmethod
    def execute(
        self,
        app_name: AppName,
        install_path: Optional[Path] = None,
        platform: Optional[Platform] = None,
    ) -> InstalledInfo:
        """
        Install *app_name*.

        The caller supplies an optional *install_path* (falls back to
        the default from settings) and *platform* (defaults to the host
        platform).

        Publishes download progress events and ``GameInstalled`` on
        completion.
        """


class UpdateGameUseCase(ABC):
    @abstractmethod
    def execute(self, app_name: AppName) -> InstalledInfo:
        """Download and apply the latest update for *app_name*."""


class RepairGameUseCase(ABC):
    @abstractmethod
    def execute(self, app_name: AppName) -> InstalledInfo:
        """Verify files and re-download any that are missing or corrupt."""


class MoveGameUseCase(ABC):
    @abstractmethod
    def execute(self, app_name: AppName, new_path: Path) -> InstalledInfo:
        """Move *app_name* installation to *new_path*."""


class UninstallGameUseCase(ABC):
    @abstractmethod
    def execute(self, app_name: AppName) -> None:
        """Remove *app_name* from disk and the installed registry."""


# ------------------------------------------------------------------ #
# Launch                                                               #
# ------------------------------------------------------------------ #


class LaunchGameUseCase(ABC):
    @abstractmethod
    def execute(
        self,
        app_name: AppName,
        launch_options: Optional[LaunchOptions] = None,
        offline: bool = False,
    ) -> int:
        """
        Launch *app_name* and return its PID.

        Publishes ``GameLaunched`` on success; ``GameStopped`` when the
        process exits.
        """


# ------------------------------------------------------------------ #
# Downloads                                                            #
# ------------------------------------------------------------------ #


class EnqueueDownloadUseCase(ABC):
    @abstractmethod
    def execute(
        self,
        app_name: AppName,
        kind: str = "install",
        install_path: Optional[Path] = None,
        platform: Optional[Platform] = None,
    ) -> DownloadTask:
        """
        Add a download task for *app_name* to the queue.

        ``kind`` is one of ``"install"``, ``"update"``, ``"repair"``.
        Publishes ``DownloadEnqueued``.
        """


class CancelDownloadUseCase(ABC):
    @abstractmethod
    def execute(self, task_id: str) -> None:
        """Abort the task identified by *task_id* and remove it from the queue."""


# ------------------------------------------------------------------ #
# Cloud saves                                                          #
# ------------------------------------------------------------------ #


class SyncSavesUseCase(ABC):
    @abstractmethod
    def execute(
        self,
        app_name: AppName,
        direction: SyncDirection = SyncDirection.BOTH,
    ) -> None:
        """
        Synchronise cloud saves for *app_name*.

        Publishes ``SavesSyncStarted``, ``SavesSyncCompleted`` (or
        ``SavesSyncFailed``).
        """


# ------------------------------------------------------------------ #
# Settings                                                             #
# ------------------------------------------------------------------ #


class GetSettingsUseCase(ABC):
    @abstractmethod
    def execute(self) -> AppSettings:
        """Return the current application settings."""


class UpdateSettingsUseCase(ABC):
    @abstractmethod
    def execute(self, settings: AppSettings) -> None:
        """Persist updated settings."""


# ------------------------------------------------------------------ #
# Runner management                                                    #
# ------------------------------------------------------------------ #


class ListProtonVersionsUseCase(ABC):
    @abstractmethod
    def execute(
        self, runner_type: Optional[WineRunnerType] = None
    ) -> list[ProtonRelease]:
        """
        Return available Proton / Proton-GE builds.

        Pass ``runner_type`` to filter to a single runner family.
        Returns installed builds first, then available-for-download.
        """


class InstallProtonUseCase(ABC):
    @abstractmethod
    def execute(self, release: ProtonRelease) -> ProtonRelease:
        """
        Download, extract, and configure *release*.

        Publishes ``RunnerInstallStarted``, ``RunnerInstallProgressed``,
        ``RunnerInstallCompleted`` (or ``RunnerInstallFailed``).
        """


class SetGameProtonUseCase(ABC):
    @abstractmethod
    def execute(
        self,
        app_name: AppName,
        runner_type: WineRunnerType,
        proton_version: str,
    ) -> None:
        """
        Persist the per-game Proton selection.

        Updates ``InstalledInfo.launch_options`` with the chosen
        ``runner_type`` and ``proton_version`` tag.
        """
