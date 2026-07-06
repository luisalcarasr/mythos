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
    "Mac": Platform.MAC,
    "macOS": Platform.MAC,
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

    # Extract cover image URL from metadata / keyImages
    cover_url = ""
    try:
        key_images = lg_game.metadata.get("keyImages", [])
        for img in key_images:
            if img.get("type") in ("DieselGameBoxTall", "DieselGameBox", "Thumbnail"):
                cover_url = img.get("url", "")
                break
        if not cover_url and key_images:
            cover_url = key_images[0].get("url", "")
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
    try:
        description = lg_game.metadata.get("description", {}).get("shortDescription", "")
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
        cover_url=cover_url,
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
    )
