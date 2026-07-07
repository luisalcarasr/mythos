from __future__ import annotations

import logging
from typing import Optional

from mythos.adapters.output.legendary.cli_wrapper import LegendaryCliWrapper
from mythos.adapters.output.legendary.mappers import legendary_installed_to_domain
from mythos.domain.entities import InstalledInfo
from mythos.domain.value_objects import AppName
from mythos.ports.output import InstalledLibraryRepository

logger = logging.getLogger(__name__)


class LegendaryInstalledRepo(InstalledLibraryRepository):
    def __init__(self, cli: Optional[LegendaryCliWrapper] = None) -> None:
        self._cli = cli or LegendaryCliWrapper()

    def get_all(self) -> list[InstalledInfo]:
        try:
            raw = self._cli.run_json(["list-installed", "--json"])
            return [legendary_installed_to_domain(g) for g in raw]
        except Exception as exc:
            logger.error("Failed to read installed game list: %s", exc)
            return []

    def get(self, app_name: AppName) -> Optional[InstalledInfo]:
        try:
            raw = self._cli.run_json(["list-installed", "--json"])
            for entry in raw:
                if entry.get("app_name") == str(app_name):
                    return legendary_installed_to_domain(entry)
            return None
        except Exception as exc:
            logger.error("Failed to get installed game %s: %s", app_name, exc)
            return None

    def save(self, info: InstalledInfo) -> None:
        logger.debug("InstalledRepo.save() called for %s (no-op)", info.app_name)

    def remove(self, app_name: AppName) -> None:
        logger.debug("InstalledRepo.remove() called for %s (no-op)", app_name)
