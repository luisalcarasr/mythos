# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""In-memory fake EpicStorePort."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Optional

from mythos.domain.entities import Game, InstalledInfo
from mythos.domain.value_objects import (
    AppName,
    DiskSize,
    GameStatus,
    InstallPath,
    LaunchOptions,
    Platform,
    Progress,
)
from mythos.ports.output import EpicStorePort


class FakeEpicStore(EpicStorePort):
    """
    Deterministic, in-memory Epic store.

    Seed it with ``games`` and ``installed`` lists.  Install / update /
    uninstall mutate the in-memory state so the UI reflects changes
    immediately.
    """

    def __init__(
        self,
        games: Optional[list[Game]] = None,
        installed: Optional[list[InstalledInfo]] = None,
        fail_install: bool = False,
        fake_pid: int = 12345,
        install_delay: float = 0.0,
    ) -> None:
        self._games: dict[AppName, Game] = {g.app_name: g for g in (games or [])}
        self._installed: dict[AppName, InstalledInfo] = {
            i.app_name: i for i in (installed or [])
        }
        self.fail_install = fail_install
        self.fake_pid = fake_pid
        self.install_delay = install_delay

        # Spy counters
        self.install_calls: list[AppName] = []
        self.update_calls: list[AppName] = []
        self.uninstall_calls: list[AppName] = []
        self.launch_calls: list[AppName] = []
        self.cancel_calls: list[AppName] = []

    # ---------------------------------------------------------------- #
    # EpicStorePort                                                      #
    # ---------------------------------------------------------------- #

    def list_games(self, include_dlc: bool = False) -> list[Game]:
        return [g for g in self._games.values() if not g.is_dlc or include_dlc]

    def get_game(self, app_name: AppName) -> Optional[Game]:
        return self._games.get(app_name)

    def install_game(
        self,
        app_name: AppName,
        install_path: Path,
        platform: Platform,
        on_progress: Callable[[Progress], None],
    ) -> InstalledInfo:
        self.install_calls.append(app_name)
        if self.fail_install:
            raise RuntimeError("Simulated install failure")

        steps = 5
        for i in range(1, steps + 1):
            if self.install_delay:
                time.sleep(self.install_delay / steps)
            on_progress(
                Progress(
                    fraction=i / steps,
                    downloaded_bytes=i * 200,
                    total_bytes=steps * 200,
                    speed_bps=10 * 1024 * 1024,
                    eta_seconds=max(0, (steps - i) * 0.5),
                )
            )

        info = InstalledInfo(
            app_name=app_name,
            install_path=InstallPath(install_path / str(app_name)),
            version="1.0.0",
            platform=platform,
            install_size=DiskSize.from_gib(2),
            executable="game.exe",
        )
        self._installed[app_name] = info
        if app_name in self._games:
            self._games[app_name].installed_info = info
            self._games[app_name].status = GameStatus.INSTALLED
        return info

    def update_game(
        self,
        app_name: AppName,
        on_progress: Callable[[Progress], None],
    ) -> InstalledInfo:
        self.update_calls.append(app_name)
        on_progress(Progress(fraction=1.0))
        info = self._installed[app_name]
        # Clear the update flag
        from dataclasses import replace
        updated = replace(info, update_available=False)
        self._installed[app_name] = updated
        if app_name in self._games:
            self._games[app_name].installed_info = updated
        return updated

    def repair_game(
        self,
        app_name: AppName,
        on_progress: Callable[[Progress], None],
    ) -> InstalledInfo:
        on_progress(Progress(fraction=1.0))
        return self._installed[app_name]

    def move_game(self, app_name: AppName, new_path: Path) -> InstalledInfo:
        from dataclasses import replace
        info = self._installed[app_name]
        updated = replace(info, install_path=InstallPath(new_path))
        self._installed[app_name] = updated
        return updated

    def uninstall_game(self, app_name: AppName) -> None:
        self.uninstall_calls.append(app_name)
        self._installed.pop(app_name, None)
        if app_name in self._games:
            self._games[app_name].installed_info = None
            self._games[app_name].status = GameStatus.NOT_INSTALLED

    def cancel_download(self, app_name: AppName) -> None:
        self.cancel_calls.append(app_name)

    def get_installed(self) -> list[InstalledInfo]:
        return list(self._installed.values())

    def get_download_size(self, app_name: AppName, platform: Platform) -> DiskSize:
        return DiskSize.from_mib(800)

    def get_install_size(self, app_name: AppName, platform: Platform) -> DiskSize:
        return DiskSize.from_gib(3)

    def launch_game(
        self,
        app_name: AppName,
        launch_options: Optional[LaunchOptions] = None,
        offline: bool = False,
    ) -> int:
        self.launch_calls.append(app_name)
        return self.fake_pid
