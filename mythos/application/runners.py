# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Proton runner management use cases."""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import Optional

from mythos.domain.events import (
    RunnerInstallCompleted,
    RunnerInstallFailed,
    RunnerInstallStarted,
)
from mythos.domain.value_objects import AppName, ProtonRelease, WineRunnerType
from mythos.ports.input import (
    InstallProtonUseCase,
    ListProtonVersionsUseCase,
    SetGameProtonUseCase,
)
from mythos.ports.output import (
    EventBus,
    InstalledLibraryRepository,
    RunnerManagerPort,
)

logger = logging.getLogger(__name__)


class ListProtonVersions(ListProtonVersionsUseCase):
    """
    Return available Proton / Proton-GE builds.

    Installed builds are listed first so the UI can show them at the
    top of the version dropdown.
    """

    def __init__(self, runner_manager: RunnerManagerPort) -> None:
        self._mgr = runner_manager

    def execute(
        self, runner_type: Optional[WineRunnerType] = None
    ) -> list[ProtonRelease]:
        installed = self._mgr.list_installed(runner_type)
        available = [
            r for r in self._mgr.list_available(runner_type)
            if not self._mgr.is_installed(r)
        ]
        return installed + available


class InstallProton(InstallProtonUseCase):
    """Download, extract, and configure a Proton release."""

    def __init__(
        self,
        runner_manager: RunnerManagerPort,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self._mgr = runner_manager
        self._bus = event_bus

    def execute(self, release: ProtonRelease) -> ProtonRelease:
        logger.info("Installing runner %s…", release.name)

        if self._bus:
            self._bus.publish(RunnerInstallStarted(runner_name=release.name))

        try:
            def _on_progress(progress) -> None:
                # RunnerInstallProgressed published inside the adapter
                # via on_progress; no need to republish here.
                pass

            installed = self._mgr.install(release, on_progress=_on_progress)

            if self._bus:
                self._bus.publish(RunnerInstallCompleted(runner_name=release.name))

            logger.info("Runner %s installed at %s", release.name, installed.install_path)
            return installed

        except Exception as exc:
            reason = str(exc)
            logger.error("Runner install failed: %s", reason)
            if self._bus:
                self._bus.publish(
                    RunnerInstallFailed(runner_name=release.name, reason=reason)
                )
            raise


class SetGameProton(SetGameProtonUseCase):
    """Persist the per-game Proton selection in InstalledInfo.launch_options."""

    def __init__(self, installed_repo: InstalledLibraryRepository) -> None:
        self._repo = installed_repo

    def execute(
        self,
        app_name: AppName,
        runner_type: WineRunnerType,
        proton_version: str,
    ) -> None:
        info = self._repo.get(app_name)
        if info is None:
            logger.warning(
                "SetGameProton: game %s not in installed repo — skipping.", app_name
            )
            return

        updated_options = replace(
            info.launch_options,
            wine_runner=runner_type,
            proton_version=proton_version,
        )
        updated_info = replace(info, launch_options=updated_options)
        self._repo.save(updated_info)
        logger.info(
            "Game %s runner set to %s %s", app_name, runner_type.value, proton_version
        )
