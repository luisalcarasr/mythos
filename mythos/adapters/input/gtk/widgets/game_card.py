# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
GameCard — a clickable tile in the library grid.

Layout (top→bottom):
  1. Image area — CONTAIN (full image visible) on dark bg
  2. Footer — title, status, action button + settings icon

Card aspect ratio is 9:16 (vertical), computed from _CARD_WIDTH.
"""

from __future__ import annotations

import logging
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from mythos.adapters.input.gtk.view_models import GameViewModel  # noqa: E402
from mythos.domain.value_objects import GameStatus  # noqa: E402

logger = logging.getLogger(__name__)

_CARD_WIDTH = 220
_FOOTER_HEIGHT = 60
_CARD_HEIGHT = int(_CARD_WIDTH * 16 / 9)
_IMAGE_HEIGHT = _CARD_HEIGHT - _FOOTER_HEIGHT


class GameCard(Gtk.FlowBoxChild):
    """
    A fixed-width card at 9:16 vertical ratio (height = width × 16/9).

    ┌─────────────────┬──┐
    │                 │⚙ │  Image area (COVER) + settings top-right
    │                 │  │
    │                 │  │
    ├────────────────────┤
    │ Title              │  Footer
    │ [Install]          │
    └────────────────────┘
    """

    def __init__(
        self,
        vm: GameViewModel,
        on_detail: Callable[[GameViewModel], None],
        on_install: Callable[[GameViewModel], None],
        on_launch: Callable[[GameViewModel], None],
    ) -> None:
        super().__init__()
        self._vm = vm
        self._on_detail = on_detail
        self._on_install = on_install
        self._on_launch = on_launch

        self.set_size_request(_CARD_WIDTH, _CARD_HEIGHT)
        self.set_hexpand(False)
        self.set_vexpand(False)
        self._build()

    # ---------------------------------------------------------------- #
    # UI construction                                                    #
    # ---------------------------------------------------------------- #

    def _build(self) -> None:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_size_request(_CARD_WIDTH, _CARD_HEIGHT)
        outer.add_css_class("card-box")
        outer.set_hexpand(False)

        # -- Image area + settings overlay --------------------------------
        img_overlay = Gtk.Overlay()
        img_overlay.set_size_request(_CARD_WIDTH, _IMAGE_HEIGHT)

        self._cover = Gtk.Picture()
        self._cover.set_size_request(_CARD_WIDTH, _IMAGE_HEIGHT)
        self._cover.set_content_fit(Gtk.ContentFit.COVER)
        self._cover.add_css_class("card-cover")

        img_click = Gtk.GestureClick()
        img_click.connect("released", lambda *_: self._on_detail(self._vm))
        self._cover.add_controller(img_click)

        img_overlay.set_child(self._cover)

        settings_btn = Gtk.Button(icon_name="emblem-system-symbolic")
        settings_btn.add_css_class("flat")
        settings_btn.add_css_class("circular")
        settings_btn.add_css_class("card-settings")
        settings_btn.set_tooltip_text("Game details")
        settings_btn.set_halign(Gtk.Align.END)
        settings_btn.set_valign(Gtk.Align.START)
        settings_btn.set_margin_top(6)
        settings_btn.set_margin_end(6)
        settings_btn.connect("clicked", lambda *_: self._on_detail(self._vm))
        img_overlay.add_overlay(settings_btn)

        motion = Gtk.EventControllerMotion()
        motion.connect("enter", lambda *_: settings_btn.add_css_class("card-settings-visible"))
        motion.connect("leave", lambda *_: settings_btn.remove_css_class("card-settings-visible"))
        outer.add_controller(motion)

        outer.append(img_overlay)

        # -- Footer -------------------------------------------------------
        footer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        footer.set_size_request(_CARD_WIDTH, _FOOTER_HEIGHT)
        footer.add_css_class("card-footer")

        title = Gtk.Label(label=self._vm.title)
        title.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        title.set_lines(2)
        title.set_wrap(True)
        title.set_xalign(0)
        title.set_hexpand(True)
        title.add_css_class("card-title")
        footer.append(title)

        self._action_btn = Gtk.Button()
        self._action_btn.add_css_class("card-action-button")
        self._action_btn.set_hexpand(True)
        self._action_btn.set_margin_top(4)
        self._update_action_button()
        footer.append(self._action_btn)
        outer.append(footer)

        self._load_cover()
        self.set_child(outer)

    # ---------------------------------------------------------------- #
    # Cover image                                                        #
    # ---------------------------------------------------------------- #

    def _load_cover(self) -> None:
        if self._vm.cover_path and self._vm.cover_path.exists():
            try:
                self._cover.set_filename(str(self._vm.cover_path))
                return
            except Exception as exc:
                logger.debug("Could not load cover %s: %s", self._vm.cover_path, exc)

    # ---------------------------------------------------------------- #
    # Action button                                                      #
    # ---------------------------------------------------------------- #

    def _update_action_button(self) -> None:
        if self._vm.status == GameStatus.NOT_INSTALLED:
            self._action_btn.set_label("Install")
            self._action_btn.set_visible(self._vm.can_install)

        elif self._vm.status == GameStatus.INSTALLED:
            if self._vm.needs_update:
                self._action_btn.set_label("Update")
            else:
                self._action_btn.set_label("Play")

        elif self._vm.status == GameStatus.RUNNING:
            self._action_btn.set_label("Running")
            self._action_btn.set_sensitive(False)

        elif self._vm.status in (GameStatus.INSTALLING, GameStatus.QUEUED):
            self._action_btn.set_label("Installing\u2026")
            self._action_btn.set_sensitive(False)

        elif self._vm.status == GameStatus.ERROR:
            self._action_btn.set_label("Retry")

        else:
            self._action_btn.set_visible(False)

        self._action_btn.connect("clicked", self._on_action_clicked)

    def _on_action_clicked(self, _btn: Gtk.Button) -> None:
        status = self._vm.status
        if status == GameStatus.NOT_INSTALLED:
            self._on_install(self._vm)
        elif status == GameStatus.INSTALLED:
            if self._vm.needs_update:
                self._on_install(self._vm)
            else:
                self._on_launch(self._vm)
        elif status == GameStatus.ERROR:
            self._on_install(self._vm)
