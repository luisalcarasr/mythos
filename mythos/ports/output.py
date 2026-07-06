# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Output ports (driven / secondary adapters).

These are the contracts that the application layer requires from
infrastructure.  Concrete implementations live in
``mythos/adapters/output/``.

Rules:
- Only import from ``mythos.domain``.
- Use ``abc.ABC`` + ``@abstractmethod`` for explicit contracts.
- Keep method signatures minimal and domain-centric.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Optional

from mythos.domain.entities import AppSettings, DownloadTask, Game, InstalledInfo
from mythos.domain.events import DomainEvent
from mythos.domain.value_objects import (
    AppName,
    DiskSize,
    LaunchOptions,
    Platform,
    Progress,
    SyncDirection,
    WineRunnerType,
)


# ------------------------------------------------------------------ #
# Epic Store port                                                      #
# ------------------------------------------------------------------ #


class EpicStorePort(ABC):
    """
    Contract for all interactions with the Epic Games Store backend
    (authentication aside — see ``AuthSessionRepository``).
    """

    @abstractmethod
    def list_games(self, include_dlc: bool = False) -> list[Game]:
        """
        Return every game in the authenticated user's library.

        Parameters
        ----------
        include_dlc:
            When *True*, DLC items are included in the result.
        """

    @abstractmethod
    def get_game(self, app_name: AppName) -> Optional[Game]:
        """Return a single ``Game`` by *app_name*, or ``None``."""

    @abstractmethod
    def install_game(
        self,
        app_name: AppName,
        install_path: Path,
        platform: Platform,
        on_progress: Callable[[Progress], None],
    ) -> InstalledInfo:
        """
        Install *app_name* to *install_path*.

        Calls *on_progress* periodically with the current ``Progress``.
        Returns the ``InstalledInfo`` on success; raises ``InstallError``
        on failure.
        """

    @abstractmethod
    def update_game(
        self,
        app_name: AppName,
        on_progress: Callable[[Progress], None],
    ) -> InstalledInfo:
        """Download and apply available updates for *app_name*."""

    @abstractmethod
    def repair_game(
        self,
        app_name: AppName,
        on_progress: Callable[[Progress], None],
    ) -> InstalledInfo:
        """Verify and re-download any corrupted files."""

    @abstractmethod
    def move_game(self, app_name: AppName, new_path: Path) -> InstalledInfo:
        """Move an installed game to a new location on disk."""

    @abstractmethod
    def uninstall_game(self, app_name: AppName) -> None:
        """Remove an installed game from disk."""

    @abstractmethod
    def cancel_download(self, app_name: AppName) -> None:
        """Abort an in-progress install or update."""

    @abstractmethod
    def get_installed(self) -> list[InstalledInfo]:
        """Return metadata for every locally installed game."""

    @abstractmethod
    def get_download_size(self, app_name: AppName, platform: Platform) -> DiskSize:
        """Return the estimated download size for *app_name*."""

    @abstractmethod
    def get_install_size(self, app_name: AppName, platform: Platform) -> DiskSize:
        """Return the estimated installed size for *app_name*."""

    @abstractmethod
    def launch_game(
        self,
        app_name: AppName,
        launch_options: Optional[LaunchOptions] = None,
        offline: bool = False,
    ) -> int:
        """
        Launch *app_name* and return the process PID.

        Parameters
        ----------
        launch_options:
            Override per-game launch settings for this run.
        offline:
            Launch without Epic online services.
        """


# ------------------------------------------------------------------ #
# Auth session repository                                              #
# ------------------------------------------------------------------ #


class AuthSessionRepository(ABC):
    """Manages Epic Games OAuth session persistence."""

    @abstractmethod
    def login_with_code(self, authorization_code: str) -> dict:
        """
        Exchange an authorisation code for tokens.

        Returns a dict with at least:
          - ``display_name``
          - ``account_id``
          - ``access_token``
        """

    @abstractmethod
    def logout(self) -> None:
        """Invalidate and remove the stored session."""

    @abstractmethod
    def get_session(self) -> Optional[dict]:
        """
        Return the current session dict, or ``None`` when not logged in.

        The returned dict contains ``display_name`` and ``account_id`` at
        minimum.
        """

    @abstractmethod
    def is_logged_in(self) -> bool:
        """Return ``True`` when a valid (non-expired) session exists."""


# ------------------------------------------------------------------ #
# Installed library repository                                         #
# ------------------------------------------------------------------ #


class InstalledLibraryRepository(ABC):
    """
    Read/write access to the list of locally installed games.

    This is distinct from ``EpicStorePort`` because the installed state
    can be queried offline without communicating with Epic's servers.
    """

    @abstractmethod
    def get_all(self) -> list[InstalledInfo]:
        """Return metadata for every installed game."""

    @abstractmethod
    def get(self, app_name: AppName) -> Optional[InstalledInfo]:
        """Return ``InstalledInfo`` for *app_name*, or ``None``."""

    @abstractmethod
    def save(self, info: InstalledInfo) -> None:
        """Persist or update the installation record for a game."""

    @abstractmethod
    def remove(self, app_name: AppName) -> None:
        """Delete the installation record for *app_name*."""


# ------------------------------------------------------------------ #
# Image cache port                                                     #
# ------------------------------------------------------------------ #


class ImageCachePort(ABC):
    """Local cache for game cover images."""

    @abstractmethod
    def get(self, app_name: AppName) -> Optional[Path]:
        """
        Return the local path to the cached cover, or ``None`` when
        the image is not in the cache yet.
        """

    @abstractmethod
    def store(self, app_name: AppName, image_bytes: bytes) -> Path:
        """Save *image_bytes* to disk and return the local path."""

    @abstractmethod
    def fetch_and_cache(self, app_name: AppName, url: str) -> Path:
        """
        Download the image at *url*, cache it, and return the path.

        May raise ``requests.RequestException`` on network failure.
        """


# ------------------------------------------------------------------ #
# Wine runtime port                                                    #
# ------------------------------------------------------------------ #


class WineRuntimePort(ABC):
    """Discovers and validates Wine / Proton / CrossOver runtimes."""

    @abstractmethod
    def list_runtimes(self) -> list[dict]:
        """
        Return all detected Wine runtimes as dicts with keys:
          - ``name``  (str)
          - ``type``  (WineRunnerType)
          - ``path``  (Path)
          - ``version`` (str)
        """

    @abstractmethod
    def get_default(self) -> Optional[dict]:
        """Return the default runtime, or ``None`` when Wine is unavailable."""

    @abstractmethod
    def validate(self, executable: Path) -> bool:
        """Return ``True`` if *executable* is a valid Wine binary."""


# ------------------------------------------------------------------ #
# Cloud save port                                                      #
# ------------------------------------------------------------------ #


class CloudSavePort(ABC):
    """Sync cloud saves for Epic Games that support them."""

    @abstractmethod
    def sync(
        self,
        app_name: AppName,
        direction: SyncDirection,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> None:
        """
        Synchronise cloud saves for *app_name*.

        Parameters
        ----------
        direction:
            ``UPLOAD`` pushes local saves; ``DOWNLOAD`` pulls remote;
            ``BOTH`` performs a two-way merge.
        on_progress:
            Optional callback that receives status messages as strings.
        """

    @abstractmethod
    def supports(self, app_name: AppName) -> bool:
        """Return ``True`` if the game supports cloud saves."""


# ------------------------------------------------------------------ #
# Settings repository                                                  #
# ------------------------------------------------------------------ #


class SettingsRepository(ABC):
    """Persist and retrieve application-level settings."""

    @abstractmethod
    def load(self) -> AppSettings:
        """Load settings from persistent storage."""

    @abstractmethod
    def save(self, settings: AppSettings) -> None:
        """Write *settings* to persistent storage."""


# ------------------------------------------------------------------ #
# Download queue port                                                  #
# ------------------------------------------------------------------ #


class DownloadQueuePort(ABC):
    """Manages the ordered queue of pending installation tasks."""

    @abstractmethod
    def enqueue(self, task: DownloadTask) -> None:
        """Add *task* to the end of the queue."""

    @abstractmethod
    def cancel(self, task_id: str) -> None:
        """Remove and abort the task identified by *task_id*."""

    @abstractmethod
    def list_tasks(self) -> list[DownloadTask]:
        """Return all current tasks (queued and in-progress)."""

    @abstractmethod
    def get_active(self) -> Optional[DownloadTask]:
        """Return the currently-running task, or ``None``."""


# ------------------------------------------------------------------ #
# Event bus                                                            #
# ------------------------------------------------------------------ #


class EventBus(ABC):
    """
    Publish–subscribe bus for ``DomainEvent`` instances.

    Use cases publish; UI adapters subscribe.
    """

    @abstractmethod
    def publish(self, event: DomainEvent) -> None:
        """Publish *event* to all registered subscribers."""

    @abstractmethod
    def subscribe(
        self,
        event_type: type[DomainEvent],
        handler: Callable[[DomainEvent], None],
    ) -> None:
        """Register *handler* to be called for every *event_type* event."""

    @abstractmethod
    def unsubscribe(
        self,
        event_type: type[DomainEvent],
        handler: Callable[[DomainEvent], None],
    ) -> None:
        """Remove a previously registered *handler*."""
