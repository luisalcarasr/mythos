# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
MythosWindow — main application window.

Layout:
  Adw.ApplicationWindow
  └── Adw.ToolbarView
      ├── Adw.HeaderBar (top)
      └── Gtk.Stack (content)
          ├── "login"    → LoginView
          ├── "library"  → LibraryView
          ├── "downloads"→ DownloadsView
          └── "settings" → SettingsView

Navigation between views is done via ``switch_view(name)``.
"""

from __future__ import annotations

import logging

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from mythos.config.container import Container  # noqa: E402
from mythos.domain.events import UserLoggedIn, UserLoggedOut  # noqa: E402

logger = logging.getLogger(__name__)

_ICON_LIBRARY = "view-grid-symbolic"
_ICON_DOWNLOADS = "folder-download-symbolic"
_ICON_SETTINGS = "preferences-system-symbolic"


class MythosWindow(Adw.ApplicationWindow):
    def __init__(self, application: Adw.Application, container: Container) -> None:
        super().__init__(application=application)
        self._c = container

        self.set_title("Mythos")
        self.set_default_size(1280, 780)
        self.set_size_request(900, 600)

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
        self._header = Adw.HeaderBar()
        toolbar_view.add_top_bar(self._header)

        # View switcher (top, library / downloads / settings)
        self._view_stack = Adw.ViewStack()
        self._view_switcher = Adw.ViewSwitcher(stack=self._view_stack, policy=Adw.ViewSwitcherPolicy.WIDE)
        self._header.set_title_widget(self._view_switcher)

        # Search / refresh buttons
        self._btn_refresh = Gtk.Button(icon_name="view-refresh-symbolic")
        self._btn_refresh.set_tooltip_text("Refresh library")
        self._btn_refresh.connect("clicked", self._on_refresh_clicked)
        self._header.pack_start(self._btn_refresh)

        toolbar_view.set_content(self._view_stack)

        # Bottom switcher bar (for narrow widths)
        self._switcher_bar = Adw.ViewSwitcherBar(stack=self._view_stack)
        toolbar_view.add_bottom_bar(self._switcher_bar)

        # ---- Pages -------------------------------------------------- #
        from mythos.adapters.input.gtk.views.library_view import LibraryView
        from mythos.adapters.input.gtk.views.downloads_view import DownloadsView
        from mythos.adapters.input.gtk.views.settings_view import SettingsView
        from mythos.adapters.input.gtk.views.login_view import LoginView

        self._login_view = LoginView(container=self._c, on_login=self._on_login)
        self._library_view = LibraryView(container=self._c, window=self)
        self._downloads_view = DownloadsView(container=self._c)
        self._settings_view = SettingsView(container=self._c)

        # Login uses a separate overlay (not in the stack)
        self._login_overlay = Adw.Dialog()
        self._login_overlay.set_title("Sign in to Epic Games")
        self._login_overlay.set_content_width(800)
        self._login_overlay.set_content_height(600)
        self._login_overlay.set_child(self._login_view)

        self._view_stack.add_titled_with_icon(
            self._library_view, "library", "Library", _ICON_LIBRARY
        )
        self._view_stack.add_titled_with_icon(
            self._downloads_view, "downloads", "Downloads", _ICON_DOWNLOADS
        )
        self._view_stack.add_titled_with_icon(
            self._settings_view, "settings", "Settings", _ICON_SETTINGS
        )

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
