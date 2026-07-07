# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Functional fake RunnerManagerPort for design mode and unit tests."""

from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path
from typing import Callable, Optional

from mythos.domain.value_objects import Progress, ProtonRelease, WineRunnerType
from mythos.ports.output import RunnerManagerPort

# ---------------------------------------------------------------------------
# Demo catalogue
# ---------------------------------------------------------------------------

_PROTON_GE_RELEASES: list[ProtonRelease] = [
    ProtonRelease(
        name="GE-Proton9-20",
        runner_type=WineRunnerType.PROTON_GE,
        version="GE-Proton9-20",
        download_url="https://example.fake/GE-Proton9-20.tar.gz",
        size_bytes=366_000_000,
    ),
    ProtonRelease(
        name="GE-Proton9-16",
        runner_type=WineRunnerType.PROTON_GE,
        version="GE-Proton9-16",
        download_url="https://example.fake/GE-Proton9-16.tar.gz",
        size_bytes=362_000_000,
    ),
    ProtonRelease(
        name="GE-Proton8-32",
        runner_type=WineRunnerType.PROTON_GE,
        version="GE-Proton8-32",
        download_url="https://example.fake/GE-Proton8-32.tar.gz",
        size_bytes=340_000_000,
    ),
]

_PROTON_RELEASES: list[ProtonRelease] = [
    ProtonRelease(
        name="Proton 9.0-4",
        runner_type=WineRunnerType.PROTON,
        version="9.0-4",
        download_url="https://example.fake/proton-9.0-4.tar.gz",
        size_bytes=420_000_000,
    ),
    ProtonRelease(
        name="Proton 8.0-5",
        runner_type=WineRunnerType.PROTON,
        version="8.0-5",
        download_url="https://example.fake/proton-8.0-5.tar.gz",
        size_bytes=400_000_000,
    ),
]

_ALL_RELEASES = _PROTON_GE_RELEASES + _PROTON_RELEASES

# Simulate GE-Proton9-20 already installed out of the box (design mode)
_DEFAULT_INSTALLED = {"GE-Proton9-20"}


class FakeRunnerManager(RunnerManagerPort):
    """
    In-memory fake runner manager for design mode and unit tests.

    ``install()`` simulates a download with staged ``Progress`` callbacks
    and a short delay per step.  Installed state is kept in-memory.

    Parameters
    ----------
    pre_installed:
        Set of version strings considered already installed on startup.
        Defaults to ``{"GE-Proton9-20"}`` so the Runner tab shows at
        least one installed build in design mode.
    install_steps:
        Number of progress callbacks emitted per install (default 5).
    step_delay:
        Seconds to sleep between steps (default 0.05 — fast for tests).
    """

    def __init__(
        self,
        pre_installed: Optional[set[str]] = None,
        install_steps: int = 5,
        step_delay: float = 0.05,
    ) -> None:
        self._installed: set[str] = (
            set(pre_installed) if pre_installed is not None else set(_DEFAULT_INSTALLED)
        )
        self._install_steps = install_steps
        self._step_delay = step_delay
        self._fake_install_root = Path("/fake/runners")

    # ---------------------------------------------------------------- #
    # RunnerManagerPort                                                  #
    # ---------------------------------------------------------------- #

    def list_available(
        self, runner_type: Optional[WineRunnerType] = None
    ) -> list[ProtonRelease]:
        releases = list(_ALL_RELEASES)
        if runner_type is not None:
            releases = [r for r in releases if r.runner_type == runner_type]
        return releases

    def list_installed(
        self, runner_type: Optional[WineRunnerType] = None
    ) -> list[ProtonRelease]:
        result: list[ProtonRelease] = []
        for r in _ALL_RELEASES:
            if r.version not in self._installed:
                continue
            if runner_type is not None and r.runner_type != runner_type:
                continue
            result.append(
                replace(
                    r,
                    installed=True,
                    install_path=self._fake_install_root / r.version,
                )
            )
        return result

    def install(
        self,
        release: ProtonRelease,
        on_progress: Callable[[Progress], None],
    ) -> ProtonRelease:
        total = release.size_bytes or (360 * 1024 * 1024)
        for step in range(1, self._install_steps + 1):
            if self._step_delay:
                time.sleep(self._step_delay)
            downloaded = int(total * step / self._install_steps)
            on_progress(
                Progress(
                    fraction=step / self._install_steps,
                    downloaded_bytes=downloaded,
                    total_bytes=total,
                    speed_bps=80 * 1024 * 1024,
                    eta_seconds=max(0, (self._install_steps - step) * self._step_delay),
                )
            )

        self._installed.add(release.version)
        return replace(
            release,
            installed=True,
            install_path=self._fake_install_root / release.version,
        )

    def remove(self, release: ProtonRelease) -> None:
        self._installed.discard(release.version)

    def is_installed(self, release: ProtonRelease) -> bool:
        return release.version in self._installed
