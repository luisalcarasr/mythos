# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Domain exceptions — no external dependencies.

All exceptions inherit from ``MythosError`` so callers can catch the
whole hierarchy with a single ``except MythosError``.
"""

from __future__ import annotations


class MythosError(Exception):
    """Base class for all Mythos domain exceptions."""


# ------------------------------------------------------------------ #
# Authentication                                                       #
# ------------------------------------------------------------------ #


class NotLoggedInError(MythosError):
    """Raised when an operation requires an active Epic session."""
    def __init__(self) -> None:
        super().__init__("No active Epic Games session. Please log in first.")


class AuthenticationError(MythosError):
    """Raised when login or token refresh fails."""


class SessionExpiredError(AuthenticationError):
    """Raised when the stored session token has expired."""
    def __init__(self) -> None:
        super().__init__("Epic Games session expired. Please log in again.")


# ------------------------------------------------------------------ #
# Library / game                                                       #
# ------------------------------------------------------------------ #


class GameNotFoundError(MythosError):
    """Raised when a game cannot be found by app name."""
    def __init__(self, app_name: str) -> None:
        super().__init__(f"Game not found: {app_name!r}")
        self.app_name = app_name


class GameAlreadyInstalledError(MythosError):
    """Raised when attempting to install a game that is already installed."""
    def __init__(self, app_name: str) -> None:
        super().__init__(f"Game {app_name!r} is already installed.")
        self.app_name = app_name


class GameNotInstalledError(MythosError):
    """Raised when an operation requires the game to be installed."""
    def __init__(self, app_name: str) -> None:
        super().__init__(f"Game {app_name!r} is not installed.")
        self.app_name = app_name


class GameAlreadyRunningError(MythosError):
    """Raised when a launch is attempted for a game already running."""
    def __init__(self, app_name: str) -> None:
        super().__init__(f"Game {app_name!r} is already running.")
        self.app_name = app_name


# ------------------------------------------------------------------ #
# Installation / update                                                #
# ------------------------------------------------------------------ #


class InstallError(MythosError):
    """Raised when an installation or update operation fails."""


class DiskSpaceError(InstallError):
    """Raised when there is not enough free disk space for an install."""
    def __init__(self, required_bytes: int, available_bytes: int) -> None:
        super().__init__(
            f"Not enough disk space: need {required_bytes} bytes, "
            f"only {available_bytes} available."
        )
        self.required_bytes = required_bytes
        self.available_bytes = available_bytes


class DownloadError(InstallError):
    """Raised when a chunk download fails irrecoverably."""


# ------------------------------------------------------------------ #
# Cloud saves                                                          #
# ------------------------------------------------------------------ #


class CloudSaveError(MythosError):
    """Raised when a cloud save sync operation fails."""


# ------------------------------------------------------------------ #
# Wine / runtime                                                       #
# ------------------------------------------------------------------ #


class WineRuntimeError(MythosError):
    """Raised when the selected Wine runtime cannot be used."""


# ------------------------------------------------------------------ #
# Settings                                                             #
# ------------------------------------------------------------------ #


class SettingsError(MythosError):
    """Raised when settings cannot be loaded or persisted."""
