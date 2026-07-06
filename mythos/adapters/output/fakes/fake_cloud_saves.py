# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""In-memory fake CloudSavePort."""

from __future__ import annotations

from typing import Callable, Optional

from mythos.domain.value_objects import AppName, SyncDirection
from mythos.ports.output import CloudSavePort


class FakeCloudSaves(CloudSavePort):
    """
    No-op cloud saves adapter.

    ``sync()`` emits a couple of progress messages and returns
    immediately.  ``supports()`` reports ``True`` for any app_name so
    the UI can show the sync controls.
    """

    def __init__(self, games_with_saves: Optional[set[str]] = None) -> None:
        # Default: all games appear to support cloud saves
        self._supported: Optional[set[str]] = games_with_saves

    def sync(
        self,
        app_name: AppName,
        direction: SyncDirection,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> None:
        if on_progress:
            on_progress(f"[fake] Syncing saves for {app_name}…")
            on_progress(f"[fake] Sync complete for {app_name}.")

    def supports(self, app_name: AppName) -> bool:
        if self._supported is None:
            return True
        return str(app_name) in self._supported
