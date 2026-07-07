# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
MythosWindow — main application window.

Layout:
  Adw.ApplicationWindow
  └── Adw.ToolbarView
      ├── Adw.HeaderBar (top)
      │   ├── [start] refresh button
      │   └── [end]   info/settings button → Adw.PreferencesDialog
      └── LibraryView (single page with inline download progress)

Settings are no longer a navigation tab.  They open as a modal
``Adw.PreferencesDialog`` from the info button (⋮ / gear) in the
header bar — following the GNOME HIG pattern for app preferences.
"""

from __future__ import annotations

import logging

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from mythos.config.container import Container  # noqa: E402
from mythos.domain.events import UserLoggedOut  # noqa: E402

logger = logging.getLogger(__name__)


class MythosWindow(Adw.ApplicationWindow):
    def __init__(self, application: Adw.Application, container: Container) -> None:
        super().__init__(application=application)
        self._c = container

        self.set_title("Mythos")
        self.set_default_size(1280, 780)
        self.set_size_request(900, 600)

        self.connect("close-request", self._on_close_request)

        self._build_ui()
        self._connect_events()
        self._check_session()

    # ---------------------------------------------------------------- #
    # UI construction                                                    #
    # ---------------------------------------------------------------- #

    def _build_ui(self) -> None:
        # Root layout
        toolbar_view = Adw.ToolbarView()
        self.set_content(toolbar_view)

        # Header bar
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        # [start] Refresh button
        self._btn_refresh = Gtk.Button(icon_name="view-refresh-symbolic")
        self._btn_refresh.set_tooltip_text("Refresh library")
        self._btn_refresh.connect("clicked", self._on_refresh_clicked)
        header.pack_start(self._btn_refresh)

        # [end] Info / settings button
        self._btn_info = Gtk.Button(icon_name="preferences-system-symbolic")
        self._btn_info.set_tooltip_text("Preferences")
        self._btn_info.connect("clicked", self._on_info_clicked)
        header.pack_end(self._btn_info)

        # ---- Content ------------------------------------------------ #
        from mythos.adapters.input.gtk.views.library_view import LibraryView
        from mythos.adapters.input.gtk.views.settings_view import SettingsView
        from mythos.adapters.input.gtk.views.login_view import LoginView

        self._library_view = LibraryView(container=self._c, window=self)
        toolbar_view.set_content(self._library_view)

        # Settings open as a modal Adw.PreferencesDialog
        self._settings_view = SettingsView(container=self._c)
        self._prefs_dialog = Adw.PreferencesDialog()
        self._prefs_dialog.add(self._settings_view)

        # Login uses a separate overlay
        self._login_view = LoginView(container=self._c, on_login=self._on_login)
        self._login_overlay = Adw.Dialog()
        self._login_overlay.set_title("Sign in to Epic Games")
        self._login_overlay.set_content_width(800)
        self._login_overlay.set_content_height(600)
        self._login_overlay.set_child(self._login_view)

    # ---------------------------------------------------------------- #
    # Session handling                                                   #
    # ---------------------------------------------------------------- #

    def _check_session(self) -> None:
        session = self._c.get_session_use_case.execute()
        if session:
            logger.info("Existing session found for %s.", session.get("display_name"))
            GLib.idle_add(self._library_view.refresh)
        else:
            logger.info("No session — showing login dialog.")
            GLib.idle_add(self._show_login)

    def _show_login(self) -> bool:
        self._login_overlay.present(self)
        return GLib.SOURCE_REMOVE

    def _on_login(self, session: dict) -> None:
        """Called by LoginView when the user successfully authenticates."""
        self._login_overlay.close()
        self._library_view.refresh()

    # ---------------------------------------------------------------- #
    # Event bus subscriptions                                           #
    # ---------------------------------------------------------------- #

    def _connect_events(self) -> None:
        bus = self._c.event_bus
        bus.subscribe(UserLoggedOut, self._on_logged_out)

    def _on_logged_out(self, event: UserLoggedOut) -> None:
        self._show_login()

    # ---------------------------------------------------------------- #
    # Toolbar actions                                                    #
    # ---------------------------------------------------------------- #

    def _on_refresh_clicked(self, btn: Gtk.Button) -> None:
        self._library_view.refresh()

    def _on_info_clicked(self, btn: Gtk.Button) -> None:
        self._prefs_dialog.present(self)

    def _on_close_request(self, window: object) -> bool:
        logger.info("Window close requested — quitting application.")
        self.get_application().quit()
        return False  # allow default destruction

    # ---------------------------------------------------------------- #
