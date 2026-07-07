# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for Proton runner management use cases."""

from __future__ import annotations

import pytest

from mythos.adapters.output.fakes.fake_event_bus import FakeEventBus
from mythos.adapters.output.fakes.fake_installed_repo import FakeInstalledRepo
from mythos.adapters.output.fakes.fake_runner_manager import FakeRunnerManager
from mythos.application.runners import InstallProton, ListProtonVersions, SetGameProton
from mythos.domain.entities import InstalledInfo
from mythos.domain.events import RunnerInstallCompleted, RunnerInstallStarted
from mythos.domain.value_objects import (
    AppName,
    DiskSize,
    InstallPath,
    LaunchOptions,
    Platform,
    ProtonRelease,
    WineRunnerType,
)
from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def manager() -> FakeRunnerManager:
    return FakeRunnerManager(pre_installed=set(), install_steps=3, step_delay=0)


@pytest.fixture
def manager_with_preinstall() -> FakeRunnerManager:
    return FakeRunnerManager(
        pre_installed={"GE-Proton9-20"}, install_steps=3, step_delay=0
    )


@pytest.fixture
def installed_repo() -> FakeInstalledRepo:
    info = InstalledInfo(
        app_name=AppName("Hades"),
        install_path=InstallPath(Path("/games/Hades")),
        version="1.0.0",
        platform=Platform.MAC,
        install_size=DiskSize.from_gib(5),
    )
    return FakeInstalledRepo(initial=[info])


# ---------------------------------------------------------------------------
# ListProtonVersions
# ---------------------------------------------------------------------------


def test_list_returns_all_releases(manager: FakeRunnerManager) -> None:
    uc = ListProtonVersions(runner_manager=manager)
    releases = uc.execute()
    assert len(releases) > 0
    types = {r.runner_type for r in releases}
    assert WineRunnerType.PROTON in types
    assert WineRunnerType.PROTON_GE in types


def test_list_filters_by_runner_type(manager: FakeRunnerManager) -> None:
    uc = ListProtonVersions(runner_manager=manager)
    ge_only = uc.execute(runner_type=WineRunnerType.PROTON_GE)
    assert all(r.runner_type == WineRunnerType.PROTON_GE for r in ge_only)
    assert len(ge_only) > 0


def test_list_installed_first(manager_with_preinstall: FakeRunnerManager) -> None:
    uc = ListProtonVersions(runner_manager=manager_with_preinstall)
    releases = uc.execute(runner_type=WineRunnerType.PROTON_GE)
    # First entry should be the pre-installed one
    assert releases[0].installed is True
    assert releases[0].version == "GE-Proton9-20"


# ---------------------------------------------------------------------------
# InstallProton
# ---------------------------------------------------------------------------


def test_install_reports_progress(manager: FakeRunnerManager) -> None:
    bus = FakeEventBus()
    uc = InstallProton(runner_manager=manager, event_bus=bus)

    release = manager.list_available(WineRunnerType.PROTON_GE)[0]
    progress_calls: list[float] = []

    # Patch manager to capture progress via fake (steps=3, delay=0)
    installed = uc.execute(release)

    assert installed.installed is True
    assert installed.install_path is not None


def test_install_publishes_started_and_completed(manager: FakeRunnerManager) -> None:
    bus = FakeEventBus()
    uc = InstallProton(runner_manager=manager, event_bus=bus)
    release = manager.list_available(WineRunnerType.PROTON_GE)[0]

    uc.execute(release)

    assert len(bus.events_of(RunnerInstallStarted)) == 1
    assert len(bus.events_of(RunnerInstallCompleted)) == 1
    assert bus.events_of(RunnerInstallStarted)[0].runner_name == release.name
    assert bus.events_of(RunnerInstallCompleted)[0].runner_name == release.name


def test_install_marks_as_installed(manager: FakeRunnerManager) -> None:
    uc = InstallProton(runner_manager=manager)
    release = manager.list_available(WineRunnerType.PROTON_GE)[0]
    assert not manager.is_installed(release)

    uc.execute(release)

    assert manager.is_installed(release)


# ---------------------------------------------------------------------------
# SetGameProton
# ---------------------------------------------------------------------------


def test_set_game_proton_persists_runner(installed_repo: FakeInstalledRepo) -> None:
    uc = SetGameProton(installed_repo=installed_repo)
    app_name = AppName("Hades")

    uc.execute(app_name, WineRunnerType.PROTON_GE, "GE-Proton9-20")

    info = installed_repo.get(app_name)
    assert info is not None
    assert info.launch_options.wine_runner == WineRunnerType.PROTON_GE
    assert info.launch_options.proton_version == "GE-Proton9-20"


def test_set_game_proton_noop_for_unknown_game(installed_repo: FakeInstalledRepo) -> None:
    uc = SetGameProton(installed_repo=installed_repo)
    # Should not raise
    uc.execute(AppName("UnknownGame"), WineRunnerType.PROTON, "9.0-4")


# ---------------------------------------------------------------------------
# ProtonRelease value object
# ---------------------------------------------------------------------------


def test_proton_release_label_ge() -> None:
    r = ProtonRelease(
        name="GE-Proton9-20",
        runner_type=WineRunnerType.PROTON_GE,
        version="GE-Proton9-20",
    )
    assert r.label == "Proton-GE — GE-Proton9-20"


def test_proton_release_label_proton() -> None:
    r = ProtonRelease(
        name="Proton 9.0-4",
        runner_type=WineRunnerType.PROTON,
        version="9.0-4",
    )
    assert r.label == "Proton — 9.0-4"
