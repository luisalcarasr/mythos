from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, GLib, Gtk

from mythos.adapters.input.gtk.view_models import GameViewModel, ProtonReleaseViewModel
from mythos.domain.value_objects import WineRunnerType

if TYPE_CHECKING:
    from mythos.config.container import Container

logger = logging.getLogger(__name__)

_RUNNER_LABELS = ["None", "Proton", "Proton-GE"]
_RUNNER_TYPES = [WineRunnerType.NONE, WineRunnerType.PROTON, WineRunnerType.PROTON_GE]


class GameSettingsDialog(Adw.PreferencesDialog):
    """
    Game settings dialog with preferences pages.

    Tabs:
      - Game (default): cover image, game info, installation details, actions
      - Runner: runner-type selector, Proton version dropdown, launch params
      - About: long description (only when present)
    """

    def __init__(self, vm: GameViewModel, container: "Container") -> None:
        super().__init__()
        self._vm = vm
        self._c = container

        self.set_title(f"Settings \u2014 {vm.title}")
        self.set_content_width(620)
        self.set_content_height(700)
        self.set_search_enabled(False)

        self._launch_params_row: Adw.EntryRow | None = None
        self._offline_row: Adw.SwitchRow | None = None

        # Runner tab state
        self._all_releases: list[ProtonReleaseViewModel] = []
        self._filtered_releases: list[ProtonReleaseViewModel] = []
        self._version_combo: Adw.ComboRow | None = None
        self._version_model: Gtk.StringList | None = None

        self._build()

    def _build(self) -> None:
        self._build_game_info()       # combined "Game" tab (default)
        self._build_launch_options()  # own tab
        if self._vm.long_description:
            self._build_about()       # own tab, only when present

    # -- Pages -------------------------------------------------------- #

    def _build_launch_options(self) -> None:
        page = Adw.PreferencesPage(
            title="Runner", icon_name="media-playback-start-symbolic"
        )

        # -- Single "Runner" group: type selector + version dropdown -- #
        runner_group = Adw.PreferencesGroup(title="Runner")

        runner_model = Gtk.StringList.new(_RUNNER_LABELS)
        current_idx = 0
        if self._vm.wine_runner in _RUNNER_TYPES:
            current_idx = _RUNNER_TYPES.index(self._vm.wine_runner)

        self._runner_combo = Adw.ComboRow(title="Runner", model=runner_model)
        self._runner_combo.set_selected(current_idx)
        self._runner_combo.connect("notify::selected", self._on_runner_type_changed)
        runner_group.add(self._runner_combo)

        self._version_model = Gtk.StringList.new([])
        self._version_combo = Adw.ComboRow(title="Version")
        self._version_combo.set_model(self._version_model)
        self._version_combo.connect("notify::selected", self._on_version_selected)
        runner_group.add(self._version_combo)

        page.add(runner_group)

        # -- Launch options ------------------------------------------- #
        launch_group = Adw.PreferencesGroup(title="Launch Options")

        self._launch_params_row = Adw.EntryRow(title="Launch Parameters")
        self._launch_params_row.set_text(self._vm.launch_parameters or "")
        self._launch_params_row.connect("changed", self._on_launch_params_changed)
        launch_group.add(self._launch_params_row)

        self._offline_row = Adw.SwitchRow(title="Offline Mode")
        self._offline_row.set_subtitle(
            "Allow launching the game without an internet connection"
        )
        self._offline_row.set_active(self._vm.can_run_offline)
        self._offline_row.connect("notify::active", self._on_offline_toggled)
        launch_group.add(self._offline_row)

        page.add(launch_group)
        self.add(page)

        # Populate versions for the current runner type
        self._load_releases()

    # -- Runner tab helpers ------------------------------------------- #

    def _load_releases(self) -> None:
        """Load Proton releases in a background thread."""
        def _fetch() -> None:
            try:
                releases = self._c.list_proton_versions_use_case.execute()
                vms = [ProtonReleaseViewModel.from_release(r) for r in releases]
                GLib.idle_add(self._on_releases_loaded, vms)
            except Exception as exc:
                logger.error("Failed to load Proton releases: %s", exc)

        threading.Thread(target=_fetch, daemon=True, name="runner-list").start()

    def _on_releases_loaded(self, releases: list[ProtonReleaseViewModel]) -> bool:
        self._all_releases = releases
        self._refresh_version_dropdown()
        return GLib.SOURCE_REMOVE

    def _current_runner_type(self) -> WineRunnerType:
        idx = self._runner_combo.get_selected() if self._runner_combo else 0
        if 0 <= idx < len(_RUNNER_TYPES):
            return _RUNNER_TYPES[idx]
        return WineRunnerType.NONE

    def _refresh_version_dropdown(self) -> None:
        if self._version_model is None or self._version_combo is None:
            return

        runner_type = self._current_runner_type()

        if runner_type == WineRunnerType.NONE:
            self._filtered_releases = []
        else:
            self._filtered_releases = [
                r for r in self._all_releases if r.runner_type == runner_type
            ]

        # Rebuild the string list
        while self._version_model.get_n_items():
            self._version_model.remove(0)

        if not self._filtered_releases:
            self._version_model.append("No versions available")
            self._version_combo.set_sensitive(False)
            return

        self._version_combo.set_sensitive(True)
        selected_idx = 0
        for i, rel in enumerate(self._filtered_releases):
            # Show only the bare version tag + installed marker or size
            suffix = " ✓" if rel.installed else f"  ({rel.size_human})"
            self._version_model.append(f"{rel.version}{suffix}")
            if rel.version == self._vm.proton_version:
                selected_idx = i

        self._version_combo.set_selected(selected_idx)

    def _on_runner_type_changed(self, combo: Adw.ComboRow, _: object) -> None:
        self._refresh_version_dropdown()

    def _on_version_selected(self, combo: Adw.ComboRow, _: object) -> None:
        """Persist the per-game runner selection regardless of install state.

        The actual download happens lazily when the game is launched and
        the selected version is not yet installed.
        """
        idx = combo.get_selected()
        if not self._filtered_releases or idx >= len(self._filtered_releases):
            return
        rel = self._filtered_releases[idx]
        if not self._vm.is_installed:
            return
        from mythos.domain.value_objects import AppName
        try:
            self._c.set_game_proton_use_case.execute(
                AppName(self._vm.app_name), rel.runner_type, rel.version
            )
            # Keep vm in sync so reopening the dialog shows the right selection
            self._vm = self._vm.__class__(
                **{**self._vm.__dict__,
                   "wine_runner": rel.runner_type,
                   "proton_version": rel.version}
            )
        except Exception as exc:
            logger.error("Failed to set game runner: %s", exc)

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
