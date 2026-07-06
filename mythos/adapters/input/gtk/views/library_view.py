# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
LibraryView — grid of game covers.

Layout:
  Gtk.Box (vertical)
  ├── Gtk.SearchEntry
  └── Gtk.ScrolledWindow
      └── Gtk.FlowBox
          └── GameCard × N
"""

from __future__ import annotations

import logging
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from mythos.config.container import Container  # noqa: E402
from mythos.adapters.input.gtk.dialogs.game_settings_dialog import (  # noqa: E402
    GameSettingsDialog,
)
from mythos.adapters.input.gtk.dialogs.edit_game_dialog import EditGameDialog  # noqa: E402
from mythos.adapters.input.gtk.view_models import GameViewModel, LibraryViewModel  # noqa: E402
from mythos.adapters.input.gtk.widgets.game_card import GameCard  # noqa: E402
from mythos.domain.events import LibraryRefreshCompleted, LibraryRefreshStarted  # noqa: E402
from mythos.domain.value_objects import AppName  # noqa: E402

logger = logging.getLogger(__name__)


class LibraryView(Gtk.Box):
    def __init__(self, container: Container, window: object) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._c = container
        self._window = window
        self._vm = LibraryViewModel()

        self._build_ui()
        self._subscribe_events()

    # ---------------------------------------------------------------- #
    # UI construction                                                    #
    # ---------------------------------------------------------------- #

    def _build_ui(self) -> None:
        # Toolbar row (search + filters)
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        toolbar.set_margin_top(8)
        toolbar.set_margin_bottom(8)
        toolbar.set_margin_start(12)
        toolbar.set_margin_end(12)

        self._search = Gtk.SearchEntry()
        self._search.set_placeholder_text("Search games…")
        self._search.set_hexpand(True)
        self._search.connect("search-changed", self._on_search_changed)
        toolbar.append(self._search)

        self._filter_btn = Gtk.ToggleButton(label="Installed only")
        self._filter_btn.connect("toggled", self._on_filter_toggled)
        toolbar.append(self._filter_btn)

        self.append(toolbar)

        # Separator
        self.append(Gtk.Separator())

        # Loading spinner overlay
        self._spinner_overlay = Gtk.Overlay()
        self._spinner_overlay.set_vexpand(True)

        self._scrolled = Gtk.ScrolledWindow()
        self._scrolled.set_vexpand(True)
        self._scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._flow = Gtk.FlowBox()
        self._flow.set_max_children_per_line(4)
        self._flow.set_min_children_per_line(4)
        self._flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self._flow.set_homogeneous(False)
        self._flow.set_column_spacing(12)
        self._flow.set_row_spacing(12)
        self._flow.set_margin_top(12)
        self._flow.set_margin_bottom(12)
        self._flow.set_margin_start(12)
        self._flow.set_margin_end(12)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(1080)
        clamp.set_child(self._flow)
        self._scrolled.set_child(clamp)

        self._spinner_overlay.set_child(self._scrolled)

        # Spinner (shown during refresh)
        self._spinner = Gtk.Spinner()
        self._spinner.set_size_request(64, 64)
        self._spinner.set_halign(Gtk.Align.CENTER)
        self._spinner.set_valign(Gtk.Align.CENTER)
        self._spinner.set_visible(False)
        self._spinner_overlay.add_overlay(self._spinner)

        # Empty state
        self._empty_status = Adw.StatusPage()
        self._empty_status.set_icon_name("application-x-executable-symbolic")
        self._empty_status.set_title("No games found")
        self._empty_status.set_description("Refresh your library or adjust the filter.")
        self._empty_status.set_visible(False)
        self._spinner_overlay.add_overlay(self._empty_status)

        self.append(self._spinner_overlay)

    # ---------------------------------------------------------------- #
    # Refresh                                                            #
    # ---------------------------------------------------------------- #

    def refresh(self) -> None:
        """Trigger a library refresh in a background thread."""
        self._set_loading(True)
        threading.Thread(
            target=self._fetch_games, daemon=True, name="library-refresh"
        ).start()

    def _fetch_games(self) -> None:
        try:
            games = self._c.refresh_library_use_case.execute()
            GLib.idle_add(self._on_games_loaded, games)
        except Exception as exc:
            logger.error("Library refresh error: %s", exc)
            GLib.idle_add(self._set_loading, False)

    def _on_games_loaded(self, games: list) -> bool:
        from mythos.domain.entities import Game
        vms = [GameViewModel.from_game(g) for g in games]
        self._vm.games = vms
        self._render()
        self._set_loading(False)
        return GLib.SOURCE_REMOVE

    # ---------------------------------------------------------------- #
    # Render                                                             #
    # ---------------------------------------------------------------- #

    def _render(self) -> None:
        # Remove existing cards
        while child := self._flow.get_child_at_index(0):
            self._flow.remove(child)

        visible = self._vm.visible_games
        if not visible:
            self._empty_status.set_visible(True)
            return

        self._empty_status.set_visible(False)
        for vm in visible:
            card = GameCard(
                vm=vm,
                callbacks={
                    "on_settings": self._on_game_settings,
                    "on_edit": self._on_game_edit,
                    "on_install": self._on_game_install,
                    "on_launch": self._on_game_launch,
                    "on_update": self._on_game_install,
                    "on_uninstall": self._on_game_uninstall,
                    "on_verify": self._on_game_verify,
                    "on_open_folder": self._on_game_open_folder,
                },
            )
            self._flow.append(card)

    def _on_game_settings(self, vm: GameViewModel) -> None:
        dialog = GameSettingsDialog(vm)
        dialog.present(self._window)

    def _on_game_edit(self, vm: GameViewModel) -> None:
        on_save = lambda title, cover: logger.info(
            "Edit %s: title=%s, cover=%s", vm.app_name, title, cover
        )
        dialog = EditGameDialog(vm, on_save=on_save)
        dialog.present(self._window)

    def _on_game_install(self, vm: GameViewModel) -> None:
        def _work() -> None:
            try:
                self._c.install_game_use_case.execute(AppName(vm.app_name))
                GLib.idle_add(self._refresh_library)
            except Exception as exc:
                logger.error("Install failed for %s: %s", vm.app_name, exc)

        threading.Thread(target=_work, daemon=True).start()

    def _on_game_launch(self, vm: GameViewModel) -> None:
        def _work() -> None:
            try:
                self._c.launch_game_use_case.execute(AppName(vm.app_name))
            except Exception as exc:
                logger.error("Launch failed for %s: %s", vm.app_name, exc)

        threading.Thread(target=_work, daemon=True).start()

    def _on_game_uninstall(self, vm: GameViewModel) -> None:
        def _work() -> None:
            try:
                self._c.uninstall_game_use_case.execute(AppName(vm.app_name))
                GLib.idle_add(self._refresh_library)
            except Exception as exc:
                logger.error("Uninstall failed for %s: %s", vm.app_name, exc)

        threading.Thread(target=_work, daemon=True).start()

    def _on_game_verify(self, vm: GameViewModel) -> None:
        def _work() -> None:
            try:
                self._c.repair_game_use_case.execute(AppName(vm.app_name))
                GLib.idle_add(self._refresh_library)
            except Exception as exc:
                logger.error("Verify failed for %s: %s", vm.app_name, exc)

        threading.Thread(target=_work, daemon=True).start()

    def _on_game_open_folder(self, vm: GameViewModel) -> None:
        if vm.install_path:
            from gi.repository import Gdk
            Gtk.show_uri(None, f"file://{vm.install_path}", Gdk.CURRENT_TIME)

    def _refresh_library(self) -> None:
        def _work() -> None:
            try:
                self._c.refresh_library_use_case.execute()
            except Exception as exc:
                logger.error("Refresh failed: %s", exc)

        threading.Thread(target=_work, daemon=True).start()

    # ---------------------------------------------------------------- #
    # Helpers                                                            #
    # ---------------------------------------------------------------- #

    def _set_loading(self, loading: bool) -> bool:
        self._vm.is_loading = loading
        self._spinner.set_visible(loading)
        if loading:
            self._spinner.start()
        else:
            self._spinner.stop()
        return GLib.SOURCE_REMOVE

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        self._vm.search_query = entry.get_text()
        self._render()

    def _on_filter_toggled(self, btn: Gtk.ToggleButton) -> None:
        self._vm.filter_installed_only = btn.get_active()
        self._render()

    def _on_library_refresh_started(self, event: object) -> None:
        self._set_loading(True)

    def _on_library_refresh_completed(self, event: object) -> None:
        try:
            games = self._c.list_library_use_case.execute()
            from mythos.domain.entities import Game
            vms = [GameViewModel.from_game(g) for g in games]
            self._vm.games = vms
            self._render()
        except Exception as exc:
            logger.error("Cache reload error: %s", exc)
        self._set_loading(False)

    def _subscribe_events(self) -> None:
        bus = self._c.event_bus
        bus.subscribe(LibraryRefreshStarted, self._on_library_refresh_started)
        bus.subscribe(LibraryRefreshCompleted, self._on_library_refresh_completed)
