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
_FOOTER_HEIGHT = 60
_CARD_HEIGHT = int(_CARD_WIDTH * 16 / 9)
_IMAGE_HEIGHT = _CARD_HEIGHT - _FOOTER_HEIGHT


class GameCard(Gtk.FlowBoxChild):
    """
    A fixed-width card at 9:16 vertical ratio (height = width x 16/9).

    Layout:
      - Image area (COVER) + settings button (top-right overlay, hover)
      - Footer: title + action button

    Right-click or click on the settings button opens a context menu
    with actions contextual to the game state.
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
        settings_btn.connect("clicked", lambda *_: self._ctx_menu.show_at(settings_btn))
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
