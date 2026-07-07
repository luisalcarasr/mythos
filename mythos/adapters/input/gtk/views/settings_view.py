# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
SettingsView — Adw.PreferencesPage with all app settings.

Sections:
  - General  (language, theme, startup behaviour)
  - Downloads (default install path, concurrent downloads)
  - Wine      (default runner, default executable)
  - Account   (logout button)
"""

from __future__ import annotations

import logging
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from mythos.config.container import Container  # noqa: E402
from mythos.domain.entities import AppSettings  # noqa: E402
from mythos.domain.value_objects import WineRunnerType  # noqa: E402

logger = logging.getLogger(__name__)


class SettingsView(Adw.PreferencesPage):
    def __init__(self, container: Container) -> None:
        super().__init__()
        self._c = container
        self._settings = self._c.get_settings_use_case.execute()
        self._build_ui()

    def _build_ui(self) -> None:
        self.set_icon_name("preferences-system-symbolic")
        self.set_title("Settings")

        # ---- General ------------------------------------------------ #
        general = Adw.PreferencesGroup(title="General")

        self._lang_row = Adw.EntryRow(title="Language code (e.g. en, es)")
        self._lang_row.set_text(self._settings.language)
        self._lang_row.connect("changed", self._on_language_changed)
        general.add(self._lang_row)

        theme_model = Gtk.StringList.new(["System", "Light", "Dark"])
        theme_map = {"system": 0, "light": 1, "dark": 2}
        self._theme_row = Adw.ComboRow(title="Theme", model=theme_model)
        self._theme_row.set_selected(theme_map.get(self._settings.theme, 0))
        self._theme_row.connect("notify::selected", self._on_theme_changed)
        general.add(self._theme_row)

        self._updates_row = Adw.SwitchRow(title="Check for updates on startup")
        self._updates_row.set_active(self._settings.check_updates_on_startup)
        self._updates_row.connect("notify::active", self._on_updates_toggled)
        general.add(self._updates_row)

        self._tray_row = Adw.SwitchRow(title="Minimize to system tray")
        self._tray_row.set_active(self._settings.minimize_to_tray)
        self._tray_row.connect("notify::active", self._on_tray_toggled)
        general.add(self._tray_row)

        self._dlc_row = Adw.SwitchRow(title="Show DLC in library")
        self._dlc_row.set_active(self._settings.show_dlc_in_library)
        self._dlc_row.connect("notify::active", self._on_dlc_toggled)
        general.add(self._dlc_row)

        self.add(general)

        # ---- Downloads ---------------------------------------------- #
        downloads_group = Adw.PreferencesGroup(title="Downloads")

        self._install_path_row = Adw.ActionRow(title="Default install path")
        self._install_path_row.set_subtitle(
            str(self._settings.default_install_path or Path.home() / "Games")
        )
        choose_btn = Gtk.Button(label="Choose…")
        choose_btn.set_valign(Gtk.Align.CENTER)
        choose_btn.connect("clicked", self._on_choose_install_path)
        self._install_path_row.add_suffix(choose_btn)
        downloads_group.add(self._install_path_row)

        adj = Gtk.Adjustment(
            value=self._settings.concurrent_downloads,
            lower=1, upper=5, step_increment=1,
        )
        self._concurrent_row = Adw.SpinRow(title="Concurrent downloads", adjustment=adj)
        self._concurrent_row.connect("changed", self._on_concurrent_changed)
        downloads_group.add(self._concurrent_row)

        self.add(downloads_group)

        # ---- Proton / Wine ----------------------------------------- #
        wine_group = Adw.PreferencesGroup(title="Proton / Wine (umu)")

        runner_model = Gtk.StringList.new(["None", "Proton", "Proton-GE"])
        runner_map = {
            WineRunnerType.NONE: 0,
            WineRunnerType.PROTON: 1,
            WineRunnerType.PROTON_GE: 2,
        }
        self._runner_row = Adw.ComboRow(title="Default runner", model=runner_model)
        self._runner_row.set_selected(runner_map.get(self._settings.default_wine_runner, 0))
        self._runner_row.connect("notify::selected", self._on_runner_changed)
        wine_group.add(self._runner_row)

        subtitle = Adw.ActionRow()
        subtitle.set_subtitle("Proton is auto-downloaded by umu. Select which variant to use by default.")
        subtitle.set_activatable(False)
        wine_group.add(subtitle)

        self.add(wine_group)

        # ---- Account ------------------------------------------------ #
        account_group = Adw.PreferencesGroup(title="Account")
        logout_row = Adw.ActionRow(title="Epic Games account")
        logout_btn = Gtk.Button(label="Sign out")
        logout_btn.add_css_class("destructive-action")
        logout_btn.set_valign(Gtk.Align.CENTER)
        logout_btn.connect("clicked", self._on_logout)
        logout_row.add_suffix(logout_btn)
        account_group.add(logout_row)
        self.add(account_group)

    # ---------------------------------------------------------------- #
    # Change handlers (all persist immediately)                          #
    # ---------------------------------------------------------------- #

    def _save(self) -> None:
        try:
            self._c.update_settings_use_case.execute(self._settings)
        except Exception as exc:
            logger.error("Could not save settings: %s", exc)

    def _on_language_changed(self, row: Adw.EntryRow) -> None:
        self._settings.language = row.get_text().strip()
        self._save()

    def _on_theme_changed(self, row: Adw.ComboRow, _: object) -> None:
        themes = ["system", "light", "dark"]
        self._settings.theme = themes[row.get_selected()]
        self._save()

    def _on_updates_toggled(self, row: Adw.SwitchRow, _: object) -> None:
        self._settings.check_updates_on_startup = row.get_active()
        self._save()

    def _on_tray_toggled(self, row: Adw.SwitchRow, _: object) -> None:
        self._settings.minimize_to_tray = row.get_active()
        self._save()

    def _on_dlc_toggled(self, row: Adw.SwitchRow, _: object) -> None:
        self._settings.show_dlc_in_library = row.get_active()
        self._save()

    def _on_concurrent_changed(self, row: Adw.SpinRow) -> None:
        self._settings.concurrent_downloads = int(row.get_value())
        self._save()

    def _on_runner_changed(self, row: Adw.ComboRow, _: object) -> None:
        runners = [
            WineRunnerType.NONE,
            WineRunnerType.PROTON,
            WineRunnerType.PROTON_GE,
        ]
        self._settings.default_wine_runner = runners[row.get_selected()]
        self._save()

    def _on_choose_install_path(self, btn: Gtk.Button) -> None:
        dialog = Gtk.FileDialog()
        dialog.set_title("Choose default install path")
        dialog.select_folder(
            parent=self.get_root(),
            callback=self._on_folder_chosen,
        )

    def _on_folder_chosen(self, dialog: Gtk.FileDialog, result: object) -> None:
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                path = Path(folder.get_path())
                self._settings.default_install_path = path
                self._install_path_row.set_subtitle(str(path))
                self._save()
        except Exception:  # noqa: BLE001
            pass

    def _on_logout(self, btn: Gtk.Button) -> None:
        import threading

        def _work() -> None:
            self._c.logout_use_case.execute()

        threading.Thread(target=_work, daemon=True).start()
