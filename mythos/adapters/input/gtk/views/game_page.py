# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
GamePage — detail view for a single game.

Shows cover, metadata, and action buttons:
  - Install / Launch / Update / Repair / Uninstall
  - Cloud save sync
  - Per-game settings (launch options, Wine runner)
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from mythos.adapters.input.gtk.view_models import GameViewModel  # noqa: E402
from mythos.config.container import Container  # noqa: E402
from mythos.domain.value_objects import AppName, GameStatus, SyncDirection  # noqa: E402

logger = logging.getLogger(__name__)


class GamePage(Gtk.Box):
    def __init__(
        self,
        container: Container,
        vm: GameViewModel,
        window: object,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._c = container
        self._vm = vm
        self._window = window
        self._build_ui()

    # ---------------------------------------------------------------- #
    # UI                                                                 #
    # ---------------------------------------------------------------- #

    def _build_ui(self) -> None:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self.append(scrolled)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(24)
        content.set_margin_end(24)
        scrolled.set_child(content)

        # Cover + info row
        hero = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)

        cover = Gtk.Picture()
        cover.set_size_request(200, 267)
        cover.set_content_fit(Gtk.ContentFit.COVER)
        if self._vm.cover_path and self._vm.cover_path.exists():
            cover.set_filename(str(self._vm.cover_path))
        else:
            cover.set_icon_name("application-x-executable")
        hero.append(cover)

        meta = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        meta.set_vexpand(True)

        title = Gtk.Label(label=self._vm.title)
        title.add_css_class("title-1")
        title.set_xalign(0)
        title.set_wrap(True)
        meta.append(title)

        if self._vm.developer:
            dev = Gtk.Label(label=f"By {self._vm.developer}")
            dev.add_css_class("dim-label")
            dev.set_xalign(0)
            meta.append(dev)

        if self._vm.is_installed:
            info_grid = Gtk.Grid()
            info_grid.set_row_spacing(4)
            info_grid.set_column_spacing(12)

            def row(label: str, value: str, r: int) -> None:
                lbl = Gtk.Label(label=label)
                lbl.add_css_class("dim-label")
                lbl.set_xalign(1)
                val = Gtk.Label(label=value)
                val.set_xalign(0)
                info_grid.attach(lbl, 0, r, 1, 1)
                info_grid.attach(val, 1, r, 1, 1)

            row("Version", self._vm.version, 0)
            row("Install size", self._vm.install_size_human, 1)
            row("Location", self._vm.install_path, 2)
            meta.append(info_grid)

        hero.append(meta)
        content.append(hero)

        # Action buttons
        self._action_bar = self._build_action_bar()
        content.append(self._action_bar)

        # Status / progress row
        self._status_row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._status_row.set_visible(False)
        self._progress_bar = Gtk.ProgressBar()
        self._progress_bar.set_show_text(True)
        self._status_label = Gtk.Label()
        self._status_label.add_css_class("dim-label")
        self._status_row.append(self._progress_bar)
        self._status_row.append(self._status_label)
        content.append(self._status_row)

    def _build_action_bar(self) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        vm = self._vm

        if vm.can_launch:
            btn = Gtk.Button(label="Launch")
            btn.add_css_class("suggested-action")
            btn.add_css_class("pill")
            btn.connect("clicked", self._on_launch)
            box.append(btn)

        if vm.needs_update:
            btn = Gtk.Button(label="Update")
            btn.add_css_class("pill")
            btn.connect("clicked", self._on_update)
            box.append(btn)

        if vm.can_install:
            btn = Gtk.Button(label="Install")
            btn.add_css_class("suggested-action")
            btn.add_css_class("pill")
            btn.connect("clicked", self._on_install)
            box.append(btn)

        if vm.is_installed:
            repair_btn = Gtk.Button(label="Repair")
            repair_btn.add_css_class("pill")
            repair_btn.connect("clicked", self._on_repair)
            box.append(repair_btn)

            if vm.supports_cloud_saves:
                saves_btn = Gtk.Button(label="Sync saves")
                saves_btn.add_css_class("pill")
                saves_btn.connect("clicked", self._on_sync_saves)
                box.append(saves_btn)

            uninstall_btn = Gtk.Button(label="Uninstall")
            uninstall_btn.add_css_class("destructive-action")
            uninstall_btn.add_css_class("pill")
            uninstall_btn.connect("clicked", self._on_uninstall)
            box.append(uninstall_btn)

        return box

    # ---------------------------------------------------------------- #
    # Actions                                                            #
    # ---------------------------------------------------------------- #

    def _on_launch(self, btn: Gtk.Button) -> None:
        def _work() -> None:
            try:
                pid = self._c.launch_game_use_case.execute(AppName(self._vm.app_name))
                GLib.idle_add(self._show_status, f"Running (PID {pid})")
            except Exception as exc:
                GLib.idle_add(self._show_error, str(exc))

        threading.Thread(target=_work, daemon=True).start()

    def _on_install(self, btn: Gtk.Button) -> None:
        self._status_row.set_visible(True)
        self._progress_bar.set_fraction(0)
        self._status_label.set_text("Preparing install…")

        def _work() -> None:
            def on_prog(p: object) -> None:
                GLib.idle_add(
                    self._progress_bar.set_fraction, p.fraction  # type: ignore[attr-defined]
                )
                GLib.idle_add(
                    self._status_label.set_text,
                    f"{p.percent}% — {p.speed_human()}",  # type: ignore[attr-defined]
                )

            try:
                self._c.install_game_use_case.execute(AppName(self._vm.app_name))
                GLib.idle_add(self._show_status, "Installed successfully.")
            except Exception as exc:
                GLib.idle_add(self._show_error, str(exc))

        threading.Thread(target=_work, daemon=True).start()

    def _on_update(self, btn: Gtk.Button) -> None:
        def _work() -> None:
            try:
                self._c.update_game_use_case.execute(AppName(self._vm.app_name))
                GLib.idle_add(self._show_status, "Update complete.")
            except Exception as exc:
                GLib.idle_add(self._show_error, str(exc))

        threading.Thread(target=_work, daemon=True).start()

    def _on_repair(self, btn: Gtk.Button) -> None:
        def _work() -> None:
            try:
                self._c.repair_game_use_case.execute(AppName(self._vm.app_name))
                GLib.idle_add(self._show_status, "Repair complete.")
            except Exception as exc:
                GLib.idle_add(self._show_error, str(exc))

        threading.Thread(target=_work, daemon=True).start()

    def _on_uninstall(self, btn: Gtk.Button) -> None:
        dialog = Adw.AlertDialog()
        dialog.set_heading(f"Uninstall {self._vm.title}?")
        dialog.set_body("This will remove the game files from disk.")
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("uninstall", "Uninstall")
        dialog.set_response_appearance("uninstall", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.connect("response", self._on_uninstall_confirmed)
        dialog.present(self._window)

    def _on_uninstall_confirmed(self, dialog: Adw.AlertDialog, response: str) -> None:
        if response != "uninstall":
            return

        def _work() -> None:
            try:
                self._c.uninstall_game_use_case.execute(AppName(self._vm.app_name))
                GLib.idle_add(self._show_status, "Uninstalled.")
            except Exception as exc:
                GLib.idle_add(self._show_error, str(exc))

        threading.Thread(target=_work, daemon=True).start()

    def _on_sync_saves(self, btn: Gtk.Button) -> None:
        def _work() -> None:
            try:
                self._c.sync_saves_use_case.execute(
                    AppName(self._vm.app_name), SyncDirection.BOTH
                )
                GLib.idle_add(self._show_status, "Cloud saves synced.")
            except Exception as exc:
                GLib.idle_add(self._show_error, str(exc))

        threading.Thread(target=_work, daemon=True).start()

    # ---------------------------------------------------------------- #
    # Status helpers                                                     #
    # ---------------------------------------------------------------- #

    def _show_status(self, msg: str) -> bool:
        self._status_row.set_visible(True)
        self._status_label.set_text(msg)
        self._progress_bar.set_fraction(1.0)
        return GLib.SOURCE_REMOVE

    def _show_error(self, msg: str) -> bool:
        self._status_row.set_visible(True)
        self._status_label.set_markup(f'<span color="red">{msg}</span>')
        return GLib.SOURCE_REMOVE
