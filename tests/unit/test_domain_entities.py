# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for domain entities — no external dependencies."""

from __future__ import annotations

import pytest
from pathlib import Path

from mythos.domain.entities import AppSettings, Game, InstalledInfo
from mythos.domain.exceptions import (
    GameAlreadyInstalledError,
    GameAlreadyRunningError,
    GameNotInstalledError,
)
from mythos.domain.value_objects import (
    AppName,
    DiskSize,
    GameStatus,
    InstallPath,
    Platform,
    Progress,
)


# ------------------------------------------------------------------ #
# AppName                                                              #
# ------------------------------------------------------------------ #


def test_app_name_valid() -> None:
    name = AppName("Sugar")
    assert str(name) == "Sugar"


def test_app_name_empty_raises() -> None:
    with pytest.raises(ValueError):
        AppName("")


def test_app_name_whitespace_raises() -> None:
    with pytest.raises(ValueError):
        AppName("   ")


# ------------------------------------------------------------------ #
# DiskSize                                                             #
# ------------------------------------------------------------------ #


def test_disk_size_from_gib() -> None:
    size = DiskSize.from_gib(2)
    assert size.to_gib() == pytest.approx(2.0, rel=1e-3)


def test_disk_size_human_readable_bytes() -> None:
    assert "B" in DiskSize(500).human_readable()


def test_disk_size_human_readable_gib() -> None:
    assert "GiB" in DiskSize.from_gib(3).human_readable()


def test_disk_size_negative_raises() -> None:
    with pytest.raises(ValueError):
        DiskSize(-1)


# ------------------------------------------------------------------ #
# Progress                                                             #
# ------------------------------------------------------------------ #


def test_progress_complete() -> None:
    p = Progress(fraction=1.0)
    assert p.is_complete
    assert p.percent == 100


def test_progress_out_of_range_raises() -> None:
    with pytest.raises(ValueError):
        Progress(fraction=1.5)


# ------------------------------------------------------------------ #
# Game lifecycle                                                        #
# ------------------------------------------------------------------ #


def _make_game(installed: bool = False) -> Game:
    app = AppName("TestGame")
    game = Game(app_name=app, title="Test Game", developer="TestDev")
    if installed:
        info = InstalledInfo(
            app_name=app,
            install_path=InstallPath(Path("/games/TestGame")),
            version="1.0",
            platform=Platform.LINUX,
            install_size=DiskSize.from_gib(2),
        )
        game.installed_info = info
        game.status = GameStatus.INSTALLED
    return game


def test_game_not_installed_initially() -> None:
    game = _make_game()
    assert not game.is_installed
    assert game.status == GameStatus.NOT_INSTALLED


def test_game_mark_installing() -> None:
    game = _make_game()
    game.mark_installing()
    assert game.status == GameStatus.INSTALLING


def test_game_mark_installing_when_already_installed_raises() -> None:
    game = _make_game(installed=True)
    with pytest.raises(GameAlreadyInstalledError):
        game.mark_installing()


def test_game_mark_installed_emits_event() -> None:
    from mythos.domain.events import GameInstalled

    game = _make_game()
    info = InstalledInfo(
        app_name=game.app_name,
        install_path=InstallPath(Path("/games/TestGame")),
        version="1.0",
        platform=Platform.LINUX,
        install_size=DiskSize.from_gib(1),
    )
    game.mark_installed(info)

    events = game.collect_events()
    assert len(events) == 1
    assert isinstance(events[0], GameInstalled)
    assert events[0].app_name == "TestGame"


def test_game_mark_uninstalled_emits_event() -> None:
    from mythos.domain.events import GameUninstalled

    game = _make_game(installed=True)
    game.mark_uninstalled()

    events = game.collect_events()
    assert any(isinstance(e, GameUninstalled) for e in events)


def test_game_mark_uninstalled_not_installed_raises() -> None:
    game = _make_game()
    with pytest.raises(GameNotInstalledError):
        game.mark_uninstalled()


def test_game_launch_when_running_raises() -> None:
    game = _make_game(installed=True)
    game.mark_launched(pid=100)
    with pytest.raises(GameAlreadyRunningError):
        game.mark_launched(pid=101)


def test_game_collect_events_clears() -> None:
    game = _make_game()
    game.mark_installed(
        InstalledInfo(
            app_name=game.app_name,
            install_path=InstallPath(Path("/games")),
            version="1.0",
            platform=Platform.LINUX,
            install_size=DiskSize(1),
        )
    )
    first = game.collect_events()
    second = game.collect_events()
    assert len(first) == 1
    assert len(second) == 0


# ------------------------------------------------------------------ #
# AppSettings                                                          #
# ------------------------------------------------------------------ #


def test_app_settings_defaults() -> None:
    s = AppSettings()
    assert s.language == "en"
    assert s.concurrent_downloads == 1


def test_app_settings_concurrent_downloads_validation() -> None:
    with pytest.raises(ValueError):
        AppSettings(concurrent_downloads=0)

    with pytest.raises(ValueError):
        AppSettings(concurrent_downloads=10)
