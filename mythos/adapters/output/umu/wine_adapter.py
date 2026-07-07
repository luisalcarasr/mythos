# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
UmuWineAdapter — Wine/Proton execution via umu-launcher.

umu wraps Valve's Steam Runtime container + Proton so games run in the
same environment as native Steam games.  It handles Steam Runtime setup,
Proton auto-download, and protonfixes automatically.

This adapter integrates with ``SubprocessRunner`` (Opción B) so the game
process is monitored in background without blocking the GTK main loop.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Callable, Optional

from mythos.adapters.output.process.runner import SubprocessRunner
from mythos.domain.value_objects import WineRunnerType
from mythos.ports.output import EventBus, WineRuntimePort

logger = logging.getLogger(__name__)

# umu PROTONPATH tokens — these trigger auto-download
_UMU_PROTON_TOKENS = {
    WineRunnerType.PROTON: "UMU-Proton",
    WineRunnerType.PROTON_GE: "GE-Proton",
    WineRunnerType.WINE: None,  # let umu decide
    WineRunnerType.CROSSOVER: None,
    WineRunnerType.NONE: None,  # no Proton wrapper, run natively in SLR
}


class UmuWineAdapter(WineRuntimePort):
    """
    Wine/Proton execution adapter backed by umu-launcher.

    Uses ``umu-run`` CLI via ``SubprocessRunner`` for non-blocking
    process monitoring.  The game's PID is returned immediately and
    ``on_exit`` is called when the game exits.

    Parameters
    ----------
    runner:
        ``SubprocessRunner`` instance for launching background processes.
    event_bus:
        Optional event bus for publishing ``GameStopped`` (passed through
        to SubprocessRunner).
    """

    def __init__(
        self,
        runner: SubprocessRunner,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self._runner = runner
        self._bus = event_bus

    # ---------------------------------------------------------------- #
    # WineRuntimePort                                                    #
    # ---------------------------------------------------------------- #

    def list_runtimes(self) -> list[dict]:
        """
        List available Proton runtimes.

        umu auto-downloads Proton, so we return the well-known tokens
        plus any local installs found under Steam's common directory.
        """
        runtimes: list[dict] = [
            {
                "name": "UMU-Proton (auto-download)",
                "type": WineRunnerType.PROTON,
                "path": Path("UMU-Proton"),
                "version": "latest",
            },
            {
                "name": "GE-Proton (auto-download)",
                "type": WineRunnerType.PROTON_GE,
                "path": Path("GE-Proton"),
                "version": "latest",
            },
        ]

        steam_common = Path.home() / ".steam" / "steam" / "steamapps" / "common"
        if steam_common.exists():
            for entry in sorted(steam_common.iterdir()):
                if "Proton" in entry.name and (entry / "proton").exists():
                    runtimes.append({
                        "name": entry.name,
                        "type": WineRunnerType.PROTON,
                        "path": entry,
                        "version": entry.name,
                    })

        return runtimes

    def get_default(self) -> Optional[dict]:
        """Return UMU-Proton (auto-download) as the default."""
        return {
            "name": "UMU-Proton (auto-download)",
            "type": WineRunnerType.PROTON,
            "path": Path("UMU-Proton"),
            "version": "latest",
        }

    def validate(self, executable: Path) -> bool:
        """Return ``True`` if *executable* exists or is a valid umu token."""
        path_str = str(executable)
        if path_str in {"UMU-Proton", "GE-Proton", "GE-Latest", "UMU-Latest"}:
            return True
        return executable.exists()

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
        """
        Execute a game via ``umu-run`` in the background.

        Sets the required umu environment variables, builds the command
        ``umu-run <exe> [args...]``, and passes it to
        ``SubprocessRunner.run_background()``.

        Returns the PID of the spawned ``umu-run`` process immediately.
        """
        proton_path = self._map_proton_path(wine_runner, env.get("PROTONPATH"))

        merged_env = {
            "GAMEID": game_id or "umu-default",
            "STORE": store or "",
            "WINEPREFIX": str(wineprefix.resolve()),
        }

        if proton_path is not None:
            merged_env["PROTONPATH"] = proton_path

        merged_env.update(env)

        command = ["umu-run", str(executable.resolve())] + list(args)

        logger.info(
            "Launching via umu: %s GAMEID=%s STORE=%s WINEPREFIX=%s PROTONPATH=%s",
            executable,
            merged_env["GAMEID"],
            merged_env["STORE"],
            merged_env["WINEPREFIX"],
            merged_env.get("PROTONPATH", "default"),
        )

        pid = self._runner.run_background(
            command=command,
            env=merged_env,
            on_exit=on_exit,
        )

        logger.debug("umu-run PID=%d", pid)
        return pid

    # ---------------------------------------------------------------- #
    # Private helpers                                                    #
    # ---------------------------------------------------------------- #

    @staticmethod
    def _map_proton_path(
        runner_type: WineRunnerType,
        custom_path: Optional[str],
    ) -> Optional[str]:
        """
        Map ``WineRunnerType`` to a ``PROTONPATH`` value for umu.

        Priority: custom path > token from runner_type > None (umu default).
        """
        if custom_path:
            return custom_path
        return _UMU_PROTON_TOKENS.get(runner_type)
