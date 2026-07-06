# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
MythosApplication — the GTK4 / Adwaita driving adapter.

Responsibilities:
  - Initialise gi typelibs.
  - Create the Adw.Application instance.
  - Wire the main window to the dependency container.
  - Handle app-level signals (activate, shutdown).
"""

from __future__ import annotations

import logging
import sys
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, GLib, Gtk  # noqa: E402

from mythos.config.container import Container  # noqa: E402
from mythos import __app_id__, __version__  # noqa: E402

logger = logging.getLogger(__name__)


class MythosApplication(Adw.Application):
    """
    Top-level GTK4/Adwaita application.

    The ``container`` holds all use-case instances; the window reads
    from it to get the dependencies it needs.
    """

    def __init__(self, container: Container) -> None:
        super().__init__(application_id=__app_id__)
        self._container = container
        self.connect("activate", self._on_activate)
        self.connect("shutdown", self._on_shutdown)
        self._load_stylesheet()

    # ---------------------------------------------------------------- #
    # GTK signals                                                        #
    # ---------------------------------------------------------------- #

    def _on_activate(self, app: "MythosApplication") -> None:
        from mythos.adapters.input.gtk.window import MythosWindow

        win = self.get_active_window()
        if win is None:
            win = MythosWindow(application=self, container=self._container)

        win.present()
        logger.info("Mythos %s started.", __version__)

    def _on_shutdown(self, app: "MythosApplication") -> None:
        logger.info("Mythos shutting down.")
        main_thread = threading.main_thread()
        for t in threading.enumerate():
            if t is not main_thread and t.is_alive():
                logger.debug("Waiting for thread %s...", t.name)
                t.join(timeout=2.0)

    def _load_stylesheet(self) -> None:
        from pathlib import Path

        css_provider = Gtk.CssProvider()
        css_path = Path(__file__).parent / "resources" / "style.css"
        if not css_path.exists():
            logger.warning("Stylesheet not found: %s", css_path)
            return
        css_provider.load_from_path(str(css_path))
        display = Gdk.Display.get_default()
        if display is None:
            logger.warning("No display available; skipping stylesheet.")
            return
        Gtk.StyleContext.add_provider_for_display(
            display,
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
        logger.debug("Stylesheet loaded: %s", css_path)
