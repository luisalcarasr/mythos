# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""ImageCachePort — stores game covers on disk."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Optional

import requests

from mythos.config.paths import AppPaths
from mythos.domain.value_objects import AppName
from mythos.ports.output import ImageCachePort

logger = logging.getLogger(__name__)


class DiskImageCache(ImageCachePort):
    """Caches game cover images under ``~/.cache/mythos/covers/``."""

    EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")

    def __init__(self, cache_dir: Path | None = None) -> None:
        self._dir = cache_dir or AppPaths.image_cache_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def get(self, app_name: AppName) -> Optional[Path]:
        stem = self._stem(app_name)
        for ext in self.EXTENSIONS:
            candidate = self._dir / (stem + ext)
            if candidate.exists():
                return candidate
        return None

    def store(self, app_name: AppName, image_bytes: bytes) -> Path:
        ext = self._detect_ext(image_bytes)
        path = self._dir / (self._stem(app_name) + ext)
        path.write_bytes(image_bytes)
        logger.debug("Cached cover for %s → %s", app_name, path)
        return path

    def fetch_and_cache(self, app_name: AppName, url: str) -> Path:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return self.store(app_name, response.content)

    # ---------------------------------------------------------------- #
    # Wide (horizontal) covers                                           #
    # ---------------------------------------------------------------- #

    def get_wide(self, app_name: AppName) -> Optional[Path]:
        stem = self._stem(app_name) + "_wide"
        for ext in self.EXTENSIONS:
            candidate = self._dir / (stem + ext)
            if candidate.exists():
                return candidate
        return None

    def fetch_and_cache_wide(self, app_name: AppName, url: str) -> Path:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        ext = self._detect_ext(response.content)
        path = self._dir / (self._stem(app_name) + "_wide" + ext)
        path.write_bytes(response.content)
        logger.debug("Cached wide cover for %s → %s", app_name, path)
        return path

    # ---------------------------------------------------------------- #
    # Helpers                                                            #
    # ---------------------------------------------------------------- #

    @staticmethod
    def _stem(app_name: AppName) -> str:
        """Return a filesystem-safe filename stem for *app_name*."""
        return "".join(c if c.isalnum() or c in "-_" else "_" for c in str(app_name))

    @staticmethod
    def _detect_ext(data: bytes) -> str:
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return ".png"
        if data[:3] == b"\xff\xd8\xff":
            return ".jpg"
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return ".webp"
        return ".jpg"  # default
