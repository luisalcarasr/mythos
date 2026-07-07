# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Domain value objects — immutable, self-validating, equality-by-value.

All classes in this module are frozen dataclasses with no external deps.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path


# ------------------------------------------------------------------ #
# Enumerations                                                         #
# ------------------------------------------------------------------ #


class Platform(str, Enum):
    """Target platform for a game installation."""
    WINDOWS = "Windows"
    MAC = "Mac"
    LINUX = "Linux"

    @staticmethod
    def current() -> Platform:
        if sys.platform == "darwin":
            return Platform.MAC
        if sys.platform.startswith("linux"):
            return Platform.LINUX
        return Platform.WINDOWS


class GameStatus(Enum):
    """Lifecycle status of a game in the local library."""
    NOT_INSTALLED = auto()
    INSTALLED = auto()
    INSTALLING = auto()
    UPDATING = auto()
    REPAIRING = auto()
    UNINSTALLING = auto()
    QUEUED = auto()
    RUNNING = auto()
    ERROR = auto()


class SyncDirection(Enum):
    """Direction of a cloud-save synchronisation."""
    UPLOAD = auto()
    DOWNLOAD = auto()
    BOTH = auto()


class WineRunnerType(str, Enum):
    """Type of Wine/Proton runner in use."""
    WINE = "wine"
    PROTON = "proton"
    PROTON_GE = "proton-ge"
    CROSSOVER = "crossover"
    NONE = "none"


# ------------------------------------------------------------------ #
# Value objects                                                        #
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class AppName:
    """
    Unique Epic Games application name (e.g. ``Sugar``).

    Epic App Names are non-empty ASCII strings without whitespace.
    """
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("AppName must not be empty.")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class InstallPath:
    """Absolute path to the game installation directory."""
    value: Path

    def __post_init__(self) -> None:
        if not isinstance(self.value, Path):
            object.__setattr__(self, "value", Path(self.value))

    def __str__(self) -> str:
        return str(self.value)

    @property
    def exists(self) -> bool:
        return self.value.exists()


@dataclass(frozen=True)
class DiskSize:
    """A non-negative disk size expressed in bytes."""
    bytes_: int

    def __post_init__(self) -> None:
        if self.bytes_ < 0:
            raise ValueError("DiskSize cannot be negative.")

    @staticmethod
    def from_mib(mib: float) -> DiskSize:
        return DiskSize(int(mib * 1024 ** 2))

    @staticmethod
    def from_gib(gib: float) -> DiskSize:
        return DiskSize(int(gib * 1024 ** 3))

    def to_gib(self) -> float:
        return self.bytes_ / (1024 ** 3)

    def human_readable(self) -> str:
        b = self.bytes_
        for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
            if b < 1024:
                return f"{b:.1f} {unit}"
            b /= 1024  # type: ignore[assignment]
        return f"{b:.1f} PiB"  # type: ignore[unreachable]


@dataclass(frozen=True)
class Progress:
    """
    Represents the progress of a long-running operation (0.0 – 1.0).

    Attributes
    ----------
    fraction:
        Completion fraction in the range [0.0, 1.0].
    downloaded_bytes:
        Total bytes downloaded so far.
    total_bytes:
        Total bytes expected.
    speed_bps:
        Current transfer speed in bytes per second.
    eta_seconds:
        Estimated seconds until completion.
    """
    fraction: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: int = 0
    speed_bps: float = 0.0
    eta_seconds: float = 0.0

    def __post_init__(self) -> None:
        if not (0.0 <= self.fraction <= 1.0):
            raise ValueError(f"Progress fraction must be in [0, 1], got {self.fraction}")

    @property
    def is_complete(self) -> bool:
        return self.fraction >= 1.0

    @property
    def percent(self) -> int:
        return int(self.fraction * 100)

    def speed_human(self) -> str:
        s = self.speed_bps
        for unit in ("B/s", "KiB/s", "MiB/s", "GiB/s"):
            if s < 1024:
                return f"{s:.1f} {unit}"
            s /= 1024  # type: ignore[assignment]
        return f"{s:.1f} TiB/s"  # type: ignore[unreachable]

    @staticmethod
    def _bytes_human(b: int) -> str:
        v: float = float(b)
        for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
            if v < 1024:
                return f"{v:.1f} {unit}"
            v /= 1024
        return f"{v:.1f} PiB"

    @property
    def downloaded_human(self) -> str:
        return self._bytes_human(self.downloaded_bytes)

    @property
    def total_human(self) -> str:
        return self._bytes_human(self.total_bytes)

    @property
    def eta_human(self) -> str:
        if self.eta_seconds <= 0 or self.fraction >= 1.0:
            return "—"
        secs = int(self.eta_seconds)
        h, rem = divmod(secs, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h}h {m}m"
        if m:
            return f"{m}m {s}s"
        return f"{s}s"


@dataclass(frozen=True)
class LaunchOptions:
    """Per-game launch configuration supplied by the user."""
    wine_runner: WineRunnerType = WineRunnerType.NONE
    wine_executable: Path | None = None
    extra_env: dict[str, str] = None  # type: ignore[assignment]
    wrapper_command: str = ""
    offline: bool = False
    proton_version: str = ""  # e.g. "GE-Proton9-20" or "9.0-4"

    def __post_init__(self) -> None:
        # Ensure extra_env is never None
        if self.extra_env is None:
            object.__setattr__(self, "extra_env", {})


@dataclass(frozen=True)
class ProtonRelease:
    """
    A single Proton or Proton-GE build available for download or already
    installed locally.

    Attributes
    ----------
    name:
        Human-readable label, e.g. ``"GE-Proton9-20"`` or ``"Proton 9.0-4"``.
    runner_type:
        ``WineRunnerType.PROTON`` or ``WineRunnerType.PROTON_GE``.
    version:
        Version tag used for sorting and identification (same as *name*
        for Proton-GE; ``"9.0-4"`` for upstream Proton).
    download_url:
        Direct URL to the release tarball.  Empty when the release is
        already installed (no download needed).
    installed:
        ``True`` when the build has been extracted to *install_path*.
    install_path:
        Absolute path to the extracted runtime directory, or ``None``
        when not yet installed.
    size_bytes:
        Download size in bytes (0 when unknown).
    """
    name: str
    runner_type: WineRunnerType
    version: str
    download_url: str = ""
    installed: bool = False
    install_path: Path | None = None
    size_bytes: int = 0

    @property
    def label(self) -> str:
        """Short UI label, e.g. 'Proton-GE — GE-Proton9-20'."""
        prefix = "Proton-GE" if self.runner_type == WineRunnerType.PROTON_GE else "Proton"
        return f"{prefix} — {self.version}"
