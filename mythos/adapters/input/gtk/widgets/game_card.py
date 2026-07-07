from __future__ import annotations

import logging

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk

from mythos.adapters.input.gtk.dialogs.game_context_menu import GameContextMenu
from mythos.adapters.input.gtk.view_models import GameViewModel
from mythos.domain.value_objects import GameStatus

logger = logging.getLogger(__name__)

_CARD_WIDTH = 220
_FOOTER_HEIGHT = 90
_CARD_HEIGHT = int(_CARD_WIDTH * 16 / 9)
_IMAGE_HEIGHT = _CARD_HEIGHT - _FOOTER_HEIGHT


class GameCard(Gtk.FlowBoxChild):
    """
    A fixed-width card at 9:16 vertical ratio (height = width x 16/9).

    Layout:
      - Image area (COVER) + settings button (top-right overlay, hover)
      - Footer: title + action button | progress bar + stats

    Right-click or click on the settings button opens a context menu
    with actions contextual to the game state.

    When a download is in progress the action button is replaced by an
    inline progress bar with downloaded/total and ETA.
    """

    def __init__(self, vm: GameViewModel, callbacks: dict[str, callable]) -> None:
        super().__init__()
        self._vm = vm
        self._callbacks = callbacks
        self._ctx_menu = GameContextMenu(vm, callbacks)

        self.set_size_request(_CARD_WIDTH, _CARD_HEIGHT)
        self.set_hexpand(False)
        self.set_vexpand(False)
        self._build()

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

        img_overlay.set_child(self._cover)

        settings_btn = Gtk.Button(icon_name="emblem-system-symbolic")
        settings_btn.add_css_class("flat")
        settings_btn.add_css_class("card-settings")
        settings_btn.set_tooltip_text("Game options")
        settings_btn.set_halign(Gtk.Align.END)
        settings_btn.set_valign(Gtk.Align.START)
        settings_btn.set_margin_top(6)
        settings_btn.set_margin_end(6)
        settings_btn.connect("clicked", self._on_settings_clicked)
        img_overlay.add_overlay(settings_btn)

        motion = Gtk.EventControllerMotion()
        motion.connect(
            "enter",
            lambda *_: settings_btn.add_css_class("card-settings-visible"),
        )
        motion.connect(
            "leave",
            lambda *_: settings_btn.remove_css_class("card-settings-visible"),
        )
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

        # Inline progress box (hidden by default)
        self._progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self._progress_box.set_margin_top(4)
        self._progress_box.set_visible(False)
        self._progress_box.add_css_class("card-progress-box")

        self._progress_bar = Gtk.ProgressBar()
        self._progress_bar.set_show_text(False)
        self._progress_bar.set_hexpand(True)
        self._progress_bar.add_css_class("card-progress-bar")
        self._progress_box.append(self._progress_bar)

        stats_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        stats_row.add_css_class("card-stats-row")

        self._stats_label = Gtk.Label(label="")
        self._stats_label.set_xalign(0)
        self._stats_label.set_hexpand(True)
        self._stats_label.add_css_class("dim-label")
        self._stats_label.add_css_class("caption")
        stats_row.append(self._stats_label)

        self._eta_label = Gtk.Label(label="")
        self._eta_label.set_xalign(1)
        self._eta_label.add_css_class("dim-label")
        self._eta_label.add_css_class("caption")
        stats_row.append(self._eta_label)

        self._progress_box.append(stats_row)
        footer.append(self._progress_box)

        outer.append(footer)

        self._load_cover()

        self._setup_right_click(outer)

        self.set_child(outer)

    def _setup_right_click(self, widget: Gtk.Widget) -> None:
        right_click = Gtk.GestureClick(button=3)
        right_click.connect("pressed", lambda *_: self._ctx_menu.show_at(widget))
        widget.add_controller(right_click)

    def _load_cover(self) -> None:
        if self._vm.cover_path and self._vm.cover_path.exists():
            try:
                self._cover.set_filename(str(self._vm.cover_path))
            except Exception as exc:
                logger.debug("Could not load cover %s: %s", self._vm.cover_path, exc)

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

    def _on_settings_clicked(self, btn: Gtk.Button) -> None:
        from mythos.adapters.input.gtk.dialogs.game_settings_dialog import GameSettingsDialog
        # Walk up the widget tree to reach the window, which carries the container
        root = self.get_root()
        container = getattr(root, "_c", None)
        if container is None:
            logger.warning("GameCard: could not find container on root window")
            return
        dialog = GameSettingsDialog(self._vm, container)
        dialog.present(root)

    def _on_action_clicked(self, _btn: Gtk.Button) -> None:
        status = self._vm.status
        if status == GameStatus.NOT_INSTALLED:
            self._callbacks.get("on_install", lambda _: None)(self._vm)
        elif status == GameStatus.INSTALLED:
            if self._vm.needs_update:
                self._callbacks.get("on_install", lambda _: None)(self._vm)
            else:
                self._callbacks.get("on_launch", lambda _: None)(self._vm)
        elif status == GameStatus.ERROR:
            self._callbacks.get("on_install", lambda _: None)(self._vm)

    # ------------------------------------------------------------ #
    # Inline progress (called from LibraryView via download events) #
    # ------------------------------------------------------------ #

    def show_progress(self) -> None:
        """Replace the action button with an inline progress bar."""
        self._action_btn.set_visible(False)
        self._progress_box.set_visible(True)

    def hide_progress(self) -> None:
        """Restore the action button and hide progress."""
        self._progress_box.set_visible(False)
        self._action_btn.set_visible(True)
        self._update_action_button()

    def update_progress(
        self,
        fraction: float,
        downloaded_bytes: int,
        total_bytes: int,
        eta_seconds: float,
    ) -> None:
        """Update progress bar fraction, downloaded/total text and ETA."""
        self._progress_bar.set_fraction(fraction)

        if total_bytes == 0:
            if downloaded_bytes > 0:
                self._stats_label.set_label(
                    f"{self._bytes_human(downloaded_bytes)} / ? GB"
                )
            else:
                self._stats_label.set_label("Calculando...")
        else:
            percent = int(fraction * 100)
            self._stats_label.set_label(
                f"{self._bytes_human(downloaded_bytes)} / {self._bytes_human(total_bytes)} ({percent}%)"
            )

        self._eta_label.set_label(self._eta_human(eta_seconds))

    @staticmethod
    def _bytes_human(b: int) -> str:
        if b == 0:
            return "0 B"
        if b >= 1024 ** 3:
            return f"{b / (1024 ** 3):.1f} GB"
        if b >= 1024 ** 2:
            return f"{b / (1024 ** 2):.1f} MB"
        if b >= 1024:
            return f"{b / 1024:.1f} KB"
        return f"{b} B"

    @staticmethod
    def _eta_human(seconds: float) -> str:
        s = int(seconds)
        if s < 60:
            return f"{s}s left"
        if s < 3600:
            return f"{s // 60}m left"
        return f"{s // 3600}h {(s % 3600) // 60}m left"
