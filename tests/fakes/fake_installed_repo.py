# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""In-memory fake InstalledLibraryRepository."""

from __future__ import annotations

from typing import Optional

from mythos.domain.entities import InstalledInfo
from mythos.domain.value_objects import AppName
from mythos.ports.output import InstalledLibraryRepository


class FakeInstalledRepo(InstalledLibraryRepository):
    def __init__(self, initial: Optional[list[InstalledInfo]] = None) -> None:
        self._store: dict[AppName, InstalledInfo] = {
            i.app_name: i for i in (initial or [])
        }

    def get_all(self) -> list[InstalledInfo]:
        return list(self._store.values())

    def get(self, app_name: AppName) -> Optional[InstalledInfo]:
        return self._store.get(app_name)

    def save(self, info: InstalledInfo) -> None:
        self._store[info.app_name] = info

    def remove(self, app_name: AppName) -> None:
        self._store.pop(app_name, None)
