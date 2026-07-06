# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Domain services — complex business logic that does not belong to a
single entity.

Domain services are pure functions or stateless classes.
They must not import anything outside of the ``domain`` package.
"""

from __future__ import annotations

import shlex
import sys
from pathlib import Path
from typing import Optional

from mythos.domain.entities import Game, InstalledInfo, AppSettings
from mythos.domain.value_objects import (
    AppName,
    DiskSize,
    LaunchOptions,
    Platform,
    WineRunnerType,
)
from mythos.domain.exceptions import (
    DiskSpaceError,
    GameNotInstalledError,
    WineRuntimeError,
)


class InstallPlanningService:
    """
    Validates that a game can be installed given current disk conditions.

    This service intentionally does NOT perform any I/O; the caller
    supplies the available space as a domain value.
    """

    @staticmethod
    def validate_space(required: DiskSize, available: DiskSize) -> None:
        """
        Raise ``DiskSpaceError`` when *available* is less than *required*.

        A 10 % safety margin is added on top of the raw requirement.
        """
        needed = DiskSize(int(required.bytes_ * 1.10))
        if available.bytes_ < needed.bytes_:
            raise DiskSpaceError(
                required_bytes=needed.bytes_,
                available_bytes=available.bytes_,
            )

    @staticmethod
    def resolve_install_path(
        preferred: Optional[Path],
        settings: AppSettings,
    ) -> Path:
        """
        Return the installation path to use.

        Priority:
          1. Explicitly supplied *preferred* path.
          2. ``AppSettings.default_install_path``.
          3. ``~/Games`` as last resort.
        """
        if preferred and preferred != Path():
            return preferred
        if settings.default_install_path:
            return settings.default_install_path
        return Path.home() / "Games"


class LaunchCommandBuilder:
    """
    Builds the OS-level command list required to launch a game.

    Applies Wine / Proton / Crossover wrappers when the game's platform
    does not match the host OS.  The result is a plain list of strings
    suitable for ``subprocess.Popen``.
    """

    def build(
        self,
        game: Game,
        extra_options: Optional[LaunchOptions] = None,
    ) -> list[str]:
        """
        Return the command list for launching *game*.

        Parameters
        ----------
        game:
            The game to launch (must be installed).
        extra_options:
            Override ``InstalledInfo.launch_options`` if provided.

        Raises
        ------
        GameNotInstalledError
            If the game has no ``InstalledInfo``.
        WineRuntimeError
            If a Wine runner is required but not configured.
        """
        if game.installed_info is None:
            raise GameNotInstalledError(str(game.app_name))

        info: InstalledInfo = game.installed_info
        opts: LaunchOptions = extra_options or info.launch_options
        host = Platform.current()

        cmd: list[str] = []

        # Wrapper (e.g. gamemoderun, mangohud)
        if opts.wrapper_command:
            cmd.extend(shlex.split(opts.wrapper_command))

        # Wine / Proton when game is a Windows game on Linux/macOS
        if info.platform == Platform.WINDOWS and host != Platform.WINDOWS:
            cmd.extend(self._wine_prefix(opts, host))

        # Game executable
        exe = info.install_path.value / info.executable
        cmd.append(str(exe))

        return cmd

    @staticmethod
    def _wine_prefix(opts: LaunchOptions, host: Platform) -> list[str]:
        runner = opts.wine_runner
        exe = opts.wine_executable

        if runner == WineRunnerType.NONE:
            # Try system wine as fallback
            import shutil
            system_wine = shutil.which("wine")
            if system_wine:
                return [system_wine]
            raise WineRuntimeError(
                "Game requires Wine but no Wine runner is configured."
            )

        if runner == WineRunnerType.CROSSOVER:
            # CrossOver on macOS uses a dedicated binary
            cxrun = Path("/Applications/CrossOver.app/Contents/SharedSupport"
                         "/CrossOver/bin/wine")
            if exe and exe.exists():
                return [str(exe)]
            if cxrun.exists():
                return [str(cxrun)]
            raise WineRuntimeError("CrossOver not found.")

        if runner in (WineRunnerType.WINE, WineRunnerType.PROTON):
            if exe and exe.exists():
                return [str(exe)]
            raise WineRuntimeError(
                f"Wine runner is set to {runner.value!r} but no executable path is configured."
            )

        raise WineRuntimeError(f"Unknown wine runner: {runner}")
