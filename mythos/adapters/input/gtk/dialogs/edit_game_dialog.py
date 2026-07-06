from __future__ import annotations

import logging
from typing import Callable, Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, Gtk

from mythos.adapters.input.gtk.view_models import GameViewModel

logger = logging.getLogger(__name__)


class EditGameDialog(Adw.Dialog):
    """
    Dialog for editing game metadata (title, cover image).

    The user can change the title and cover URL.  A preview of the
    current cover is shown on the right.  Saving calls ``on_save``
    with the new title and cover URL.
    """

    def __init__(
        self,
        vm: GameViewModel,
        on_save: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        super().__init__()
        self._vm = vm
        self._on_save = on_save

        self.set_title(f"Edit Game \u2014 {vm.title}")
        self.set_content_width(640)
        self.set_content_height(420)

        self._title_entry: Adw.EntryRow | None = None
        self._cover_entry: Adw.EntryRow | None = None
        self._preview: Gtk.Picture | None = None

        self._build()

    def _build(self) -> None:
        # Header bar
        header = Adw.HeaderBar()

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda *_: self.close())
        header.pack_start(cancel_btn)

        save_btn = Gtk.Button(label="Save")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._on_save_clicked)
        header.pack_end(save_btn)

        # Content
        content = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=24,
        )
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(24)
        content.set_margin_end(24)

        # Form (left)
        form = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        form.set_hexpand(True)

        self._title_entry = Adw.EntryRow(title="Title")
        self._title_entry.set_text(self._vm.title)
        self._title_entry.connect("changed", self._on_title_changed)
        form.append(self._title_entry)

        self._cover_entry = Adw.EntryRow(title="Cover URL")
        self._cover_entry.set_text(self._vm.cover_url or "")
        paste_btn = Gtk.Button(icon_name="edit-paste-symbolic")
        paste_btn.set_tooltip_text("Paste from clipboard")
        paste_btn.add_css_class("flat")
        paste_btn.connect("clicked", self._on_paste_cover)
        self._cover_entry.add_suffix(paste_btn)
        form.append(self._cover_entry)

        content.append(form)

        # Preview (right)
        preview_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
        )
        preview_box.set_size_request(180, -1)

        preview_label = Gtk.Label(label="Preview")
        preview_label.add_css_class("dim-label")
        preview_label.set_halign(Gtk.Align.START)
        preview_box.append(preview_label)

        self._preview = Gtk.Picture()
        self._preview.set_size_request(180, 240)
        self._preview.set_content_fit(Gtk.ContentFit.COVER)
        if self._vm.cover_path and self._vm.cover_path.exists():
            self._preview.set_filename(str(self._vm.cover_path))
        preview_box.append(self._preview)

        content.append(preview_box)

        # Layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.append(header)
        main_box.append(content)

        self.set_child(main_box)

    # -- Handlers ----------------------------------------------------- #

    def _on_title_changed(self, entry: Adw.EntryRow) -> None:
        logger.debug("Title changed: %s", entry.get_text())

    def _on_paste_cover(self, _btn: Gtk.Button) -> None:
        display = Gdk.Display.get_default()
        if not display:
            return
        clipboard = display.get_clipboard()
        clipboard.read_text_async(None, self._on_clipboard_text)

    def _on_clipboard_text(
        self, clipboard: Gdk.Clipboard, result: object
    ) -> None:
        try:
            text = clipboard.read_text_finish(result)
            if text and text.strip():
                self._cover_entry.set_text(text.strip())
                self._update_preview(text.strip())
        except Exception as exc:
            logger.debug("Clipboard paste failed: %s", exc)

    def _update_preview(self, url: str) -> None:
        if not self._preview or not url:
            return
        try:
            file = Gio.File.new_for_uri(url)
            self._preview.set_file(file)
        except Exception as exc:
            logger.debug("Preview load failed: %s", exc)

    def _on_save_clicked(self, _btn: Gtk.Button) -> None:
        new_title = self._title_entry.get_text().strip() if self._title_entry else ""
        new_cover = self._cover_entry.get_text().strip() if self._cover_entry else ""
        if self._on_save:
            self._on_save(new_title or self._vm.title, new_cover)
        self.close()
