# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
GitHubRunnerManager — real Proton / Proton-GE download adapter.

Sources
-------
Proton-GE:
    https://github.com/GloriousEggroll/proton-ge-custom/releases
    Tarball pattern: GE-ProtonX-Y.tar.gz

Upstream Proton (Valve community builds):
    https://github.com/ValveSoftware/Proton/releases
    Tarball pattern: Proton-X.Y-Z.tar.gz

NOTE: The actual download / extraction logic is **not yet implemented**.
``install()`` raises ``NotImplementedError`` with an actionable message.
``list_available()`` returns a static catalogue so the UI is usable
before the real implementation lands.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

from mythos.config.paths import AppPaths
from mythos.domain.value_objects import Progress, ProtonRelease, WineRunnerType
from mythos.ports.output import RunnerManagerPort

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static catalogue — updated until the real GitHub API call is implemented.
# ---------------------------------------------------------------------------

_CATALOGUE: list[ProtonRelease] = [
    # Proton-GE
    ProtonRelease(
        name="GE-Proton9-20",
        runner_type=WineRunnerType.PROTON_GE,
        version="GE-Proton9-20",
        download_url=(
            "https://github.com/GloriousEggroll/proton-ge-custom"
            "/releases/download/GE-Proton9-20/GE-Proton9-20.tar.gz"
        ),
        size_bytes=366_000_000,
    ),
    ProtonRelease(
        name="GE-Proton9-16",
        runner_type=WineRunnerType.PROTON_GE,
        version="GE-Proton9-16",
        download_url=(
            "https://github.com/GloriousEggroll/proton-ge-custom"
            "/releases/download/GE-Proton9-16/GE-Proton9-16.tar.gz"
        ),
        size_bytes=362_000_000,
    ),
    ProtonRelease(
        name="GE-Proton8-32",
        runner_type=WineRunnerType.PROTON_GE,
        version="GE-Proton8-32",
        download_url=(
            "https://github.com/GloriousEggroll/proton-ge-custom"
            "/releases/download/GE-Proton8-32/GE-Proton8-32.tar.gz"
        ),
        size_bytes=340_000_000,
    ),
    # Upstream Proton
    ProtonRelease(
        name="Proton 9.0-4",
        runner_type=WineRunnerType.PROTON,
        version="9.0-4",
        download_url=(
            "https://github.com/ValveSoftware/Proton"
            "/releases/download/proton-9.0-4/proton-9.0-4.tar.gz"
        ),
        size_bytes=420_000_000,
    ),
    ProtonRelease(
        name="Proton 8.0-5",
        runner_type=WineRunnerType.PROTON,
        version="8.0-5",
        download_url=(
            "https://github.com/ValveSoftware/Proton"
            "/releases/download/proton-8.0-5/proton-8.0-5.tar.gz"
        ),
        size_bytes=400_000_000,
    ),
]


class GitHubRunnerManager(RunnerManagerPort):
    """
    Downloads and manages Proton runtimes from GitHub releases.

    ``install()`` is not yet implemented — it raises ``NotImplementedError``.
    All other methods are functional.
    """

    def __init__(self, runners_dir: Optional[Path] = None) -> None:
        self._runners_dir = runners_dir or AppPaths.runners_dir

    # ---------------------------------------------------------------- #
    # RunnerManagerPort                                                  #
    # ---------------------------------------------------------------- #

    def list_available(
        self, runner_type: Optional[WineRunnerType] = None
    ) -> list[ProtonRelease]:
        if runner_type is None:
            return list(_CATALOGUE)
        return [r for r in _CATALOGUE if r.runner_type == runner_type]

    def list_installed(
        self, runner_type: Optional[WineRunnerType] = None
    ) -> list[ProtonRelease]:
        installed: list[ProtonRelease] = []
        if not self._runners_dir.exists():
            return installed

        for entry in sorted(self._runners_dir.iterdir()):
            if not entry.is_dir():
                continue
            # Match against catalogue by directory name
            for release in _CATALOGUE:
                if release.version in entry.name or entry.name == release.name:
                    if runner_type is None or release.runner_type == runner_type:
                        from dataclasses import replace
                        installed.append(
                            replace(release, installed=True, install_path=entry)
                        )
                    break

        return installed

    def install(
        self,
        release: ProtonRelease,
        on_progress: Callable[[Progress], None],
    ) -> ProtonRelease:
        raise NotImplementedError(
            f"Real download of {release.name} is not yet implemented. "
            "Use --fake mode to simulate runner installation during development."
        )

    def remove(self, release: ProtonRelease) -> None:
        if release.install_path and release.install_path.exists():
            import shutil
            shutil.rmtree(release.install_path)
            logger.info("Removed runner %s from %s", release.name, release.install_path)

    def is_installed(self, release: ProtonRelease) -> bool:
        return any(
            r.version == release.version and r.runner_type == release.runner_type
            for r in self.list_installed()
        )
