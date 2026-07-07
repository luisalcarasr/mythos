# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Composition Root — the single place that knows about concrete adapter classes.

All other layers (domain, ports, application) remain unaware of which
adapter implementations are in use.  Only this module imports from
``adapters.output.*``.

The ``Container`` is built once in ``__main__.py`` and passed to the GTK
application, which distributes individual use-case instances to views.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Container:
    """
    Dependency injection container wired at startup.

    Attributes are populated by ``build()`` in the correct order:
        1. Driven adapters (output ports)
        2. Use cases (application layer)
        3. Nothing from the UI layer — views pull what they need via the
           container reference passed to the GTK Application.
    """

    # ------------------------------------------------------------------ #
    # Driven adapters (output ports)                                       #
    # ------------------------------------------------------------------ #
    epic_store: object = field(default=None, repr=False)
    auth_session_repo: object = field(default=None, repr=False)
    installed_library_repo: object = field(default=None, repr=False)
    cloud_save_port: object = field(default=None, repr=False)
    wine_runtime_port: object = field(default=None, repr=False)
    image_cache_port: object = field(default=None, repr=False)
    settings_repo: object = field(default=None, repr=False)
    download_queue_port: object = field(default=None, repr=False)
    event_bus: object = field(default=None, repr=False)

    # ------------------------------------------------------------------ #
    # Use cases (application layer)                                        #
    # ------------------------------------------------------------------ #
    login_use_case: object = field(default=None, repr=False)
    logout_use_case: object = field(default=None, repr=False)
    get_session_use_case: object = field(default=None, repr=False)
    list_library_use_case: object = field(default=None, repr=False)
    refresh_library_use_case: object = field(default=None, repr=False)
    install_game_use_case: object = field(default=None, repr=False)
    update_game_use_case: object = field(default=None, repr=False)
    repair_game_use_case: object = field(default=None, repr=False)
    move_game_use_case: object = field(default=None, repr=False)
    uninstall_game_use_case: object = field(default=None, repr=False)
    launch_game_use_case: object = field(default=None, repr=False)
    enqueue_download_use_case: object = field(default=None, repr=False)
    cancel_download_use_case: object = field(default=None, repr=False)
    sync_saves_use_case: object = field(default=None, repr=False)
    get_settings_use_case: object = field(default=None, repr=False)
    update_settings_use_case: object = field(default=None, repr=False)
    pause_download_use_case: object = field(default=None, repr=False)
    resume_download_use_case: object = field(default=None, repr=False)
    set_game_proton_use_case: object = field(default=None, repr=False)


def build() -> Container:
    """
    Instantiate all adapters and use cases and return a fully-wired
    ``Container``.

    Import order matters — output adapters first, then use cases that
    depend on them.
    """
    from mythos.adapters.output.legendary.epic_store import LegendaryEpicStore
    from mythos.adapters.output.legendary.auth_session import LegendaryAuthSession
    from mythos.adapters.output.legendary.installed_repo import LegendaryInstalledRepo
    from mythos.adapters.output.legendary.cloud_saves import LegendaryCloudSaves
    from mythos.adapters.output.legendary.core_gateway import LegendaryCoreGateway
    from mythos.adapters.output.umu.wine_adapter import UmuWineAdapter
    from mythos.adapters.output.storage.image_cache import DiskImageCache
    from mythos.adapters.output.storage.settings_json import JsonSettingsRepository
    from mythos.adapters.output.process.runner import SubprocessRunner
    from mythos.adapters.output.events.glib_bus import GLibEventBus

    from mythos.application.auth import Login, Logout, GetSession
    from mythos.application.library import ListLibrary, RefreshLibrary
    from mythos.application.install import (
        InstallGame,
        UpdateGame,
        RepairGame,
        MoveGame,
        UninstallGame,
    )
    from mythos.application.launch import LaunchGame
    from mythos.application.downloads import EnqueueDownload, CancelDownload, PauseDownload, ResumeDownload
    from mythos.application.saves import SyncSaves
    from mythos.application.settings import GetSettings, UpdateSettings
    from mythos.application.game_proton import SetGameProton

    logger.info("Building dependency container…")

    # -- Shared legendary gateway ----------------------------------------
    gateway = LegendaryCoreGateway()

    # -- Driven adapters -------------------------------------------------
    event_bus = GLibEventBus()
    runner = SubprocessRunner(event_bus=event_bus)

    epic_store = LegendaryEpicStore(gateway=gateway, runner=runner)
    auth_session_repo = LegendaryAuthSession(gateway=gateway)
    installed_library_repo = LegendaryInstalledRepo(gateway=gateway)
    cloud_save_port = LegendaryCloudSaves(gateway=gateway)
    wine_runtime_port = UmuWineAdapter(runner=runner, event_bus=event_bus)
    image_cache_port = DiskImageCache()
    settings_repo = JsonSettingsRepository()
    download_queue_port = epic_store  # EpicStore doubles as queue backend

    # -- Use cases -------------------------------------------------------
    login_uc = Login(auth_session_repo=auth_session_repo)
    logout_uc = Logout(auth_session_repo=auth_session_repo)
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

    set_game_proton_uc = SetGameProton(installed_repo=installed_library_repo)

    launch_uc = LaunchGame(
        wine_runtime=wine_runtime_port,
        epic_store=epic_store,
        installed_repo=installed_library_repo,
        settings_repo=settings_repo,
        event_bus=event_bus,
    )

    enqueue_uc = EnqueueDownload(
        install_use_case=install_uc,
        update_use_case=update_uc,
        event_bus=event_bus,
    )
    cancel_uc = CancelDownload(epic_store=epic_store, event_bus=event_bus)
    pause_uc = PauseDownload(queue=download_queue_port, event_bus=event_bus)
    resume_uc = ResumeDownload(queue=download_queue_port, event_bus=event_bus)

    sync_saves_uc = SyncSaves(
        cloud_save_port=cloud_save_port,
        installed_repo=installed_library_repo,
        event_bus=event_bus,
    )

    get_settings_uc = GetSettings(settings_repo=settings_repo)
    update_settings_uc = UpdateSettings(settings_repo=settings_repo)

    logger.info("Container ready.")

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
        pause_download_use_case=pause_uc,
        resume_download_use_case=resume_uc,
        sync_saves_use_case=sync_saves_uc,
        get_settings_use_case=get_settings_uc,
        update_settings_use_case=update_settings_uc,
        set_game_proton_use_case=set_game_proton_uc,
    )
