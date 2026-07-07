# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Fake composition root for design / UI-development mode.

``build_fake()`` mirrors ``build()`` in container.py but wires every
output port with an in-memory fake seeded with realistic demo data.
The real application-layer use cases (mythos/application/*) are wired
unchanged so the full business logic is exercised — only the external
adapters (Legendary, disk, network) are replaced.

Activate with:
    MYTHOS_FAKE=1 uv run python -m mythos
    uv run python -m mythos --fake
"""

from __future__ import annotations

import logging

from mythos.config.container import Container

logger = logging.getLogger(__name__)


def build_fake() -> Container:
    """
    Instantiate all fake adapters, seed them with demo data, wire the
    real use cases, and return a fully-populated ``Container``.
    """
    # -- Fakes --------------------------------------------------------- #
    from mythos.adapters.output.fakes.fake_auth import FakeAuthSession
    from mythos.adapters.output.fakes.fake_cloud_saves import FakeCloudSaves
    from mythos.adapters.output.fakes.fake_download_queue import FakeDownloadQueue
    from mythos.adapters.output.fakes.fake_epic_store import FakeEpicStore
    from mythos.adapters.output.fakes.fake_event_bus import FakeEventBus
    from mythos.adapters.output.fakes.fake_image_cache import FakeImageCache
    from mythos.adapters.output.fakes.fake_installed_repo import FakeInstalledRepo
    from mythos.adapters.output.fakes.fake_runner_manager import FakeRunnerManager
    from mythos.adapters.output.fakes.fake_settings_repo import FakeSettingsRepo
    from mythos.adapters.output.fakes.fake_wine_runtime import FakeWineRuntime

    # -- Demo data ----------------------------------------------------- #
    from mythos.adapters.output.fakes.demo_data import (
        demo_download_tasks,
        demo_games,
        demo_installed,
        demo_settings,
    )

    # -- Use cases (real) ---------------------------------------------- #
    from mythos.application.auth import GetSession, Login, Logout
    from mythos.application.downloads import CancelDownload, EnqueueDownload
    from mythos.application.install import (
        InstallGame,
        MoveGame,
        RepairGame,
        UninstallGame,
        UpdateGame,
    )
    from mythos.application.launch import LaunchGame
    from mythos.application.library import ListLibrary, RefreshLibrary
    from mythos.application.saves import SyncSaves
    from mythos.application.settings import GetSettings, UpdateSettings
    from mythos.application.runners import ListProtonVersions, InstallProton, SetGameProton

    logger.info("Building FAKE dependency container (design mode)…")

    # -- Seed data ------------------------------------------------------- #
    games = demo_games()
    installed = demo_installed()
    tasks = demo_download_tasks()
    settings = demo_settings()

    # -- Output adapters ------------------------------------------------- #
    event_bus = FakeEventBus()

    auth_session_repo = FakeAuthSession(logged_in=True)

    epic_store = FakeEpicStore(games=games, installed=installed)
    installed_library_repo = FakeInstalledRepo(initial=installed)
    cloud_save_port = FakeCloudSaves()
    wine_runtime_port = FakeWineRuntime()
    settings_repo = FakeSettingsRepo(settings=settings)
    download_queue_port = FakeDownloadQueue(initial=tasks)

    # Pre-render cover art for every demo game (fast, avoids first-frame lag)
    image_cache_port = FakeImageCache()
    for game in games:
        image_cache_port.preload(game.app_name, game.title)

    runner_manager = FakeRunnerManager()

    # -- Use cases ------------------------------------------------------- #
    login_uc = Login(auth_session_repo=auth_session_repo, event_bus=event_bus)
    logout_uc = Logout(auth_session_repo=auth_session_repo, event_bus=event_bus)
    get_session_uc = GetSession(auth_session_repo=auth_session_repo)

    list_library_uc = ListLibrary(
        installed_repo=installed_library_repo,
        epic_store=epic_store,
        image_cache=image_cache_port,
    )
    refresh_library_uc = RefreshLibrary(
        epic_store=epic_store,
        installed_repo=installed_library_repo,
        image_cache=image_cache_port,
        event_bus=event_bus,
    )

    install_uc = InstallGame(
        epic_store=epic_store,
        settings_repo=settings_repo,
        event_bus=event_bus,
    )
    update_uc = UpdateGame(epic_store=epic_store, event_bus=event_bus)
    repair_uc = RepairGame(epic_store=epic_store, event_bus=event_bus)
    move_uc = MoveGame(epic_store=epic_store, event_bus=event_bus)
    uninstall_uc = UninstallGame(epic_store=epic_store, event_bus=event_bus)

    list_proton_uc = ListProtonVersions(runner_manager=runner_manager)
    install_proton_uc = InstallProton(runner_manager=runner_manager, event_bus=event_bus)
    set_game_proton_uc = SetGameProton(installed_repo=installed_library_repo)

    launch_uc = LaunchGame(
        epic_store=epic_store,
        wine_runtime=wine_runtime_port,
        settings_repo=settings_repo,
        event_bus=event_bus,
        runner_manager=runner_manager,
        install_proton=install_proton_uc,
    )

    enqueue_uc = EnqueueDownload(
        install_use_case=install_uc,
        update_use_case=update_uc,
        event_bus=event_bus,
    )
    cancel_uc = CancelDownload(epic_store=epic_store, event_bus=event_bus)

    sync_saves_uc = SyncSaves(
        cloud_save_port=cloud_save_port,
        installed_repo=installed_library_repo,
        event_bus=event_bus,
    )

    get_settings_uc = GetSettings(settings_repo=settings_repo)
    update_settings_uc = UpdateSettings(settings_repo=settings_repo)

    logger.info("Fake container ready — %d demo games loaded.", len(games))

    return Container(
        epic_store=epic_store,
        auth_session_repo=auth_session_repo,
        installed_library_repo=installed_library_repo,
        cloud_save_port=cloud_save_port,
        wine_runtime_port=wine_runtime_port,
        image_cache_port=image_cache_port,
        settings_repo=settings_repo,
        download_queue_port=download_queue_port,
        event_bus=event_bus,
        runner_manager_port=runner_manager,
        login_use_case=login_uc,
        logout_use_case=logout_uc,
        get_session_use_case=get_session_uc,
        list_library_use_case=list_library_uc,
        refresh_library_use_case=refresh_library_uc,
        install_game_use_case=install_uc,
        update_game_use_case=update_uc,
        repair_game_use_case=repair_uc,
        move_game_use_case=move_uc,
        uninstall_game_use_case=uninstall_uc,
        launch_game_use_case=launch_uc,
        enqueue_download_use_case=enqueue_uc,
        cancel_download_use_case=cancel_uc,
        sync_saves_use_case=sync_saves_uc,
        get_settings_use_case=get_settings_uc,
        update_settings_use_case=update_settings_uc,
        list_proton_versions_use_case=list_proton_uc,
        install_proton_use_case=install_proton_uc,
        set_game_proton_use_case=set_game_proton_uc,
    )
