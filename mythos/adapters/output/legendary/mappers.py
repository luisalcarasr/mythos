# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Anti-corruption layer: legendary objects → Mythos domain entities.

All translation between legendary's internal types and Mythos domain
types lives here.  If legendary renames fields, only this file changes.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from mythos.domain.entities import Game, InstalledInfo
from mythos.domain.value_objects import (
    AppName,
    DiskSize,
    GameStatus,
    InstallPath,
    Platform,
)

logger = logging.getLogger(__name__)

# Mapping from legendary platform strings to our Platform enum
_PLATFORM_MAP: dict[str, Platform] = {
    "Windows": Platform.WINDOWS,
    "Mac": Platform.WINDOWS,
    "macOS": Platform.WINDOWS,
    "Linux": Platform.LINUX,
}


def legendary_game_to_domain(lg_game: Any) -> Game:
    """
    Convert a ``legendary.models.game.Game`` (or similar) to a domain
    ``Game``.

    legendary game objects expose:
      - ``app_name``   (str)
      - ``app_title``  (str)
      - ``metadata``   (dict)
      - ``asset_infos`` (dict)
    """
    app_name = AppName(lg_game.app_name)

    # Extract cover image URLs from metadata / keyImages
    # Vertical cover (used in library grid cards)
    _VERTICAL_PRIORITY = (
        "DieselStoreFrontTall",   # 1280×1440 (8:9)  — main vertical
        "DieselGameBoxTall",      # 1200×1600 (3:4)  — vertical fallback
        "TakeoverTall",           # 1280×1440 (8:9)  — rare vertical
        "Thumbnail",              # 400×400   (1:1)  — square
    )
    # Horizontal / wide cover (used in detail page hero)
    _HORIZONTAL_PRIORITY = (
        "DieselStoreFrontWide",   # 1920×1080 (16:9)
        "OfferImageWide",         # ~2560×1440 (16:9)
        "DieselGameBox",          # 2560×1440 (16:9)
    )
    cover_url = ""
    cover_url_wide = ""
    try:
        key_images = lg_game.metadata.get("keyImages", [])
        for img in key_images:
            img_type = img.get("type", "")
            if not cover_url and img_type in _VERTICAL_PRIORITY:
                cover_url = img.get("url", "")
                if cover_url:
                    break  # stop once we find best vertical
        # Find best horizontal
        for img in key_images:
            img_type = img.get("type", "")
            if img_type in _HORIZONTAL_PRIORITY:
                cover_url_wide = img.get("url", "")
                break
        # Fallbacks
        if not cover_url and key_images:
            cover_url = key_images[0].get("url", "")
        if not cover_url_wide and cover_url:
            cover_url_wide = cover_url
    except Exception:  # noqa: BLE001
        pass

    # Developer / publisher
    developer = ""
    publisher = ""
    try:
        developer = lg_game.metadata.get("developer", "")
        publisher = (
            lg_game.metadata.get("publisher", {}).get("publisherName", "")
            if isinstance(lg_game.metadata.get("publisher"), dict)
            else lg_game.metadata.get("publisher", "")
        )
    except Exception:  # noqa: BLE001
        pass

    # Description
    description = ""
    long_description = ""
    try:
        desc = lg_game.metadata.get("description", {})
        description = desc.get("shortDescription", "")
        long_description = desc.get("longDescription", "")
    except Exception:  # noqa: BLE001
        pass

    # Categories (extract meaningful labels from Epic's internal paths)
    categories: list[str] = []
    try:
        cat_list = lg_game.metadata.get("categories", [])
        for cat in cat_list:
            if isinstance(cat, dict):
                path = cat.get("path", "")
                if path:
                    parts = path.split("/")
                    if len(parts) >= 2:
                        # Extract last meaningful segment, e.g. "games/action" → "Action"
                        segment = parts[-1]
                        # Skip internal metadata segments
                        if segment.lower() not in ("base", "edition", "games", "applications", "addons"):
                            label = segment.replace("-", " ").replace("_", " ").strip().title()
                            if label and label not in categories:
                                categories.append(label)
    except Exception:  # noqa: BLE001
        pass

    # Release date
    release_date: Optional[datetime] = None
    try:
        release_info = lg_game.metadata.get("releaseInfo", [])
        if release_info and isinstance(release_info, list):
            date_str = release_info[0].get("dateAdded", "")
            if date_str:
                release_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        pass

    # Is DLC?
    is_dlc = getattr(lg_game, "is_dlc", False)

    # Cloud saves
    supports_cloud_saves = False
    try:
        cloud_info = lg_game.metadata.get("customAttributes", {}).get("CloudSaveFolder")
        supports_cloud_saves = cloud_info is not None
    except Exception:  # noqa: BLE001
        pass

    return Game(
        app_name=app_name,
        title=getattr(lg_game, "app_title", str(app_name)),
        developer=developer,
        publisher=publisher,
        description=description,
        long_description=long_description,
        categories=categories,
        release_date=release_date,
        cover_url=cover_url,
        cover_url_wide=cover_url_wide,
        is_dlc=is_dlc,
        supports_cloud_saves=supports_cloud_saves,
    )


def legendary_installed_to_domain(lg_installed: Any) -> InstalledInfo:
    """
    Convert a ``legendary.models.game.InstalledGame`` to a domain
    ``InstalledInfo``.

    legendary InstalledGame exposes:
      - ``app_name``      (str)
      - ``install_path``  (str)
      - ``version``       (str)
      - ``platform``      (str)
      - ``install_size``  (int, bytes)
      - ``executable``    (str)
    """
    app_name = AppName(lg_installed.app_name)
    platform_str = getattr(lg_installed, "platform", "Windows")
    platform = _PLATFORM_MAP.get(platform_str, Platform.WINDOWS)
    install_size = DiskSize(getattr(lg_installed, "install_size", 0))
    install_path = InstallPath(Path(getattr(lg_installed, "install_path", "/tmp")))

    return InstalledInfo(
        app_name=app_name,
        install_path=install_path,
        version=getattr(lg_installed, "version", ""),
        platform=platform,
        install_size=install_size,
        executable=getattr(lg_installed, "executable", ""),
        can_run_offline=getattr(lg_installed, "can_run_offline", False),
        launch_parameters=getattr(lg_installed, "launch_parameters", ""),
        save_path=getattr(lg_installed, "save_path", "") or "",
    )
