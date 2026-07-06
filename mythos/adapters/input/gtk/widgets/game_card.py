# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
GameCard — a clickable tile in the library grid.

Shows cover art (or placeholder) + title + install status badge.
"""

from __future__ import annotations

import logging
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GdkPixbuf, GLib, Gtk  # noqa: E402

from mythos.adapters.input.gtk.view_models import GameViewModel  # noqa: E402
from mythos.domain.value_objects import GameStatus  # noqa: E402

logger = logging.getLogger(__name__)

_CARD_WIDTH = 180
_CARD_HEIGHT = 240
_COVER_HEIGHT = 190


class GameCard(Gtk.FlowBoxChild):
    """
    A 180×240 card with:
      - Cover image (aspect-ratio preserved, cropped to 180×190)
      - Title label (2 lines max)
      - Status pill (installed / running / etc.)
    """

    def __init__(
        self,
        vm: GameViewModel,
        on_click: Callable[[GameViewModel], None],
    ) -> None:
        super().__init__()
        self._vm = vm
        self._on_click = on_click

        self.set_size_request(_CARD_WIDTH, _CARD_HEIGHT)
        self._build()

    def _build(self) -> None:
        overlay = Gtk.Overlay()
        overlay.set_size_request(_CARD_WIDTH, _CARD_HEIGHT)

        # Cover image
        self._cover = Gtk.Picture()
        self._cover.set_size_request(_CARD_WIDTH, _CARD_HEIGHT)
        self._cover.set_content_fit(Gtk.ContentFit.COVER)
        self._cover.add_css_class("card-cover")
        overlay.set_child(self._cover)
        self._load_cover()

        # Bottom overlay: title + status
        bottom = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        bottom.set_valign(Gtk.Align.END)
        bottom.add_css_class("card-bottom")
        bottom.set_margin_start(6)
        bottom.set_margin_end(6)
        bottom.set_margin_bottom(6)

        title = Gtk.Label(label=self._vm.title)
        title.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        title.set_lines(2)
        title.set_wrap(True)
        title.add_css_class("card-title")
        title.set_xalign(0)
        bottom.append(title)

        status_pill = self._make_status_pill()
        bottom.append(status_pill)

        overlay.add_overlay(bottom)

        # Clickable gesture
        click = Gtk.GestureClick()
        click.connect("released", self._on_click_released)
        overlay.add_controller(click)

        self.set_child(overlay)

    def _load_cover(self) -> None:
        """Load cover image from local path or show placeholder."""
        if self._vm.cover_path and self._vm.cover_path.exists():
            try:
                self._cover.set_filename(str(self._vm.cover_path))
                return
            except Exception as exc:
                logger.debug("Could not load cover %s: %s", self._vm.cover_path, exc)

        # Placeholder
        self._cover.set_icon_name("application-x-executable")

    def _make_status_pill(self) -> Gtk.Label:
        label = Gtk.Label(label=self._vm.status_label)
        label.add_css_class("status-pill")
        label.set_xalign(0)

        status_css = {
            GameStatus.INSTALLED: "status-installed",
            GameStatus.RUNNING: "status-running",
            GameStatus.INSTALLING: "status-installing",
            GameStatus.QUEUED: "status-queued",
            GameStatus.ERROR: "status-error",
        }
        css_class = status_css.get(self._vm.status, "status-not-installed")
        label.add_css_class(css_class)
        return label

    def _on_click_released(
        self, gesture: Gtk.GestureClick, n_press: int, x: float, y: float
    ) -> None:
        self._on_click(self._vm)
