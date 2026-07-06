# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Fake ImageCachePort that generates placeholder covers with Cairo.

Covers are rendered on demand and cached to a temp directory so each
game gets a consistent, colourful gradient cover with its title.  No
network access is performed.

Portrait covers (used by GameCard):  480 × 640 px
Wide covers (used by detail views):  920 × 430 px
"""

from __future__ import annotations

import hashlib
import math
import tempfile
from pathlib import Path
from typing import Optional

from mythos.domain.value_objects import AppName
from mythos.ports.output import ImageCachePort

# Dimensions
_W_PORTRAIT = 480
_H_PORTRAIT = 640
_W_WIDE = 920
_H_WIDE = 430

# Temp directory shared across all FakeImageCache instances in the process
_CACHE_DIR: Optional[Path] = None


def _get_cache_dir() -> Path:
    global _CACHE_DIR
    if _CACHE_DIR is None:
        _CACHE_DIR = Path(tempfile.mkdtemp(prefix="mythos-fake-covers-"))
    return _CACHE_DIR


def _hue_from_name(name: str) -> float:
    """Derive a deterministic hue (0–360) from an app name string."""
    digest = hashlib.md5(name.encode()).hexdigest()
    return (int(digest[:4], 16) / 0xFFFF) * 360.0


def _hsl_to_rgb(h: float, s: float, l: float) -> tuple[float, float, float]:
    """Convert HSL (h in degrees, s/l in 0–1) to RGB (0–1 each)."""
    h /= 360.0
    if s == 0:
        return l, l, l

    def hue2rgb(p: float, q: float, t: float) -> float:
        if t < 0:
            t += 1
        if t > 1:
            t -= 1
        if t < 1 / 6:
            return p + (q - p) * 6 * t
        if t < 1 / 2:
            return q
        if t < 2 / 3:
            return p + (q - p) * (2 / 3 - t) * 6
        return p

    q = l * (1 + s) if l < 0.5 else l + s - l * s
    p = 2 * l - q
    return hue2rgb(p, q, h + 1 / 3), hue2rgb(p, q, h), hue2rgb(p, q, h - 1 / 3)


def _render_cover(title: str, app_name: str, width: int, height: int, path: Path) -> None:
    """
    Render a gradient cover image with the game title centred.

    Uses pycairo (already a project dependency via pygobject).
    """
    import cairo  # type: ignore[import]

    hue = _hue_from_name(app_name)
    r1, g1, b1 = _hsl_to_rgb(hue, 0.65, 0.30)
    r2, g2, b2 = _hsl_to_rgb((hue + 40) % 360, 0.55, 0.55)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)

    # Gradient background
    grad = cairo.LinearGradient(0, 0, width * 0.6, height)
    grad.add_color_stop_rgb(0.0, r1, g1, b1)
    grad.add_color_stop_rgb(1.0, r2, g2, b2)
    ctx.rectangle(0, 0, width, height)
    ctx.set_source(grad)
    ctx.fill()

    # Subtle radial highlight in the top-right corner
    radial = cairo.RadialGradient(
        width * 0.75, height * 0.15, 0,
        width * 0.75, height * 0.15, width * 0.6,
    )
    radial.add_color_stop_rgba(0.0, 1, 1, 1, 0.15)
    radial.add_color_stop_rgba(1.0, 1, 1, 1, 0.0)
    ctx.rectangle(0, 0, width, height)
    ctx.set_source(radial)
    ctx.fill()

    # Dark scrim at the bottom for text legibility
    scrim = cairo.LinearGradient(0, height * 0.55, 0, height)
    scrim.add_color_stop_rgba(0.0, 0, 0, 0, 0.0)
    scrim.add_color_stop_rgba(1.0, 0, 0, 0, 0.72)
    ctx.rectangle(0, 0, width, height)
    ctx.set_source(scrim)
    ctx.fill()

    # Title text — wrap into two lines if needed
    ctx.set_source_rgb(1, 1, 1)
    words = title.split()
    line1 = title
    line2 = ""
    if len(title) > 18 and len(words) > 1:
        mid = len(words) // 2
        line1 = " ".join(words[:mid])
        line2 = " ".join(words[mid:])

    font_size = max(14, min(32, width // max(len(line1), 1) * 1.4))
    ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(font_size)

    def draw_line(text: str, y: float) -> None:
        ext = ctx.text_extents(text)
        x = (width - ext.width) / 2 - ext.x_bearing
        # Drop shadow
        ctx.set_source_rgba(0, 0, 0, 0.6)
        ctx.move_to(x + 1, y + 1)
        ctx.show_text(text)
        # Text
        ctx.set_source_rgb(1, 1, 1)
        ctx.move_to(x, y)
        ctx.show_text(text)

    line_h = font_size * 1.25
    if line2:
        draw_line(line1, height - line_h * 2.2)
        draw_line(line2, height - line_h * 1.0)
    else:
        draw_line(line1, height - line_h * 1.4)

    surface.write_to_png(str(path))


class FakeImageCache(ImageCachePort):
    """
    Generates placeholder PNG covers with pycairo on first access,
    then serves them from a process-scoped temp directory.
    """

    def __init__(self) -> None:
        self._cache_dir = _get_cache_dir()
        self._portrait: dict[AppName, Path] = {}
        self._wide: dict[AppName, Path] = {}

    # ---------------------------------------------------------------- #
    # Internal helpers                                                   #
    # ---------------------------------------------------------------- #

    def _portrait_path(self, app_name: AppName) -> Path:
        return self._cache_dir / f"{app_name}_portrait.png"

    def _wide_path(self, app_name: AppName) -> Path:
        return self._cache_dir / f"{app_name}_wide.png"

    def _ensure_portrait(self, app_name: AppName, title: str = "") -> Path:
        path = self._portrait_path(app_name)
        if not path.exists():
            _render_cover(
                title=title or str(app_name),
                app_name=str(app_name),
                width=_W_PORTRAIT,
                height=_H_PORTRAIT,
                path=path,
            )
        return path

    def _ensure_wide(self, app_name: AppName, title: str = "") -> Path:
        path = self._wide_path(app_name)
        if not path.exists():
            _render_cover(
                title=title or str(app_name),
                app_name=str(app_name) + "_wide",
                width=_W_WIDE,
                height=_H_WIDE,
                path=path,
            )
        return path

    # ---------------------------------------------------------------- #
    # Preload helper (called by build_fake before the GTK loop starts)  #
    # ---------------------------------------------------------------- #

    def preload(self, app_name: AppName, title: str) -> None:
        """Pre-render both covers for *app_name* / *title*."""
        self._ensure_portrait(app_name, title)
        self._ensure_wide(app_name, title)

    # ---------------------------------------------------------------- #
    # ImageCachePort                                                     #
    # ---------------------------------------------------------------- #

    def get(self, app_name: AppName) -> Optional[Path]:
        path = self._portrait_path(app_name)
        return path if path.exists() else None

    def store(self, app_name: AppName, image_bytes: bytes) -> Path:
        path = self._portrait_path(app_name)
        path.write_bytes(image_bytes)
        return path

    def fetch_and_cache(self, app_name: AppName, url: str) -> Path:
        # Ignore the URL; generate a placeholder instead.
        title = url  # good enough for rendering
        return self._ensure_portrait(app_name, title)

    def get_wide(self, app_name: AppName) -> Optional[Path]:
        path = self._wide_path(app_name)
        return path if path.exists() else None

    def fetch_and_cache_wide(self, app_name: AppName, url: str) -> Path:
        return self._ensure_wide(app_name, url)
