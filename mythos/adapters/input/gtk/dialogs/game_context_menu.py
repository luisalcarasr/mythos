from __future__ import annotations

import logging

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk

from mythos.adapters.input.gtk.view_models import GameViewModel
from mythos.domain.value_objects import GameStatus

logger = logging.getLogger(__name__)


class GameContextMenu:
    """
    Popover context menu for a game card.

    Shows contextual actions based on game state:
    - Settings / Edit Game (always)
    - Play / Install / Update (contextual)
    - Verify Files / Open Folder / Uninstall (installed only)
    """

    def __init__(self, vm: GameViewModel, callbacks: dict[str, callable]) -> None:
        self._vm = vm
        self._callbacks = callbacks
        self._popover: Gtk.Popover | None = None

    def show_at(self, widget: Gtk.Widget) -> None:
        self._dismiss()

        self._popover = Gtk.Popover()
        self._popover.set_autohide(True)
        self._popover.set_has_arrow(False)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._build(box)

        self._popover.set_child(box)
        self._popover.set_parent(widget)
        self._popover.popup()

    def _dismiss(self) -> None:
        if self._popover is not None:
            self._popover.popdown()
            self._popover.unparent()
            self._popover = None

    def _build(self, box: Gtk.Box) -> None:
        self._add_item(box, "Settings", "on_settings")
        self._add_item(box, "Edit Game", "on_edit")

        status = self._vm.status
        if status == GameStatus.NOT_INSTALLED:
            self._add_separator(box)
            self._add_item(box, "Install", "on_install")

        elif status == GameStatus.INSTALLED:
            self._add_separator(box)
            if self._vm.needs_update:
                self._add_item(box, "Update", "on_update")
            self._add_item(box, "Play", "on_launch")
            self._add_separator(box)
            self._add_item(box, "Verify Files", "on_verify")
            self._add_item(box, "Open Folder", "on_open_folder")
            self._add_separator(box)
            self._add_item(box, "Uninstall", "on_uninstall")

    def _add_item(self, box: Gtk.Box, label: str, callback_key: str) -> None:
        btn = Gtk.Button(label=label)
        btn.add_css_class("flat")
        btn.set_halign(Gtk.Align.FILL)
        btn.set_hexpand(True)
        btn.connect("clicked", lambda *_: self._on_item(callback_key))
        box.append(btn)

    @staticmethod
    def _add_separator(box: Gtk.Box) -> None:
        sep = Gtk.Separator()
        sep.set_margin_top(4)
        sep.set_margin_bottom(4)
        box.append(sep)

    def _on_item(self, callback_key: str) -> None:
        cb = self._callbacks.get(callback_key)
        self._dismiss()
        if cb:
            cb(self._vm)
