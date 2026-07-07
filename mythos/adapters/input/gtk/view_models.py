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
from datetime import datetime
from pathlib import Path
from typing import Optional

from mythos.domain.entities import DownloadTask, Game
from mythos.domain.value_objects import GameStatus, ProtonRelease, WineRunnerType


@dataclass
class GameViewModel:
    """Presentation state for a single game card / page."""
    app_name: str
    title: str
    developer: str
    publisher: str
    description: str
    long_description: str
    cover_path: Optional[Path]
    cover_url: str
    cover_wide_path: Optional[Path]
    cover_url_wide: str
    status: GameStatus
    is_installed: bool
    install_path: str
    version: str
    install_size_human: str
    platform: str
    executable: str
    needs_update: bool
    supports_cloud_saves: bool
    is_dlc: bool
    can_launch: bool
    can_install: bool
    categories: list[str]
    release_date: Optional[datetime]
    release_date_human: str
    can_run_offline: bool
    launch_parameters: str
    save_path: str
    wine_runner: WineRunnerType = WineRunnerType.NONE
    proton_version: str = ""

    @staticmethod
    def from_game(game: Game) -> "GameViewModel":
        info = game.installed_info

        # Format release date
        release_date_human = ""
        if game.release_date:
            try:
                release_date_human = game.release_date.strftime("%B %d, %Y")
            except Exception:
                pass

        return GameViewModel(
            app_name=str(game.app_name),
            title=game.title,
            developer=game.developer,
            publisher=game.publisher,
            description=game.description,
            long_description=game.long_description,
            cover_path=game.cover_local_path,
            cover_url=game.cover_url,
            cover_wide_path=game.cover_local_wide_path,
            cover_url_wide=game.cover_url_wide,
            status=game.status,
            is_installed=game.is_installed,
            install_path=str(info.install_path) if info else "",
            version=info.version if info else "",
            install_size_human=info.install_size.human_readable() if info else "",
            platform=str(info.platform.value) if info else "",
            executable=info.executable if info else "",
            needs_update=game.needs_update,
            supports_cloud_saves=game.supports_cloud_saves,
            is_dlc=game.is_dlc,
            can_launch=game.can_launch,
            can_install=game.can_install,
            categories=game.categories,
            release_date=game.release_date,
            release_date_human=release_date_human,
            can_run_offline=info.can_run_offline if info else False,
            launch_parameters=info.launch_parameters if info else "",
            save_path=info.save_path if info else "",
            wine_runner=info.launch_options.wine_runner if info else WineRunnerType.NONE,
            proton_version=info.launch_options.proton_version if info else "",
        )

    @property
    def status_label(self) -> str:
        labels = {
            GameStatus.NOT_INSTALLED: "Not Installed",
            GameStatus.INSTALLED: "Installed",
            GameStatus.INSTALLING: "Installing\u2026",
            GameStatus.UPDATING: "Updating\u2026",
            GameStatus.REPAIRING: "Repairing\u2026",
            GameStatus.UNINSTALLING: "Uninstalling\u2026",
            GameStatus.QUEUED: "Queued",
            GameStatus.RUNNING: "Running",
            GameStatus.ERROR: "Error",
        }
        return labels.get(self.status, str(self.status))


@dataclass
class DownloadTaskViewModel:
    """Presentation state for a single download card."""
    task_id: str
    app_name: str
    title: str
    kind: str                        # "install" | "update" | "repair" | "runner"
    percent: int
    fraction: float
    speed_human: str
    downloaded_human: str
    total_human: str
    eta_human: str
    status: GameStatus
    error_message: str
    is_paused: bool = False
    is_runner: bool = False
    thumbnail_path: Optional[Path] = None

    @staticmethod
    def from_task(task: DownloadTask) -> "DownloadTaskViewModel":
        p = task.progress
        return DownloadTaskViewModel(
            task_id=task.id,
            app_name=str(task.app_name),
            title=task.title or str(task.app_name),
            kind=task.kind,
            percent=p.percent,
            fraction=p.fraction,
            speed_human=p.speed_human(),
            downloaded_human=p.downloaded_human,
            total_human=p.total_human,
            eta_human=p.eta_human,
            status=task.status,
            error_message=task.error_message,
        )

    def stats_line(self) -> str:
        """Single-line stats: 'X GB / Y GB · Z MB/s · 3m left'."""
        if self.error_message:
            return self.error_message[:80]
        if self.fraction >= 1.0:
            return f"{self.total_human} — Complete"
        parts = [f"{self.downloaded_human} / {self.total_human}"]
        if self.speed_human and self.speed_human != "0.0 B/s":
            parts.append(self.speed_human)
        if self.eta_human and self.eta_human != "—":
            parts.append(self.eta_human)
        return "  ·  ".join(parts)


@dataclass
class ProtonReleaseViewModel:
    """Presentation state for a single Proton / Proton-GE build."""
    name: str
    version: str
    runner_type: WineRunnerType
    label: str          # e.g. "Proton-GE — GE-Proton9-20"
    installed: bool
    download_url: str
    size_human: str     # e.g. "366.0 MiB"

    @staticmethod
    def from_release(release: ProtonRelease) -> "ProtonReleaseViewModel":
        from mythos.domain.value_objects import DiskSize
        size_human = (
            DiskSize(release.size_bytes).human_readable()
            if release.size_bytes
            else "Unknown size"
        )
        return ProtonReleaseViewModel(
            name=release.name,
            version=release.version,
            runner_type=release.runner_type,
            label=release.label,
            installed=release.installed,
            download_url=release.download_url,
            size_human=size_human,
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
        games.sort(key=lambda g: (0 if g.is_installed else 1, g.title.lower()))
        return games
