from __future__ import annotations

import logging

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gtk

from mythos.adapters.input.gtk.view_models import GameViewModel

logger = logging.getLogger(__name__)


class GameSettingsDialog(Adw.PreferencesDialog):
    """
    Game settings dialog with preferences pages.

    Tabs:
      - Game (default): cover image, game info, installation details, actions
      - Runner: launch parameters, offline mode
      - About: long description (only when present)
    """

    def __init__(self, vm: GameViewModel) -> None:
        super().__init__()
        self._vm = vm

        self.set_title(f"Settings \u2014 {vm.title}")
        self.set_content_width(620)
        self.set_content_height(700)
        self.set_search_enabled(False)

        self._launch_params_row: Adw.EntryRow | None = None
        self._offline_row: Adw.SwitchRow | None = None

        self._build()

    def _build(self) -> None:
        self._build_game_info()       # combined "Game" tab (default)
        self._build_launch_options()  # own tab
        if self._vm.long_description:
            self._build_about()       # own tab, only when present

    # -- Pages -------------------------------------------------------- #

    def _build_launch_options(self) -> None:
        page = Adw.PreferencesPage(title="Runner")
        group = Adw.PreferencesGroup(title="Runner")

        self._launch_params_row = Adw.EntryRow(title="Launch Parameters")
        self._launch_params_row.set_text(self._vm.launch_parameters or "")
        self._launch_params_row.connect("changed", self._on_launch_params_changed)
        group.add(self._launch_params_row)

        self._offline_row = Adw.SwitchRow(title="Offline Mode")
        self._offline_row.set_subtitle("Allow launching the game without an internet connection")
        self._offline_row.set_active(self._vm.can_run_offline)
        self._offline_row.connect("notify::active", self._on_offline_toggled)
        group.add(self._offline_row)

        page.add(group)
        self.add(page)

    def _installation_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title="Installation")

        if self._vm.install_path:
            path_row = Adw.ActionRow(title="Install Path")
            path_row.set_subtitle(self._vm.install_path)
            open_btn = Gtk.Button(icon_name="folder-open-symbolic")
            open_btn.set_tooltip_text("Open folder")
            open_btn.add_css_class("flat")
            open_btn.connect("clicked", self._on_open_folder)
            path_row.add_suffix(open_btn)
            group.add(path_row)

        if self._vm.version:
            row = Adw.ActionRow(title="Version")
            row.set_subtitle(self._vm.version)
            group.add(row)

        if self._vm.install_size_human:
            row = Adw.ActionRow(title="Install Size")
            row.set_subtitle(self._vm.install_size_human)
            group.add(row)

        if self._vm.platform:
            row = Adw.ActionRow(title="Platform")
            row.set_subtitle(self._vm.platform)
            group.add(row)

        if self._vm.executable:
            row = Adw.ActionRow(title="Executable")
            row.set_subtitle(self._vm.executable)
            group.add(row)

        return group

    def _build_game_info(self) -> None:
        page = Adw.PreferencesPage(title="Game", icon_name="dialog-information-symbolic")

        # -- Wide cover image ------------------------------------------ #
        cover_path = self._vm.cover_wide_path or self._vm.cover_path
        if cover_path and cover_path.exists():
            picture = Gtk.Picture()
            picture.set_filename(str(cover_path))
            picture.set_content_fit(Gtk.ContentFit.COVER)
            picture.set_size_request(-1, 200)
            picture.set_hexpand(True)
            picture.add_css_class("game-dialog-cover")

            cover_frame = Gtk.Frame()
            cover_frame.set_child(picture)
            cover_frame.add_css_class("game-dialog-cover-frame")

            cover_group = Adw.PreferencesGroup()
            cover_group.add_css_class("game-dialog-cover-group")
            cover_group.add(cover_frame)
            page.add(cover_group)

        # -- Metadata rows --------------------------------------------- #
        group = Adw.PreferencesGroup()

        if self._vm.developer:
            row = Adw.ActionRow(title="Developer")
            row.set_subtitle(self._vm.developer)
            group.add(row)

        if self._vm.publisher:
            row = Adw.ActionRow(title="Publisher")
            row.set_subtitle(self._vm.publisher)
            group.add(row)

        if self._vm.release_date_human:
            row = Adw.ActionRow(title="Release Date")
            row.set_subtitle(self._vm.release_date_human)
            group.add(row)

        if self._vm.categories:
            row = Adw.ActionRow(title="Categories")
            row.set_subtitle(", ".join(self._vm.categories))
            group.add(row)

        cloud_row = Adw.ActionRow(title="Cloud Saves")
        cloud_row.set_subtitle(
            "Supported" if self._vm.supports_cloud_saves else "Not supported"
        )
        group.add(cloud_row)

        if self._vm.save_path:
            save_row = Adw.ActionRow(title="Save Path")
            save_row.set_subtitle(self._vm.save_path)
            group.add(save_row)

        page.add(group)

        # -- Installation & Actions (installed games only) ------------- #
        if self._vm.is_installed:
            page.add(self._installation_group())
            page.add(self._actions_group())

        self.add(page)

    def _build_about(self) -> None:
        page = Adw.PreferencesPage(title="About")
        group = Adw.PreferencesGroup(title="About")

        desc_label = Gtk.Label(label=self._vm.long_description)
        desc_label.set_wrap(True)
        desc_label.set_xalign(0)
        desc_label.set_margin_top(8)
        desc_label.set_margin_bottom(8)
        desc_label.set_margin_start(8)
        desc_label.set_margin_end(8)

        group.add(desc_label)
        page.add(group)
        self.add(page)

    def _actions_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title="Actions")

        verify_row = Adw.ActionRow(title="Verify Files")
        verify_row.set_subtitle("Check game file integrity and repair any issues")
        verify_btn = Gtk.Button(label="Verify")
        verify_btn.add_css_class("flat")
        verify_btn.connect("clicked", self._on_verify)
        verify_row.add_suffix(verify_btn)
        verify_row.set_activatable_widget(verify_btn)
        group.add(verify_row)

        uninstall_row = Adw.ActionRow(title="Uninstall")
        uninstall_row.set_subtitle("Remove the game from your system")
        uninstall_btn = Gtk.Button(label="Uninstall")
        uninstall_btn.add_css_class("destructive-action")
        uninstall_btn.connect("clicked", self._on_uninstall)
        uninstall_row.add_suffix(uninstall_btn)
        uninstall_row.set_activatable_widget(uninstall_btn)
        group.add(uninstall_row)

        return group

    # -- Handlers ----------------------------------------------------- #

    def _on_launch_params_changed(self, entry: Adw.EntryRow) -> None:
        logger.debug("Launch parameters changed: %s", entry.get_text())

    def _on_offline_toggled(self, switch: Adw.SwitchRow, _pspec: object) -> None:
        logger.debug("Offline mode: %s", switch.get_active())

    def _on_open_folder(self, _btn: Gtk.Button) -> None:
        if self._vm.install_path:
            Gtk.show_uri(None, f"file://{self._vm.install_path}", Gdk.CURRENT_TIME)

    def _on_verify(self, _btn: Gtk.Button) -> None:
        logger.info("Verify requested for %s", self._vm.app_name)

    def _on_uninstall(self, _btn: Gtk.Button) -> None:
        logger.info("Uninstall requested for %s", self._vm.app_name)
