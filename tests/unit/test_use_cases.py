# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for use cases using fake adapters — no GTK, no Legendary."""

from __future__ import annotations

from pathlib import Path

import pytest

from mythos.application.auth import GetSession, Login, Logout
from mythos.application.install import InstallGame, UninstallGame, UpdateGame
from mythos.application.launch import LaunchGame
from mythos.application.library import ListLibrary, RefreshLibrary
from mythos.application.settings import GetSettings, UpdateSettings
from mythos.domain.entities import AppSettings, Game
from mythos.domain.events import (
    GameInstalled,
    GameLaunched,
    GameUninstalled,
    LibraryRefreshCompleted,
    LibraryRefreshStarted,
    UserLoggedIn,
    UserLoggedOut,
)
from mythos.domain.value_objects import AppName, GameStatus

from tests.fakes.fake_auth import FakeAuthSession
from tests.fakes.fake_epic_store import FakeEpicStore
from tests.fakes.fake_event_bus import FakeEventBus
from tests.fakes.fake_installed_repo import FakeInstalledRepo
from tests.fakes.fake_settings_repo import FakeSettingsRepo


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #


def _make_game(name: str = "SugarGame", installed: bool = False) -> Game:
    return Game(app_name=AppName(name), title=name, developer="Dev")


# ------------------------------------------------------------------ #
# Auth use cases                                                       #
# ------------------------------------------------------------------ #


def test_login_returns_session_and_publishes_event() -> None:
    auth = FakeAuthSession()
    bus = FakeEventBus()
    uc = Login(auth_session_repo=auth, event_bus=bus)

    session = uc.execute("my-auth-code")

    assert session["display_name"] == "TestUser"
    assert auth.is_logged_in()
    events = bus.events_of(UserLoggedIn)
    assert len(events) == 1
    assert events[0].display_name == "TestUser"


def test_logout_clears_session_and_publishes_event() -> None:
    auth = FakeAuthSession(logged_in=True)
    bus = FakeEventBus()
    uc = Logout(auth_session_repo=auth, event_bus=bus)

    uc.execute()

    assert not auth.is_logged_in()
    assert len(bus.events_of(UserLoggedOut)) == 1


def test_get_session_returns_none_when_not_logged_in() -> None:
    auth = FakeAuthSession(logged_in=False)
    uc = GetSession(auth_session_repo=auth)
    assert uc.execute() is None


def test_get_session_returns_dict_when_logged_in() -> None:
    auth = FakeAuthSession(logged_in=True)
    uc = GetSession(auth_session_repo=auth)
    session = uc.execute()
    assert session is not None
    assert "display_name" in session


# ------------------------------------------------------------------ #
# Library use cases                                                    #
# ------------------------------------------------------------------ #


def test_list_library_returns_games() -> None:
    games = [_make_game("Alpha"), _make_game("Beta")]
    store = FakeEpicStore(games=games)
    repo = FakeInstalledRepo()
    uc = ListLibrary(installed_repo=repo, epic_store=store)

    result = uc.execute()
    assert len(result) == 2
    assert {g.title for g in result} == {"Alpha", "Beta"}


def test_list_library_marks_installed_games() -> None:
    from mythos.domain.entities import InstalledInfo
    from mythos.domain.value_objects import DiskSize, InstallPath, Platform

    app = AppName("InstalledGame")
    game = Game(app_name=app, title="InstalledGame")
    info = InstalledInfo(
        app_name=app,
        install_path=InstallPath(Path("/games/InstalledGame")),
        version="1.0",
        platform=Platform.LINUX,
        install_size=DiskSize.from_gib(2),
    )
    store = FakeEpicStore(games=[game])
    repo = FakeInstalledRepo(initial=[info])
    uc = ListLibrary(installed_repo=repo, epic_store=store)

    result = uc.execute()
    assert result[0].is_installed
    assert result[0].status == GameStatus.INSTALLED


def test_refresh_library_publishes_events() -> None:
    games = [_make_game("Gamma")]
    store = FakeEpicStore(games=games)
    repo = FakeInstalledRepo()
    bus = FakeEventBus()
    uc = RefreshLibrary(epic_store=store, installed_repo=repo, event_bus=bus)

    result = uc.execute()

    assert len(result) == 1
    assert len(bus.events_of(LibraryRefreshStarted)) == 1
    assert len(bus.events_of(LibraryRefreshCompleted)) == 1
    assert bus.events_of(LibraryRefreshCompleted)[0].total_games == 1


# ------------------------------------------------------------------ #
# Install use cases                                                    #
# ------------------------------------------------------------------ #


def test_install_game_success() -> None:
    store = FakeEpicStore()
    settings = FakeSettingsRepo()
    bus = FakeEventBus()
    uc = InstallGame(epic_store=store, settings_repo=settings, event_bus=bus)

    info = uc.execute(app_name=AppName("NewGame"), install_path=Path("/tmp/games"))

    assert AppName("NewGame") in store.install_calls
    assert info.version == "1.0"
    assert len(bus.events_of(GameInstalled)) == 1


def test_install_game_failure_publishes_failed_event() -> None:
    from mythos.domain.events import DownloadFailed

    store = FakeEpicStore(fail_install=True)
    settings = FakeSettingsRepo()
    bus = FakeEventBus()
    uc = InstallGame(epic_store=store, settings_repo=settings, event_bus=bus)

    with pytest.raises(RuntimeError):
        uc.execute(app_name=AppName("BrokenGame"), install_path=Path("/tmp/games"))

    assert len(bus.events_of(DownloadFailed)) == 1


def test_uninstall_game_publishes_event() -> None:
    store = FakeEpicStore()
    bus = FakeEventBus()
    uc = UninstallGame(epic_store=store, event_bus=bus)

    uc.execute(AppName("OldGame"))

    assert AppName("OldGame") in store.uninstall_calls
    assert len(bus.events_of(GameUninstalled)) == 1


# ------------------------------------------------------------------ #
# Launch use cases                                                     #
# ------------------------------------------------------------------ #


def test_launch_game_returns_pid_and_publishes_event() -> None:
    store = FakeEpicStore(fake_pid=9999)
    bus = FakeEventBus()
    uc = LaunchGame(epic_store=store, event_bus=bus)

    pid = uc.execute(AppName("Action"))

    assert pid == 9999
    assert AppName("Action") in store.launch_calls
    events = bus.events_of(GameLaunched)
    assert len(events) == 1
    assert events[0].pid == 9999


# ------------------------------------------------------------------ #
# Settings use cases                                                   #
# ------------------------------------------------------------------ #


def test_get_settings_returns_defaults() -> None:
    repo = FakeSettingsRepo()
    uc = GetSettings(settings_repo=repo)
    settings = uc.execute()
    assert settings.language == "en"


def test_update_settings_persists() -> None:
    repo = FakeSettingsRepo()
    uc = UpdateSettings(settings_repo=repo)
    new_settings = AppSettings(language="es")
    uc.execute(new_settings)
    assert repo.load().language == "es"
