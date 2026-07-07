# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Per-game Proton configuration use case (replaces application/runners.py)."""

from __future__ import annotations

import logging
from dataclasses import replace

from mythos.domain.value_objects import AppName, WineRunnerType
from mythos.ports.input import SetGameProtonUseCase
from mythos.ports.output import InstalledLibraryRepository

logger = logging.getLogger(__name__)


class SetGameProton(SetGameProtonUseCase):
    """Persist the per-game Wine/Proton selection in InstalledInfo."""

    def __init__(self, installed_repo: InstalledLibraryRepository) -> None:
        self._repo = installed_repo

    def execute(
        self,
        app_name: AppName,
        runner_type: WineRunnerType,
        proton_version: str = "",
    ) -> None:
        info = self._repo.get(app_name)
        if info is None:
            logger.warning(
                "SetGameProton: game %s not in installed repo — skipping.", app_name,
            )
            return

        updated_options = replace(
            info.launch_options,
            wine_runner=runner_type,
        )
        updated_info = replace(info, launch_options=updated_options)
        self._repo.save(updated_info)
        logger.info("Game %s runner set to %s", app_name, runner_type.value)
