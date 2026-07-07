from __future__ import annotations

import logging

from mythos.config.container import Container

logger = logging.getLogger(__name__)


def build_fake() -> Container:
    from mythos.adapters.output.fakes.fake_auth import FakeAuthSession
    from mythos.adapters.output.fakes.fake_cloud_saves import FakeCloudSaves
    from mythos.adapters.output.fakes.fake_epic_store import FakeEpicStore
    from mythos.adapters.output.fakes.fake_event_bus import FakeEventBus
    from mythos.adapters.output.fakes.fake_image_cache import FakeImageCache
    from mythos.adapters.output.fakes.fake_installed_repo import FakeInstalledRepo
    from mythos.adapters.output.fakes.fake_settings_repo import FakeSettingsRepo
    from mythos.adapters.output.fakes.fake_wine_runtime import FakeWineRuntime
    from mythos.adapters.output.umu.database import UmuDatabase

    from mythos.adapters.output.fakes.demo_data import (
        demo_games,
        demo_installed,
        demo_settings,
    )

    from mythos.application.auth import GetSession, Login, Logout
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
    from mythos.application.game_proton import SetGameProton

    logger.info("Building FAKE dependency container (design mode)…")

    games = demo_games()
    installed = demo_installed()
    settings = demo_settings()

    event_bus = FakeEventBus()

    auth_session_repo = FakeAuthSession(logged_in=True)

    epic_store = FakeEpicStore(games=games, installed=installed)
    installed_library_repo = FakeInstalledRepo(initial=installed)
    cloud_save_port = FakeCloudSaves()
    wine_runtime_port = FakeWineRuntime()
    settings_repo = FakeSettingsRepo(settings=settings)
    umu_database_port = UmuDatabase(cache_dir="/tmp/mythos-fake-umu")

    image_cache_port = FakeImageCache()
    for game in games:
        image_cache_port.preload(game.app_name, game.title)

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
        umu_database=umu_database_port,
    )
    update_uc = UpdateGame(
        epic_store=epic_store,
        event_bus=event_bus,
        umu_database=umu_database_port,
    )
    repair_uc = RepairGame(
        epic_store=epic_store,
        event_bus=event_bus,
        umu_database=umu_database_port,
    )
    move_uc = MoveGame(epic_store=epic_store, event_bus=event_bus)
    uninstall_uc = UninstallGame(epic_store=epic_store, event_bus=event_bus)

    set_game_proton_uc = SetGameProton(installed_repo=installed_library_repo)

    launch_uc = LaunchGame(
        wine_runtime=wine_runtime_port,
        epic_store=epic_store,
        installed_repo=installed_library_repo,
        settings_repo=settings_repo,
        event_bus=event_bus,
        umu_database=umu_database_port,
    )

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
        event_bus=event_bus,
        umu_database_port=umu_database_port,
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
        sync_saves_use_case=sync_saves_uc,
        get_settings_use_case=get_settings_uc,
        update_settings_use_case=update_settings_uc,
        set_game_proton_use_case=set_game_proton_uc,
    )
