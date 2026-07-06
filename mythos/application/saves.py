# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Cloud save synchronisation use case."""

from __future__ import annotations

import logging
from typing import Optional

from mythos.domain.events import SavesSyncCompleted, SavesSyncFailed, SavesSyncStarted
from mythos.domain.value_objects import AppName, SyncDirection
from mythos.ports.input import SyncSavesUseCase
from mythos.ports.output import CloudSavePort, EventBus, InstalledLibraryRepository
from mythos.domain.exceptions import GameNotInstalledError, CloudSaveError

logger = logging.getLogger(__name__)


class SyncSaves(SyncSavesUseCase):
    def __init__(
        self,
        cloud_save_port: CloudSavePort,
        installed_repo: InstalledLibraryRepository,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self._saves = cloud_save_port
        self._installed = installed_repo
        self._bus = event_bus

    def execute(
        self,
        app_name: AppName,
        direction: SyncDirection = SyncDirection.BOTH,
    ) -> None:
        info = self._installed.get(app_name)
        if info is None:
            raise GameNotInstalledError(str(app_name))

        if not self._saves.supports(app_name):
            logger.info("%s does not support cloud saves; skipping.", app_name)
            return

        logger.info("Syncing cloud saves for %s (%s)…", app_name, direction)

        if self._bus:
            self._bus.publish(SavesSyncStarted(app_name=str(app_name)))

        def on_progress(msg: str) -> None:
            logger.debug("Cloud save: %s", msg)

        try:
            self._saves.sync(app_name=app_name, direction=direction, on_progress=on_progress)
        except CloudSaveError as exc:
            if self._bus:
                self._bus.publish(
                    SavesSyncFailed(app_name=str(app_name), reason=str(exc))
                )
            raise

        if self._bus:
            self._bus.publish(SavesSyncCompleted(app_name=str(app_name)))

        logger.info("Cloud save sync complete for %s.", app_name)
