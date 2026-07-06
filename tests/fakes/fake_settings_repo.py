# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""In-memory fake SettingsRepository."""

from __future__ import annotations

from mythos.domain.entities import AppSettings
from mythos.ports.output import SettingsRepository


class FakeSettingsRepo(SettingsRepository):
    def __init__(self, settings: Optional[AppSettings] = None) -> None:  # noqa: F821
        self._settings = settings or AppSettings()

    def load(self) -> AppSettings:
        return self._settings

    def save(self, settings: AppSettings) -> None:
        self._settings = settings


# Fix forward ref
from typing import Optional  # noqa: E402
