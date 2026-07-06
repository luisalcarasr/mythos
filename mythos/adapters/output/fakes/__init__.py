# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
In-memory fake adapters for design-mode and unit tests.

All fakes satisfy their port contract exactly; they carry no system
dependencies (no Legendary, no GTK, no network).  They are the single
source of truth — both ``mythos --fake`` and ``pytest`` import from here.
"""

from mythos.adapters.output.fakes.fake_auth import FakeAuthSession
from mythos.adapters.output.fakes.fake_cloud_saves import FakeCloudSaves
from mythos.adapters.output.fakes.fake_download_queue import FakeDownloadQueue
from mythos.adapters.output.fakes.fake_epic_store import FakeEpicStore
from mythos.adapters.output.fakes.fake_event_bus import FakeEventBus
from mythos.adapters.output.fakes.fake_image_cache import FakeImageCache
from mythos.adapters.output.fakes.fake_installed_repo import FakeInstalledRepo
from mythos.adapters.output.fakes.fake_settings_repo import FakeSettingsRepo
from mythos.adapters.output.fakes.fake_wine_runtime import FakeWineRuntime

__all__ = [
    "FakeAuthSession",
    "FakeCloudSaves",
    "FakeDownloadQueue",
    "FakeEpicStore",
    "FakeEventBus",
    "FakeImageCache",
    "FakeInstalledRepo",
    "FakeSettingsRepo",
    "FakeWineRuntime",
]
