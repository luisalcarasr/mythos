# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""In-memory fake WineRuntimePort for design mode and tests."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

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
    In-memory fake WineRuntimePort for design mode and unit tests.

    ``execute_game()`` returns a fixed PID without actually spawning
    any process.
    """

    def __init__(
        self,
        runtimes: Optional[list[dict]] = None,
        fake_pid: int = 12345,
    ) -> None:
        self._runtimes = runtimes if runtimes is not None else _FAKE_RUNTIMES
        self._fake_pid = fake_pid
        self.execute_calls: list[dict] = []

    def list_runtimes(self) -> list[dict]:
        return list(self._runtimes)

    def get_default(self) -> Optional[dict]:
        return self._runtimes[0] if self._runtimes else None

    def validate(self, executable: Path) -> bool:
        return True

    def execute_game(
        self,
        executable: Path,
        args: list[str],
        wine_runner: WineRunnerType,
        wineprefix: Path,
        env: dict[str, str],
        game_id: Optional[str] = None,
        store: Optional[str] = None,
        on_exit: Optional[Callable[[int], None]] = None,
    ) -> int:
        self.execute_calls.append({
            "executable": executable,
            "args": args,
            "wine_runner": wine_runner,
            "wineprefix": wineprefix,
            "env": env,
            "game_id": game_id,
            "store": store,
        })
        if on_exit:
            on_exit(0)
        return self._fake_pid
