from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Optional

from mythos.adapters.output.umu.database import UmuDatabase
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
        umu_database: Optional[UmuDatabase] = None,
    ) -> None:
        self._store = epic_store
        self._settings = settings_repo
        self._bus = event_bus
        self._umu_db = umu_database
        self._planner = InstallPlanningService()

    def execute(
        self,
        app_name: AppName,
        install_path: Optional[Path] = None,
        platform: Optional[Platform] = None,
        title: str = "",
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

        # Determine total download size upfront for accurate progress display
        total_bytes = 0
        try:
            download_size = self._store.get_download_size(app_name, resolved_platform)
            total_bytes = download_size.bytes_
        except Exception:
            logger.warning("Could not determine download size for %s", app_name)

        task_id = str(uuid.uuid4())

        if self._bus:
            self._bus.publish(
                DownloadStarted(
                    task_id=task_id,
                    app_name=str(app_name),
                    title=title or str(app_name),
                    total_bytes=total_bytes,
                    kind="install",
                )
            )

        def on_progress(p: Progress) -> None:
            if not self._bus:
                return
            # Use pre-fetched total_bytes; fall back to estimation from fraction
            actual_total = total_bytes
            if actual_total == 0 and p.fraction > 0 and p.downloaded_bytes > 0:
                actual_total = int(p.downloaded_bytes / p.fraction)
            self._bus.publish(
                DownloadProgressed(
                    task_id=task_id,
                    app_name=str(app_name),
                    progress=Progress(
                        fraction=p.fraction,
                        downloaded_bytes=p.downloaded_bytes,
                        total_bytes=actual_total,
                        speed_bps=p.speed_bps,
                        eta_seconds=p.eta_seconds,
                    ),
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
                        task_id=task_id,
                        app_name=str(app_name),
                        reason=str(exc),
                    )
                )
            raise

        if self._bus:
            self._bus.publish(
                DownloadCompleted(
                    task_id=task_id,
                    app_name=str(app_name),
                )
            )
            self._bus.publish(GameInstalled(app_name=str(app_name), title=""))

        if self._umu_db:
            self._umu_db.refresh()

        return info


class UpdateGame(UpdateGameUseCase):
    def __init__(
        self,
        epic_store: EpicStorePort,
        event_bus: Optional[EventBus] = None,
        umu_database: Optional[UmuDatabase] = None,
    ) -> None:
        self._store = epic_store
        self._bus = event_bus
        self._umu_db = umu_database

    def execute(self, app_name: AppName, title: str = "") -> InstalledInfo:
        logger.info("Updating %s…", app_name)

        task_id = str(uuid.uuid4())

        if self._bus:
            self._bus.publish(
                DownloadStarted(
                    task_id=task_id,
                    app_name=str(app_name),
                    title=title or str(app_name),
                    kind="update",
                )
            )

        def on_progress(p: Progress) -> None:
            if not self._bus:
                return
            actual_total = 0
            if p.fraction > 0 and p.downloaded_bytes > 0:
                actual_total = int(p.downloaded_bytes / p.fraction)
            self._bus.publish(
                DownloadProgressed(
                    task_id=task_id,
                    app_name=str(app_name),
                    progress=Progress(
                        fraction=p.fraction,
                        downloaded_bytes=p.downloaded_bytes,
                        total_bytes=actual_total,
                        speed_bps=p.speed_bps,
                        eta_seconds=p.eta_seconds,
                    ),
                )
            )

        info = self._store.update_game(app_name=app_name, on_progress=on_progress)

        if self._bus:
            self._bus.publish(
                DownloadCompleted(task_id=task_id, app_name=str(app_name))
            )

        if self._umu_db:
            self._umu_db.refresh()

        logger.info("Update complete for %s", app_name)
        return info


class RepairGame(RepairGameUseCase):
    def __init__(
        self,
        epic_store: EpicStorePort,
        event_bus: Optional[EventBus] = None,
        umu_database: Optional[UmuDatabase] = None,
    ) -> None:
        self._store = epic_store
        self._bus = event_bus
        self._umu_db = umu_database

    def execute(self, app_name: AppName, title: str = "") -> InstalledInfo:
        logger.info("Repairing %s…", app_name)

        task_id = str(uuid.uuid4())

        if self._bus:
            self._bus.publish(
                DownloadStarted(
                    task_id=task_id,
                    app_name=str(app_name),
                    title=title or str(app_name),
                    kind="repair",
                )
            )

        def on_progress(p: Progress) -> None:
            if not self._bus:
                return
            actual_total = 0
            if p.fraction > 0 and p.downloaded_bytes > 0:
                actual_total = int(p.downloaded_bytes / p.fraction)
            self._bus.publish(
                DownloadProgressed(
                    task_id=task_id,
                    app_name=str(app_name),
                    progress=Progress(
                        fraction=p.fraction,
                        downloaded_bytes=p.downloaded_bytes,
                        total_bytes=actual_total,
                        speed_bps=p.speed_bps,
                        eta_seconds=p.eta_seconds,
                    ),
                )
            )

        info = self._store.repair_game(app_name=app_name, on_progress=on_progress)

        if self._bus:
            self._bus.publish(
                DownloadCompleted(task_id=task_id, app_name=str(app_name))
            )

        if self._umu_db:
            self._umu_db.refresh()

        return info


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
