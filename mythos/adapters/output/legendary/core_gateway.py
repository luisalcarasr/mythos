# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
LegendaryCoreGateway — THE ONLY place that imports from legendary.

This module is the anti-corruption layer between Mythos and the
legendary library.  Every other adapter delegates here so that if
legendary's internal API changes, only this file needs updating.

legendary-gl imports: ``legendary.core.LegendaryCore``

LegendaryCore is NOT designed to be used as a library; its constructor
reads config files and sets up state.  We wrap it in a lazy singleton
to avoid re-initialising it repeatedly.
"""

from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)


class LegendaryCoreGateway:
    """
    Thin wrapper around ``legendary.core.LegendaryCore``.

    Access the underlying core via the ``core`` property; it is
    instantiated lazily on first access and protected by a lock.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._core = None

    @property
    def core(self):
        """Return (creating if necessary) the LegendaryCore instance."""
        if self._core is None:
            with self._lock:
                if self._core is None:
                    self._core = self._create_core()
        return self._core

    @staticmethod
    def _create_core():
        try:
            from legendary.core import LegendaryCore  # type: ignore[import]
            logger.info("Initialising LegendaryCore…")
            core = LegendaryCore()
            logger.info("LegendaryCore ready.")
            return core
        except ImportError as exc:
            raise ImportError(
                "legendary-gl is not installed. "
                "Run: pip install legendary-gl"
            ) from exc
        except Exception as exc:
            logger.error("Failed to initialise LegendaryCore: %s", exc)
            raise

    def is_logged_in(self) -> bool:
        """Delegate to LegendaryCore.login_status."""
        try:
            return self.core.login()
        except Exception:  # noqa: BLE001
            return False

    def get_game_list(self, update_assets: bool = False):
        """
        Return the full game list as a list of legendary Game objects.

        Parameters
        ----------
        update_assets:
            When *True*, force a network refresh from Epic's CDN.
        """
        return self.core.get_game_list(update_assets=update_assets)

    def get_installed_list(self):
        """Return list of legendary InstalledGame objects."""
        return self.core.get_installed_list()

    def get_game(self, app_name: str):
        """Return a single legendary game object by app name."""
        return self.core.get_game(app_name)

    def get_installed_game(self, app_name: str):
        """Return a single legendary installed game object."""
        return self.core.get_installed_game(app_name)
