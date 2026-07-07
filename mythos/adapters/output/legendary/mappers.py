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

_PLATFORM_MAP: dict[str, Platform] = {
    "Windows": Platform.WINDOWS,
    "Mac": Platform.WINDOWS,
    "macOS": Platform.WINDOWS,
    "Linux": Platform.LINUX,
}

_VERTICAL_PRIORITY = (
    "DieselStoreFrontTall",
    "DieselGameBoxTall",
    "TakeoverTall",
    "Thumbnail",
)
_HORIZONTAL_PRIORITY = (
    "DieselStoreFrontWide",
    "OfferImageWide",
    "DieselGameBox",
)


def legendary_game_to_domain(game_dict: dict[str, Any]) -> Game:
    app_name = AppName(game_dict["app_name"])
    metadata = game_dict.get("metadata", {})

    cover_url = ""
    cover_url_wide = ""
    try:
        key_images = metadata.get("keyImages", [])
        for img in key_images:
            img_type = img.get("type", "")
            if not cover_url and img_type in _VERTICAL_PRIORITY:
                cover_url = img.get("url", "")
                if cover_url:
                    break
        for img in key_images:
            img_type = img.get("type", "")
            if img_type in _HORIZONTAL_PRIORITY:
                cover_url_wide = img.get("url", "")
                break
        if not cover_url and key_images:
            cover_url = key_images[0].get("url", "")
        if not cover_url_wide and cover_url:
            cover_url_wide = cover_url
    except Exception:
        pass

    developer = metadata.get("developer", "")
    publisher = ""

    description = metadata.get("description", "")
    long_description = ""

    categories: list[str] = []
    try:
        cat_list = metadata.get("categories", [])
        for cat in cat_list:
            if isinstance(cat, dict):
                path = cat.get("path", "")
                if path:
                    parts = path.split("/")
                    if len(parts) >= 2:
                        segment = parts[-1]
                        if segment.lower() not in (
                            "base", "edition", "games", "applications", "addons"
                        ):
                            label = (
                                segment.replace("-", " ")
                                .replace("_", " ")
                                .strip()
                                .title()
                            )
                            if label and label not in categories:
                                categories.append(label)
    except Exception:
        pass

    release_date: Optional[datetime] = None
    try:
        release_info = metadata.get("releaseInfo", [])
        if release_info and isinstance(release_info, list):
            date_str = release_info[0].get("dateAdded", "")
            if date_str:
                release_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except Exception:
        pass

    is_dlc = game_dict.get("is_dlc", False)

    supports_cloud_saves = False
    try:
        cloud_info = metadata.get("customAttributes", {}).get("CloudSaveFolder")
        supports_cloud_saves = cloud_info is not None
    except Exception:
        pass

    return Game(
        app_name=app_name,
        title=game_dict.get("app_title", str(app_name)),
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


def legendary_installed_to_domain(installed_dict: dict[str, Any]) -> InstalledInfo:
    app_name = AppName(installed_dict.get("app_name", ""))
    platform_str = installed_dict.get("platform", "Windows")
    platform = _PLATFORM_MAP.get(platform_str, Platform.WINDOWS)
    install_size = DiskSize(installed_dict.get("install_size", 0))
    install_path = InstallPath(Path(installed_dict.get("install_path", "/tmp")))

    return InstalledInfo(
        app_name=app_name,
        install_path=install_path,
        version=installed_dict.get("version", ""),
        platform=platform,
        install_size=install_size,
        executable=installed_dict.get("executable", ""),
        can_run_offline=installed_dict.get("can_run_offline", False),
        launch_parameters=installed_dict.get("launch_parameters", ""),
        save_path=installed_dict.get("save_path", "") or "",
    )


def game_info_to_installed(
    app_name: AppName,
    platform: Platform,
    install_path: Path,
    info_dict: dict[str, Any],
) -> InstalledInfo:
    manifest = info_dict.get("manifest", {})
    return InstalledInfo(
        app_name=app_name,
        install_path=InstallPath(install_path),
        version=manifest.get("build_version", ""),
        platform=platform,
        install_size=DiskSize(manifest.get("disk_size", 0)),
        executable=manifest.get("launch_exe", ""),
    )
