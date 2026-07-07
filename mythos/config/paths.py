# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
XDG-compliant path resolution for all Mythos data files.

All paths are derived from platformdirs so they follow OS conventions:
  - Linux:  ~/.config/mythos, ~/.local/share/mythos, ~/.cache/mythos
  - Windows: %APPDATA%/mythos  (future)
"""

from __future__ import annotations

from pathlib import Path

from platformdirs import PlatformDirs

_dirs = PlatformDirs(appname="mythos", appauthor=False)


class AppPaths:
    """Central registry of all runtime paths used by Mythos."""

    # ------------------------------------------------------------------ #
    # Configuration                                                        #
    # ------------------------------------------------------------------ #
    config_dir: Path = Path(_dirs.user_config_dir)
    settings_file: Path = config_dir / "settings.json"

    # ------------------------------------------------------------------ #
    # Data                                                                 #
    # ------------------------------------------------------------------ #
    data_dir: Path = Path(_dirs.user_data_dir)
    library_cache: Path = data_dir / "library.json"

    # ------------------------------------------------------------------ #
    # Cache                                                                #
    # ------------------------------------------------------------------ #
    cache_dir: Path = Path(_dirs.user_cache_dir)
    image_cache_dir: Path = cache_dir / "covers"
    icon_cache_dir: Path = cache_dir / "icons"

    # ------------------------------------------------------------------ #
    # Runners                                                             #
    # ------------------------------------------------------------------ #
    runners_dir: Path = data_dir / "runners"

    # ------------------------------------------------------------------ #
    # Logs                                                                #
    # ------------------------------------------------------------------ #
    log_dir: Path = Path(_dirs.user_log_dir)
    log_file: Path = log_dir / "mythos.log"

    @classmethod
    def ensure_all(cls) -> None:
        """Create all required directories if they do not exist yet."""
        for attr in (
            "config_dir",
            "data_dir",
            "cache_dir",
            "image_cache_dir",
            "icon_cache_dir",
            "runners_dir",
            "log_dir",
        ):
            path: Path = getattr(cls, attr)
            path.mkdir(parents=True, exist_ok=True)
