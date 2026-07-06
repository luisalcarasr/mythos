# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""In-memory fake WineRuntimePort."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from mythos.domain.value_objects import WineRunnerType
from mythos.ports.output import WineRuntimePort

_FAKE_RUNTIMES: list[dict] = [
    {
        "name": "Proton-GE 9.5",
        "type": WineRunnerType.PROTON,
        "path": Path("/opt/proton-ge/9.5"),
        "version": "9.5-GE-1",
    },
    {
        "name": "System Wine 9.0",
        "type": WineRunnerType.WINE,
        "path": Path("/usr/bin/wine"),
        "version": "9.0",
    },
]


class FakeWineRuntime(WineRuntimePort):
    """
    Returns a couple of hard-coded fake Wine runtimes so the settings
    dropdown is populated in design mode.
    """

    def __init__(self, runtimes: Optional[list[dict]] = None) -> None:
        self._runtimes = runtimes if runtimes is not None else _FAKE_RUNTIMES

    def list_runtimes(self) -> list[dict]:
        return list(self._runtimes)

    def get_default(self) -> Optional[dict]:
        return self._runtimes[0] if self._runtimes else None

    def validate(self, executable: Path) -> bool:
        return True
