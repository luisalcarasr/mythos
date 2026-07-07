from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

from mythos.adapters.output.legendary.cli_wrapper import LegendaryCliWrapper
from mythos.adapters.output.legendary.lock_manager import can_clear_lock, clear_lock
from mythos.adapters.output.legendary.mappers import (
    game_info_to_installed,
    legendary_game_to_domain,
    legendary_installed_to_domain,
)
from mythos.domain.entities import Game, InstalledInfo
from mythos.domain.exceptions import GameNotFoundError, InstallError
from mythos.domain.value_objects import (
    AppName,
    DiskSize,
    InstallPath,
    Platform,
    Progress,
)
from mythos.ports.output import EpicStorePort

logger = logging.getLogger(__name__)


class LegendaryEpicStore(EpicStorePort):
    def __init__(self, cli: Optional[LegendaryCliWrapper] = None) -> None:
        self._cli = cli or LegendaryCliWrapper()

    def list_games(self, include_dlc: bool = False) -> list[Game]:
        try:
            raw = self._cli.run_json(["list", "--json", "--platform", "Windows"])
            games = [legendary_game_to_domain(g) for g in raw]
            if not include_dlc:
                games = [g for g in games if not g.is_dlc]
            return games
        except Exception as exc:
            logger.error("list_games failed: %s", exc)
            return []

    def get_game(self, app_name: AppName) -> Optional[Game]:
        try:
            raw = self._cli.run_json(
                ["info", str(app_name), "--json", "--platform", "Windows"]
            )
            game_data = raw.get("game", {})
            if not game_data:
                return None
            # Build a synthetic dict from info output to reuse the mapper
            metadata = _load_game_metadata(str(app_name))
            synthetic = {
                "app_name": game_data.get("app_name", str(app_name)),
                "app_title": game_data.get("title", str(app_name)),
                "is_dlc": game_data.get("is_dlc", False),
                "metadata": metadata if metadata else {},
                "asset_infos": {},
            }
            return legendary_game_to_domain(synthetic)
        except Exception as exc:
            logger.error("get_game(%s) failed: %s", app_name, exc)
            return None

    def get_installed(self) -> list[InstalledInfo]:
        try:
            raw = self._cli.run_json(["list-installed", "--json"])
            return [legendary_installed_to_domain(g) for g in raw]
        except Exception as exc:
            logger.error("get_installed failed: %s", exc)
            return []

    def get_download_size(self, app_name: AppName, platform: Platform) -> DiskSize:
        try:
            raw = self._cli.run_json(
                ["info", str(app_name), "--json", "--platform", platform.value]
            )
            manifest = raw.get("manifest", {})
            return DiskSize(manifest.get("download_size", 0))
        except Exception:
            return DiskSize(0)

    def get_install_size(self, app_name: AppName, platform: Platform) -> DiskSize:
        try:
            raw = self._cli.run_json(
                ["info", str(app_name), "--json", "--platform", platform.value]
            )
            manifest = raw.get("manifest", {})
            return DiskSize(manifest.get("disk_size", 0))
        except Exception:
            return DiskSize(0)

    def _ensure_no_orphan_lock(self) -> None:
        if can_clear_lock():
            clear_lock()

    def install_game(
        self,
        app_name: AppName,
        install_path: Path,
        platform: Platform,
        on_progress: Callable[[Progress], None],
    ) -> InstalledInfo:
        self._ensure_no_orphan_lock()
        try:
            self._cli.run_and_check(
                [
                    "install",
                    str(app_name),
                    "--base-path",
                    str(install_path),
                    "--platform",
                    platform.value,
                    "-y",
                ],
                on_progress=on_progress,
            )

            installed = self._get_installed_game(str(app_name))
            if installed:
                return installed

            raw = self._cli.run_json(
                ["info", str(app_name), "--json", "--platform", platform.value]
            )
            return game_info_to_installed(app_name, platform, install_path, raw)
        except Exception as exc:
            raise InstallError(f"Install failed for {app_name}: {exc}") from exc

    def update_game(
        self,
        app_name: AppName,
        on_progress: Callable[[Progress], None],
    ) -> InstalledInfo:
        self._ensure_no_orphan_lock()
        installed = self._get_installed_game(str(app_name))
        if not installed:
            raise InstallError(f"{app_name} is not installed")
        try:
            self._cli.run_and_check(
                ["update", str(app_name), "-y"],
                on_progress=on_progress,
            )
            updated = self._get_installed_game(str(app_name))
            return updated or installed
        except Exception as exc:
            raise InstallError(f"Update failed for {app_name}: {exc}") from exc

    def repair_game(
        self,
        app_name: AppName,
        on_progress: Callable[[Progress], None],
    ) -> InstalledInfo:
        self._ensure_no_orphan_lock()
        installed = self._get_installed_game(str(app_name))
        if not installed:
            raise InstallError(f"{app_name} is not installed")
        try:
            self._cli.run_and_check(
                ["install", str(app_name), "--repair", "-y"],
                on_progress=on_progress,
            )
            repaired = self._get_installed_game(str(app_name))
            return repaired or installed
        except Exception as exc:
            raise InstallError(f"Repair failed for {app_name}: {exc}") from exc

    def move_game(self, app_name: AppName, new_path: Path) -> InstalledInfo:
        self._ensure_no_orphan_lock()
        try:
            self._cli.run(["move", str(app_name), str(new_path), "-y"])
            moved = self._get_installed_game(str(app_name))
            if moved:
                return moved
            raise InstallError(f"Move failed for {app_name}")
        except Exception as exc:
            raise InstallError(f"Move failed for {app_name}: {exc}") from exc

    def uninstall_game(self, app_name: AppName) -> None:
        self._ensure_no_orphan_lock()
        try:
            self._cli.run(["uninstall", str(app_name), "-y"])
        except Exception as exc:
            raise InstallError(f"Uninstall failed for {app_name}: {exc}") from exc

    def _get_installed_game(self, app_name: str) -> Optional[InstalledInfo]:
        try:
            raw = self._cli.run_json(["list-installed", "--json"])
            for entry in raw:
                if entry.get("app_name") == app_name:
                    return legendary_installed_to_domain(entry)
            return None
        except Exception:
            return None


def _load_game_metadata(app_name: str) -> Optional[dict]:
    try:
        import json
        import os
        from pathlib import Path

        meta_dir = (
            Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
            / "legendary"
            / "metadata"
        )
        meta_file = meta_dir / f"{app_name}.json"
        if meta_file.exists():
            return json.loads(meta_file.read_text())
    except Exception:
        pass
    return None
