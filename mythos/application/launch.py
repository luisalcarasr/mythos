# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Launch game use case."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from mythos.domain.entities import Game
from mythos.domain.events import GameLaunched, GameStopped
from mythos.domain.value_objects import AppName, LaunchOptions, WineRunnerType
from mythos.ports.input import LaunchGameUseCase
from mythos.adapters.output.umu.database import UmuDatabase
from mythos.ports.output import EpicStorePort, EventBus, InstalledLibraryRepository, SettingsRepository, WineRuntimePort

logger = logging.getLogger(__name__)


class LaunchGame(LaunchGameUseCase):
    """
    Launch a game via umu-launcher (Wine/Proton container).

    Gets the game's install info, builds the ``umu-run`` command, and
    executes it through ``WineRuntimePort`` in the background via
    ``SubprocessRunner``.

    Publishes ``GameLaunched`` on start and ``GameStopped`` when the
    game process exits.
    """

    def __init__(
        self,
        wine_runtime: WineRuntimePort,
        epic_store: Optional[EpicStorePort] = None,
        installed_repo: Optional[InstalledLibraryRepository] = None,
        settings_repo: Optional[SettingsRepository] = None,
        event_bus: Optional[EventBus] = None,
        umu_database: Optional[UmuDatabase] = None,
    ) -> None:
        self._wine = wine_runtime
        self._store = epic_store
        self._installed_repo = installed_repo
        self._settings = settings_repo
        self._bus = event_bus
        self._umu_db = umu_database

    def execute(
        self,
        app_name: AppName,
        launch_options: Optional[LaunchOptions] = None,
        offline: bool = False,
    ) -> int:
        effective_options = self._resolve_options(launch_options)

        # Get install info
        installed = self._installed_repo.get(app_name) if self._installed_repo else None
        if installed is None:
            raise RuntimeError(f"Cannot launch {app_name}: not installed or no install info")

        # Build executable path
        exe = installed.install_path.value / installed.executable if installed.executable else installed.install_path.value

        # Build wineprefix (umu default: ~/Games/umu/<game-id>)
        wineprefix = Path.home() / "Games" / "umu" / str(app_name)

        # Build launch args (wrapper command is prepended to umu-run)
        launch_args: list[str] = []
        if effective_options and effective_options.wrapper_command:
            launch_args = effective_options.wrapper_command.split()

        # Extra env from config
        extra_env: dict[str, str] = {}
        if effective_options and effective_options.extra_env:
            extra_env = dict(effective_options.extra_env)

        game_title = str(app_name)
        if self._store:
            try:
                game: Game | None = self._store.get_game(app_name)
                if game:
                    game_title = game.title.value
            except Exception:
                pass

        umu_id = None
        if self._umu_db:
            umu_id = self._umu_db.lookup("egs", str(app_name))
            if not umu_id:
                umu_id = self._umu_db.fuzzy_search(game_title, store="egs")
        game_id = umu_id.umu_id if umu_id else "umu-default"

        pid = self._wine.execute_game(
            executable=exe,
            args=launch_args,
            wine_runner=effective_options.wine_runner if effective_options else WineRunnerType.NONE,
            wineprefix=wineprefix,
            env=extra_env,
            game_id=game_id,
            store="egs",
            on_exit=lambda code: self._on_game_exited(app_name, code),
        )

        logger.info(
            "Launched %s via umu (PID=%d, wine=%s, offline=%s)",
            app_name, pid,
            effective_options.wine_runner if effective_options else "none",
            offline,
        )

        if self._bus:
            self._bus.publish(GameLaunched(
                app_name=str(app_name), title=installed.app_name.value, pid=pid,
            ))

        return pid

    def _on_game_exited(self, app_name: AppName, exit_code: int) -> None:
        """Called by SubprocessRunner when the umu-run process exits."""
        logger.info("Game %s exited with code %d", app_name, exit_code)
        if self._bus:
            self._bus.publish(GameStopped(app_name=str(app_name), title=""))

    def _resolve_options(
        self, override: Optional[LaunchOptions],
    ) -> Optional[LaunchOptions]:
        if override:
            return override
        if self._settings:
            settings = self._settings.load()
            return LaunchOptions(
                wine_runner=settings.default_wine_runner,
                wine_executable=settings.default_wine_executable,
            )
        return None
