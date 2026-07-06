# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Launch game use case."""

from __future__ import annotations

import logging
from typing import Optional

from mythos.domain.events import GameLaunched
from mythos.domain.value_objects import AppName, LaunchOptions
from mythos.ports.input import LaunchGameUseCase
from mythos.ports.output import EpicStorePort, EventBus, SettingsRepository, WineRuntimePort

logger = logging.getLogger(__name__)


class LaunchGame(LaunchGameUseCase):
    """
    Launch a game through the Epic / legendary backend.

    Applies Wine / Proton configuration from settings or per-call
    ``launch_options`` override.
    """

    def __init__(
        self,
        epic_store: EpicStorePort,
        wine_runtime: Optional[WineRuntimePort] = None,
        settings_repo: Optional[SettingsRepository] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self._store = epic_store
        self._wine = wine_runtime
        self._settings = settings_repo
        self._bus = event_bus

    def execute(
        self,
        app_name: AppName,
        launch_options: Optional[LaunchOptions] = None,
        offline: bool = False,
    ) -> int:
        # Merge per-call options with defaults from settings
        effective_options = self._resolve_options(launch_options)

        logger.info(
            "Launching %s (offline=%s, wine=%s)…",
            app_name,
            offline,
            effective_options.wine_runner if effective_options else "none",
        )

        pid = self._store.launch_game(
            app_name=app_name,
            launch_options=effective_options,
            offline=offline,
        )

        if self._bus:
            self._bus.publish(GameLaunched(app_name=str(app_name), title="", pid=pid))

        logger.info("Game %s launched with PID %d", app_name, pid)
        return pid

    def _resolve_options(
        self, override: Optional[LaunchOptions]
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
