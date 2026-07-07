# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Install / update / repair / move / uninstall use cases."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from mythos.domain.entities import InstalledInfo
from mythos.domain.events import (
    DownloadCompleted,
    DownloadFailed,
    DownloadProgressed,
    DownloadStarted,
    GameInstalled,
    GameUninstalled,
)
from mythos.domain.value_objects import AppName, Platform, Progress
from mythos.ports.input import (
    InstallGameUseCase,
    MoveGameUseCase,
    RepairGameUseCase,
    UninstallGameUseCase,
    UpdateGameUseCase,
)
from mythos.ports.output import EpicStorePort, EventBus, SettingsRepository
from mythos.domain.services import InstallPlanningService

logger = logging.getLogger(__name__)


class InstallGame(InstallGameUseCase):
    def __init__(
        self,
        epic_store: EpicStorePort,
        settings_repo: SettingsRepository,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self._store = epic_store
        self._settings = settings_repo
        self._bus = event_bus
        self._planner = InstallPlanningService()

    def execute(
        self,
        app_name: AppName,
        install_path: Optional[Path] = None,
        platform: Optional[Platform] = None,
    ) -> InstalledInfo:
        settings = self._settings.load()
        resolved_path = self._planner.resolve_install_path(install_path, settings)
        resolved_platform = platform or Platform.WINDOWS

        logger.info(
            "Installing %s to %s (platform=%s) — will run via Proton on Linux",
            app_name,
            resolved_path,
            resolved_platform,
        )

        if self._bus:
            import uuid
            task_id = str(uuid.uuid4())
            self._bus.publish(DownloadStarted(task_id=task_id, app_name=str(app_name)))

        def on_progress(p: Progress) -> None:
            if self._bus:
                self._bus.publish(
                    DownloadProgressed(
                        task_id=task_id if self._bus else "",
                        app_name=str(app_name),
                        progress=p,
                    )
                )

        try:
            info = self._store.install_game(
                app_name=app_name,
                install_path=resolved_path,
                platform=resolved_platform,
                on_progress=on_progress,
            )
        except Exception as exc:
            if self._bus:
                self._bus.publish(
                    DownloadFailed(
                        task_id=task_id if self._bus else "",
                        app_name=str(app_name),
                        reason=str(exc),
                    )
                )
            raise

        if self._bus:
            self._bus.publish(
                DownloadCompleted(
                    task_id=task_id if self._bus else "",
                    app_name=str(app_name),
                )
            )
            self._bus.publish(GameInstalled(app_name=str(app_name), title=""))

        return info


class UpdateGame(UpdateGameUseCase):
    def __init__(self, epic_store: EpicStorePort, event_bus: Optional[EventBus] = None) -> None:
        self._store = epic_store
        self._bus = event_bus

    def execute(self, app_name: AppName) -> InstalledInfo:
        logger.info("Updating %s…", app_name)

        def on_progress(p: Progress) -> None:
            if self._bus:
                self._bus.publish(
                    DownloadProgressed(task_id="", app_name=str(app_name), progress=p)
                )

        info = self._store.update_game(app_name=app_name, on_progress=on_progress)
        logger.info("Update complete for %s", app_name)
        return info


class RepairGame(RepairGameUseCase):
    def __init__(self, epic_store: EpicStorePort, event_bus: Optional[EventBus] = None) -> None:
        self._store = epic_store
        self._bus = event_bus

    def execute(self, app_name: AppName) -> InstalledInfo:
        logger.info("Repairing %s…", app_name)

        def on_progress(p: Progress) -> None:
            if self._bus:
                self._bus.publish(
                    DownloadProgressed(task_id="", app_name=str(app_name), progress=p)
                )

        return self._store.repair_game(app_name=app_name, on_progress=on_progress)


class MoveGame(MoveGameUseCase):
    def __init__(self, epic_store: EpicStorePort, event_bus: Optional[EventBus] = None) -> None:
        self._store = epic_store
        self._bus = event_bus

    def execute(self, app_name: AppName, new_path: Path) -> InstalledInfo:
        logger.info("Moving %s to %s…", app_name, new_path)
        return self._store.move_game(app_name=app_name, new_path=new_path)


class UninstallGame(UninstallGameUseCase):
    def __init__(self, epic_store: EpicStorePort, event_bus: Optional[EventBus] = None) -> None:
        self._store = epic_store
        self._bus = event_bus

    def execute(self, app_name: AppName) -> None:
        logger.info("Uninstalling %s…", app_name)
        self._store.uninstall_game(app_name=app_name)
        if self._bus:
            self._bus.publish(GameUninstalled(app_name=str(app_name), title=""))
        logger.info("Uninstalled %s.", app_name)
