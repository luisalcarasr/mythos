# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Library use cases."""

from __future__ import annotations

import logging
from typing import Optional

from mythos.domain.entities import Game
from mythos.domain.events import LibraryRefreshCompleted, LibraryRefreshStarted
from mythos.domain.value_objects import AppName
from mythos.ports.input import ListLibraryUseCase, RefreshLibraryUseCase
from mythos.ports.output import (
    EpicStorePort,
    EventBus,
    ImageCachePort,
    InstalledLibraryRepository,
)

logger = logging.getLogger(__name__)


class ListLibrary(ListLibraryUseCase):
    """
    Return all games merging the remote library with local install state.

    No network request is made; relies on whatever is cached by
    ``EpicStorePort.list_games()`` (which may use legendary's local
    metadata files).
    """

    def __init__(
        self,
        installed_repo: InstalledLibraryRepository,
        epic_store: EpicStorePort,
        image_cache: Optional[ImageCachePort] = None,
    ) -> None:
        self._installed = installed_repo
        self._store = epic_store
        self._images = image_cache

    def execute(self, include_dlc: bool = False) -> list[Game]:
        games = self._store.list_games(include_dlc=include_dlc)
        installed_map = {
            info.app_name: info for info in self._installed.get_all()
        }

        for game in games:
            if game.app_name in installed_map:
                game.installed_info = installed_map[game.app_name]
                from mythos.domain.value_objects import GameStatus
                game.status = GameStatus.INSTALLED

            # Attach cached cover paths if available
            if self._images:
                cached = self._images.get(game.app_name)
                if cached:
                    game.cover_local_path = cached
                cached_wide = self._images.get_wide(game.app_name)
                if cached_wide:
                    game.cover_local_wide_path = cached_wide

        return games


class RefreshLibrary(RefreshLibraryUseCase):
    """
    Force-refresh library from Epic's servers.

    1. Publishes ``LibraryRefreshStarted``.
    2. Fetches from the store (network call via legendary).
    3. Fetches covers for new games (async-friendly — sequential here).
    4. Publishes ``LibraryRefreshCompleted``.
    """

    def __init__(
        self,
        epic_store: EpicStorePort,
        installed_repo: InstalledLibraryRepository,
        image_cache: Optional[ImageCachePort] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self._store = epic_store
        self._installed = installed_repo
        self._images = image_cache
        self._bus = event_bus

    def execute(self) -> list[Game]:
        if self._bus:
            self._bus.publish(LibraryRefreshStarted())

        logger.info("Refreshing Epic Games library…")
        games = self._store.list_games(include_dlc=False)
        installed_map = {
            info.app_name: info for info in self._installed.get_all()
        }

        for game in games:
            if game.app_name in installed_map:
                game.installed_info = installed_map[game.app_name]
                from mythos.domain.value_objects import GameStatus
                game.status = GameStatus.INSTALLED

            # Download covers if not already cached
            if self._images:
                if game.cover_url:
                    cached = self._images.get(game.app_name)
                    if not cached:
                        try:
                            cached = self._images.fetch_and_cache(
                                game.app_name, game.cover_url
                            )
                        except Exception as exc:  # noqa: BLE001
                            logger.warning(
                                "Could not cache cover for %s: %s", game.app_name, exc
                            )
                    if cached:
                        game.cover_local_path = cached

                if game.cover_url_wide:
                    cached_wide = self._images.get_wide(game.app_name)
                    if not cached_wide:
                        try:
                            cached_wide = self._images.fetch_and_cache_wide(
                                game.app_name, game.cover_url_wide
                            )
                        except Exception as exc:  # noqa: BLE001
                            logger.warning(
                                "Could not cache wide cover for %s: %s",
                                game.app_name, exc,
                            )
                    if cached_wide:
                        game.cover_local_wide_path = cached_wide

        if self._bus:
            self._bus.publish(LibraryRefreshCompleted(total_games=len(games)))

        logger.info("Library refresh complete: %d games.", len(games))
        return games
