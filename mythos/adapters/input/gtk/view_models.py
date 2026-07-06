# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
View-models (presenters) — translate domain entities to UI-friendly state.

View-models are plain dataclasses with no GTK dependency, so they can
be tested without a display.  GTK widgets read from view-models instead
of touching domain entities directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from mythos.domain.entities import DownloadTask, Game
from mythos.domain.value_objects import GameStatus


@dataclass
class GameViewModel:
    """Presentation state for a single game card / page."""
    app_name: str
    title: str
    developer: str
    cover_path: Optional[Path]
    cover_url: str
    status: GameStatus
    is_installed: bool
    install_path: str
    version: str
    install_size_human: str
    needs_update: bool
    supports_cloud_saves: bool
    is_dlc: bool
    can_launch: bool
    can_install: bool

    @staticmethod
    def from_game(game: Game) -> "GameViewModel":
        info = game.installed_info
        return GameViewModel(
            app_name=str(game.app_name),
            title=game.title,
            developer=game.developer,
            cover_path=game.cover_local_path,
            cover_url=game.cover_url,
            status=game.status,
            is_installed=game.is_installed,
            install_path=str(info.install_path) if info else "",
            version=info.version if info else "",
            install_size_human=info.install_size.human_readable() if info else "",
            needs_update=game.needs_update,
            supports_cloud_saves=game.supports_cloud_saves,
            is_dlc=game.is_dlc,
            can_launch=game.can_launch,
            can_install=game.can_install,
        )

    @property
    def status_label(self) -> str:
        labels = {
            GameStatus.NOT_INSTALLED: "Not Installed",
            GameStatus.INSTALLED: "Installed",
            GameStatus.INSTALLING: "Installing…",
            GameStatus.UPDATING: "Updating…",
            GameStatus.REPAIRING: "Repairing…",
            GameStatus.UNINSTALLING: "Uninstalling…",
            GameStatus.QUEUED: "Queued",
            GameStatus.RUNNING: "Running",
            GameStatus.ERROR: "Error",
        }
        return labels.get(self.status, str(self.status))


@dataclass
class DownloadTaskViewModel:
    """Presentation state for a row in the download queue view."""
    task_id: str
    app_name: str
    title: str
    kind: str
    percent: int
    speed_human: str
    status: GameStatus
    error_message: str

    @staticmethod
    def from_task(task: DownloadTask) -> "DownloadTaskViewModel":
        return DownloadTaskViewModel(
            task_id=task.id,
            app_name=str(task.app_name),
            title=task.title,
            kind=task.kind,
            percent=task.progress.percent,
            speed_human=task.progress.speed_human(),
            status=task.status,
            error_message=task.error_message,
        )


@dataclass
class LibraryViewModel:
    """Aggregated state for the library view."""
    games: list[GameViewModel] = field(default_factory=list)
    is_loading: bool = False
    search_query: str = ""
    filter_installed_only: bool = False

    @property
    def visible_games(self) -> list[GameViewModel]:
        games = self.games
        if self.filter_installed_only:
            games = [g for g in games if g.is_installed]
        if self.search_query:
            q = self.search_query.lower()
            games = [g for g in games if q in g.title.lower() or q in g.developer.lower()]
        return games
