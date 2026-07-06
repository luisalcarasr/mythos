# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""CloudSavePort implemented via LegendaryCore."""

from __future__ import annotations

import logging
from typing import Callable, Optional

from mythos.adapters.output.legendary.core_gateway import LegendaryCoreGateway
from mythos.domain.exceptions import CloudSaveError
from mythos.domain.value_objects import AppName, SyncDirection
from mythos.ports.output import CloudSavePort

logger = logging.getLogger(__name__)


class LegendaryCloudSaves(CloudSavePort):
    def __init__(self, gateway: LegendaryCoreGateway) -> None:
        self._gw = gateway

    def supports(self, app_name: AppName) -> bool:
        try:
            game = self._gw.core.get_game(str(app_name))
            if game is None:
                return False
            attrs = game.metadata.get("customAttributes", {})
            return "CloudSaveFolder" in attrs
        except Exception:  # noqa: BLE001
            return False

    def sync(
        self,
        app_name: AppName,
        direction: SyncDirection,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> None:
        try:
            igame = self._gw.get_installed_game(str(app_name))
            if igame is None:
                raise CloudSaveError(f"Game {app_name} is not installed.")

            if on_progress:
                on_progress(f"Resolving save path for {app_name}…")

            save_path = self._gw.core.get_save_path(str(app_name))

            if direction in (SyncDirection.DOWNLOAD, SyncDirection.BOTH):
                if on_progress:
                    on_progress("Downloading cloud saves…")
                self._gw.core.download_saves(str(app_name), save_path)

            if direction in (SyncDirection.UPLOAD, SyncDirection.BOTH):
                if on_progress:
                    on_progress("Uploading local saves…")
                self._gw.core.upload_saves(str(app_name), save_path)

            if on_progress:
                on_progress("Cloud save sync complete.")

        except CloudSaveError:
            raise
        except Exception as exc:
            raise CloudSaveError(f"Cloud save sync failed for {app_name}: {exc}") from exc
