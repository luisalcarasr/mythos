# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

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
        on_back: Callable[[], None],
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._c = container
        self._vm = vm
        self._on_back = on_back
        self._build_ui()

    def _build_ui(self) -> None:
        # Header with back button
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_margin_top(12)
        header.set_margin_start(12)
        header.set_margin_bottom(8)

        back_btn = Gtk.Button(label="Back to Library")
        back_btn.set_icon_name("go-previous-symbolic")
        back_btn.add_css_class("flat")
        back_btn.connect("clicked", lambda *_: self._go_back())
        header.append(back_btn)

        self.append(header)

        # Scrolled content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self.append(scrolled)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_bottom(24)
        content.set_margin_start(24)
        content.set_margin_end(24)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(1080)
        clamp.set_child(content)
        scrolled.set_child(clamp)

        # -- Hero cover (full width) ------------------------------------
        self._hero = Gtk.Picture()
        self._hero.set_content_fit(Gtk.ContentFit.COVER)
        self._hero.set_size_request(-1, 360)
        self._hero.add_css_class("game-hero-cover")
        self._load_hero_cover()
        content.append(self._hero)

        # -- Title section ----------------------------------------------
        title = Gtk.Label(label=self._vm.title)
        title.add_css_class("title-1")
        title.set_xalign(0)
        title.set_wrap(True)
        content.append(title)

        # Developer / Publisher
        dev_pub_text = ""
        if self._vm.developer:
            dev_pub_text = f"by {self._vm.developer}"
            if self._vm.publisher and self._vm.publisher != self._vm.developer:
                dev_pub_text += f" \u00b7 {self._vm.publisher}"
        if dev_pub_text:
            dev_pub = Gtk.Label(label=dev_pub_text)
            dev_pub.add_css_class("dim-label")
            dev_pub.set_xalign(0)
            content.append(dev_pub)

        # Release date
        if self._vm.release_date_human:
            release_lbl = Gtk.Label(label=self._vm.release_date_human)
            release_lbl.add_css_class("dim-label")
            release_lbl.set_xalign(0)
            content.append(release_lbl)

        # -- Action buttons ---------------------------------------------
        self._action_bar = self._build_action_bar()
        content.append(self._action_bar)

        # -- Separator --------------------------------------------------
        sep = Gtk.Separator()
        sep.set_margin_top(4)
        content.append(sep)

        # -- About section ----------------------------------------------
        desc_text = self._vm.long_description or self._vm.description
        if desc_text:
            about_title = Gtk.Label(label="About")
            about_title.add_css_class("title-3")
            about_title.set_xalign(0)
            content.append(about_title)

            about_text = Gtk.Label(label=desc_text)
            about_text.set_xalign(0)
            about_text.set_wrap(True)
            about_text.set_wrap_mode(2)
            content.append(about_text)

            content.append(Gtk.Separator())

        # -- Details section --------------------------------------------
        details_title = Gtk.Label(label="Details")
        details_title.add_css_class("title-3")
        details_title.set_xalign(0)
        content.append(details_title)

        details_grid = Gtk.Grid()
        details_grid.set_row_spacing(6)
        details_grid.set_column_spacing(16)
        details_grid.set_margin_top(4)
        details_grid.set_margin_bottom(8)

        row_idx = 0

        def add_row(label: str, value: str) -> None:
            nonlocal row_idx
            lbl = Gtk.Label(label=f"{label}:")
            lbl.add_css_class("dim-label")
            lbl.set_xalign(1)
            val = Gtk.Label(label=value)
            val.set_xalign(0)
            val.set_wrap(True)
            val.set_selectable(True)
            details_grid.attach(lbl, 0, row_idx, 1, 1)
            details_grid.attach(val, 1, row_idx, 1, 1)
            row_idx += 1

        if self._vm.is_installed:
            add_row("Platform", self._vm.platform if self._vm.platform else "Windows")
            add_row("Version", self._vm.version)
            add_row("Install size", self._vm.install_size_human)
            add_row("Install location", self._vm.install_path)
            if self._vm.executable:
                add_row("Executable", self._vm.executable)
            if self._vm.launch_parameters:
                add_row("Launch parameters", self._vm.launch_parameters)
            if self._vm.save_path:
                add_row("Save location", self._vm.save_path)
        add_row("Cloud saves", "Yes" if self._vm.supports_cloud_saves else "No")
        add_row("Type", "DLC" if self._vm.is_dlc else "Base Game")
        if self._vm.is_installed:
            add_row("Offline mode", "Yes" if self._vm.can_run_offline else "No")

        content.append(details_grid)

        # -- Categories section -----------------------------------------
        if self._vm.categories:
            content.append(Gtk.Separator())

            cat_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            cat_box.set_margin_top(4)

            cat_lbl = Gtk.Label(label="Categories:")
            cat_lbl.add_css_class("dim-label")
            cat_box.append(cat_lbl)

            cat_flow = Gtk.FlowBox()
            cat_flow.set_selection_mode(Gtk.SelectionMode.NONE)
            cat_flow.set_column_spacing(6)
            cat_flow.set_row_spacing(6)
            cat_flow.set_hexpand(True)

            for cat in self._vm.categories:
                chip = Gtk.Button(label=cat)
                chip.add_css_class("pill")
                chip.set_sensitive(False)
                cat_flow.append(chip)

            cat_box.append(cat_flow)
            content.append(cat_box)

        # -- Progress / status row --------------------------------------
        content.append(Gtk.Separator())
        self._status_row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._status_row.set_visible(False)
        self._progress_bar = Gtk.ProgressBar()
        self._progress_bar.set_show_text(True)
        self._status_label = Gtk.Label()
        self._status_label.add_css_class("dim-label")
        self._status_row.append(self._progress_bar)
        self._status_row.append(self._status_label)
        content.append(self._status_row)

    def _load_hero_cover(self) -> None:
        path = self._vm.cover_wide_path or self._vm.cover_path
        if path and path.exists():
            try:
                self._hero.set_filename(str(path))
                return
            except Exception as exc:
                logger.debug("Could not load hero cover %s: %s", path, exc)

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

    def _go_back(self) -> None:
        self._on_back()

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
        self._status_label.set_text("Preparing install\u2026")

        def _work() -> None:
            def on_prog(p: object) -> None:
                GLib.idle_add(
                    self._progress_bar.set_fraction, p.fraction  # type: ignore[attr-defined]
                )
                GLib.idle_add(
                    self._status_label.set_text,
                    f"{p.percent}% \u2014 {p.speed_human()}",  # type: ignore[attr-defined]
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
        dialog.present(self)

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

    def _show_status(self, msg: str) -> bool:
        self._status_row.set_visible(True)
        self._status_label.set_text(msg)
        self._progress_bar.set_fraction(1.0)
        return GLib.SOURCE_REMOVE

    def _show_error(self, msg: str) -> bool:
        self._status_row.set_visible(True)
        self._status_label.set_markup(f'<span color="red">{msg}</span>')
        return GLib.SOURCE_REMOVE
