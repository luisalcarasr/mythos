# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Settings use cases."""

from __future__ import annotations

import logging

from mythos.domain.entities import AppSettings
from mythos.ports.input import GetSettingsUseCase, UpdateSettingsUseCase
from mythos.ports.output import SettingsRepository

logger = logging.getLogger(__name__)


class GetSettings(GetSettingsUseCase):
    def __init__(self, settings_repo: SettingsRepository) -> None:
        self._repo = settings_repo

    def execute(self) -> AppSettings:
        return self._repo.load()


class UpdateSettings(UpdateSettingsUseCase):
    def __init__(self, settings_repo: SettingsRepository) -> None:
        self._repo = settings_repo

    def execute(self, settings: AppSettings) -> None:
        logger.info("Saving settings…")
        self._repo.save(settings)
