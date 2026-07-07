# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
WineRuntimePort — detects Wine, Proton installations.

Strategy:
  1. Check for Proton runtimes under ~/.steam/steam/steamapps/common/
  2. Check for system wine via ``which wine``
  3. Check common Proton-GE locations under ~/.local/share/Steam/...
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from mythos.domain.value_objects import WineRunnerType
from mythos.ports.output import WineRuntimePort

logger = logging.getLogger(__name__)

# Common locations where Proton / Wine runtimes might be found on Linux
_STEAM_COMMON = Path.home() / ".steam" / "steam" / "steamapps" / "common"
_STEAM_COMPAT = Path.home() / ".local" / "share" / "Steam" / "steamapps" / "common"


class WineRuntimeAdapter(WineRuntimePort):
    def list_runtimes(self) -> list[dict]:
        runtimes: list[dict] = []

        runtimes.extend(self._find_proton_runtimes())
        wine = self._find_system_wine()
        if wine:
            runtimes.append(wine)

        return runtimes

    def get_default(self) -> Optional[dict]:
        runtimes = self.list_runtimes()
        return runtimes[0] if runtimes else None

    def validate(self, executable: Path) -> bool:
        if not executable.exists():
            return False
        try:
            result = subprocess.run(
                [str(executable), "--version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:  # noqa: BLE001
            return False

    # ---------------------------------------------------------------- #
    # Private discovery helpers                                          #
    # ---------------------------------------------------------------- #

    def _find_system_wine(self) -> Optional[dict]:
        wine_bin = shutil.which("wine")
        if not wine_bin:
            return None
        version = self._get_version(Path(wine_bin))
        return {
            "name": "System Wine",
            "type": WineRunnerType.WINE,
            "path": Path(wine_bin),
            "version": version,
        }

    def _find_proton_runtimes(self) -> list[dict]:
        runtimes: list[dict] = []
        for base in (_STEAM_COMMON, _STEAM_COMPAT):
            if not base.exists():
                continue
            for entry in sorted(base.iterdir()):
                if "Proton" in entry.name and entry.is_dir():
                    proton_bin = entry / "proton"
                    if proton_bin.exists():
                        runtimes.append(
                            {
                                "name": entry.name,
                                "type": WineRunnerType.PROTON,
                                "path": proton_bin,
                                "version": entry.name,
                            }
                        )
        return runtimes

    @staticmethod
    def _get_version(executable: Path) -> str:
        try:
            out = subprocess.run(
                [str(executable), "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return out.stdout.strip().splitlines()[0] if out.stdout else "unknown"
        except Exception:  # noqa: BLE001
            return "unknown"
