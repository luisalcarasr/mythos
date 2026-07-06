# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""InstalledLibraryRepository implemented via LegendaryCore."""

from __future__ import annotations

import logging
from typing import Optional

from mythos.adapters.output.legendary.core_gateway import LegendaryCoreGateway
from mythos.adapters.output.legendary.mappers import legendary_installed_to_domain
from mythos.domain.entities import InstalledInfo
from mythos.domain.value_objects import AppName
from mythos.ports.output import InstalledLibraryRepository

logger = logging.getLogger(__name__)


class LegendaryInstalledRepo(InstalledLibraryRepository):
    """
    Reads installed game data from legendary's local metadata files.

    legendary manages its own ``installed.json`` (or equivalent); we
    delegate reading to ``LegendaryCore.get_installed_list()``.
    Write operations (save / remove) are handled indirectly through
    install/uninstall operations on the store adapter.
    """

    def __init__(self, gateway: LegendaryCoreGateway) -> None:
        self._gw = gateway

    def get_all(self) -> list[InstalledInfo]:
        try:
            lg_list = self._gw.get_installed_list()
            return [legendary_installed_to_domain(g) for g in lg_list]
        except Exception as exc:
            logger.error("Failed to read installed game list: %s", exc)
            return []

    def get(self, app_name: AppName) -> Optional[InstalledInfo]:
        try:
            lg = self._gw.get_installed_game(str(app_name))
            if lg is None:
                return None
            return legendary_installed_to_domain(lg)
        except Exception as exc:
            logger.error("Failed to get installed game %s: %s", app_name, exc)
            return None

    def save(self, info: InstalledInfo) -> None:
        # legendary persists install metadata automatically during
        # install/update operations; no direct write needed here.
        logger.debug("InstalledRepo.save() called for %s (no-op)", info.app_name)

    def remove(self, app_name: AppName) -> None:
        # Removal is handled by legendary during uninstall.
        logger.debug("InstalledRepo.remove() called for %s (no-op)", app_name)
