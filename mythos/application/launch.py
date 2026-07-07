# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Launch game use case."""

from __future__ import annotations

import logging
from typing import Optional

from mythos.domain.events import GameLaunched
from mythos.domain.value_objects import AppName, LaunchOptions, WineRunnerType
from mythos.ports.input import LaunchGameUseCase
from mythos.ports.output import EpicStorePort, EventBus, RunnerManagerPort, SettingsRepository, WineRuntimePort

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
        runner_manager: Optional[RunnerManagerPort] = None,
        install_proton: Optional[object] = None,  # InstallProtonUseCase (avoids circular)
    ) -> None:
        self._store = epic_store
        self._wine = wine_runtime
        self._settings = settings_repo
        self._bus = event_bus
        self._runner_manager = runner_manager
        self._install_proton = install_proton

    def execute(
        self,
        app_name: AppName,
        launch_options: Optional[LaunchOptions] = None,
        offline: bool = False,
    ) -> int:
        # Merge per-call options with defaults from settings
        effective_options = self._resolve_options(launch_options)

        # Lazy runner install: if a Proton version is selected but not
        # yet installed, download it now before launching the game.
        self._ensure_runner(effective_options)

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

    def _ensure_runner(self, options: Optional[LaunchOptions]) -> None:
        """
        If the game's selected Proton version is not installed, download
        it now (progress published via RunnerInstall* events → Downloads
        view).  Raises on failure so the launch is aborted.
        """
        if not options:
            return
        if options.wine_runner not in (WineRunnerType.PROTON, WineRunnerType.PROTON_GE):
            return
        if not options.proton_version:
            return
        if not self._runner_manager or not self._install_proton:
            return

        # Find the matching release in the available catalogue
        available = self._runner_manager.list_available(options.wine_runner)
        release = next(
            (r for r in available if r.version == options.proton_version),
            None,
        )
        if release is None:
            logger.warning(
                "Runner %s %s not found in catalogue — launching without it.",
                options.wine_runner.value,
                options.proton_version,
            )
            return

        if self._runner_manager.is_installed(release):
            return  # already installed, nothing to do

        logger.info(
            "Runner %s not installed — downloading before launch…",
            release.name,
        )
        # InstallProton.execute() publishes Started/Progressed/Completed/Failed
        self._install_proton.execute(release)

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
