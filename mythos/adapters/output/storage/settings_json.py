# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""SettingsRepository — persists AppSettings to a JSON file."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

from mythos.config.paths import AppPaths
from mythos.domain.entities import AppSettings
from mythos.domain.exceptions import SettingsError
from mythos.domain.value_objects import WineRunnerType
from mythos.ports.output import SettingsRepository

logger = logging.getLogger(__name__)


class JsonSettingsRepository(SettingsRepository):
    """Reads / writes ``AppSettings`` as a JSON file in the XDG config dir."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or AppPaths.settings_file

    def load(self) -> AppSettings:
        if not self._path.exists():
            logger.debug("No settings file found; using defaults.")
            return AppSettings()

        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            return self._deserialise(raw)
        except Exception as exc:
            raise SettingsError(f"Could not load settings: {exc}") from exc

    def save(self, settings: AppSettings) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._serialise(settings), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug("Settings saved to %s", self._path)
        except Exception as exc:
            raise SettingsError(f"Could not save settings: {exc}") from exc

    # ---------------------------------------------------------------- #
    # Serialisation helpers                                              #
    # ---------------------------------------------------------------- #

    @staticmethod
    def _serialise(settings: AppSettings) -> dict[str, Any]:
        d = asdict(settings)
        # Convert Path objects to strings
        if d.get("default_install_path"):
            d["default_install_path"] = str(d["default_install_path"])
        if d.get("default_wine_executable"):
            d["default_wine_executable"] = str(d["default_wine_executable"])
        # Enum to value
        d["default_wine_runner"] = settings.default_wine_runner.value
        return d

    @staticmethod
    def _deserialise(raw: dict[str, Any]) -> AppSettings:
        install_path = raw.get("default_install_path")
        wine_exe = raw.get("default_wine_executable")
        wine_runner_raw = raw.get("default_wine_runner", WineRunnerType.NONE.value)

        return AppSettings(
            language=raw.get("language", "en"),
            theme=raw.get("theme", "system"),
            default_install_path=Path(install_path) if install_path else None,
            default_wine_runner=WineRunnerType(wine_runner_raw),
            default_wine_executable=Path(wine_exe) if wine_exe else None,
            enable_discord_rpc=raw.get("enable_discord_rpc", False),
            check_updates_on_startup=raw.get("check_updates_on_startup", True),
            minimize_to_tray=raw.get("minimize_to_tray", True),
            show_dlc_in_library=raw.get("show_dlc_in_library", False),
            concurrent_downloads=raw.get("concurrent_downloads", 1),
        )
