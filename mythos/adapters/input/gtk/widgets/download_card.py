# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
DownloadCard — a rich card widget for the Downloads view.

Layout
------
┌──────────────────────────────────────────────────────────────┐
│ [thumb]  Title                               [⏸/▶]  [✕]    │
│          ▓▓▓▓▓▓▓▓▓▓░░░░░░  62%                               │
│          12.3 GB / 65 GB  ·  45 MB/s  ·  7m 30s             │
└──────────────────────────────────────────────────────────────┘

- Thumbnail (left, 80×80, rounded): portrait cover for games,
  symbolic icon for runners.
- Pause/play button and cancel button in the top-right corner.
- Progress bar below the title.
- Single-line stats label (downloaded / total · speed · ETA).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk  # noqa: E402

from mythos.adapters.input.gtk.view_models import DownloadTaskViewModel  # noqa: E402

logger = logging.getLogger(__name__)

_THUMB_SIZE = 80


class DownloadCard(Gtk.Box):
    """
    Rich download card.

    Parameters
    ----------
    vm:
        Initial view-model state.
    on_pause:
        Called with ``task_id`` when the pause/resume button is clicked.
    on_cancel:
        Called with ``task_id`` when the cancel button is clicked.
    """

    def __init__(
        self,
        vm: DownloadTaskViewModel,
        on_pause: Optional[Callable[[str], None]] = None,
        on_cancel: Optional[Callable[[str], None]] = None,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self._vm = vm
        self._on_pause = on_pause
        self._on_cancel = on_cancel
        self._paused = vm.is_paused

        self.set_valign(Gtk.Align.START)
        self.set_vexpand(False)
        self.set_vexpand_set(True)
        self.add_css_class("download-card")
        self._build()

    # ---------------------------------------------------------------- #
    # Build                                                              #
    # ---------------------------------------------------------------- #

    def _build(self) -> None:
        # -- Thumbnail ------------------------------------------------ #
        self._thumb = Gtk.Box()
        self._thumb.set_size_request(_THUMB_SIZE, _THUMB_SIZE)
        self._thumb.set_halign(Gtk.Align.START)
        self._thumb.set_valign(Gtk.Align.CENTER)
        self._thumb.set_vexpand(False)
        self._thumb.set_vexpand_set(True)
        self._thumb.add_css_class("download-card-thumb")

        if self._vm.is_runner or self._vm.thumbnail_path is None:
            icon = Gtk.Image.new_from_icon_name("application-x-executable-symbolic")
            icon.set_pixel_size(40)
            icon.set_halign(Gtk.Align.CENTER)
            icon.set_valign(Gtk.Align.CENTER)
            self._thumb.append(icon)
        else:
            picture = Gtk.Picture()
            picture.set_filename(str(self._vm.thumbnail_path))
            picture.set_content_fit(Gtk.ContentFit.COVER)
            picture.set_size_request(_THUMB_SIZE, _THUMB_SIZE)
            self._thumb.append(picture)

        self.append(self._thumb)

        # -- Content area --------------------------------------------- #
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        content.set_hexpand(True)
        content.set_valign(Gtk.Align.CENTER)
        content.set_margin_start(14)
        content.set_margin_end(8)
        content.set_margin_top(12)
        content.set_margin_bottom(12)

        # Title row (title + buttons)
        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        title_row.set_hexpand(True)

        self._title_label = Gtk.Label(label=self._vm.title)
        self._title_label.set_xalign(0)
        self._title_label.set_hexpand(True)
        self._title_label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        self._title_label.add_css_class("download-card-title")
        title_row.append(self._title_label)

        # Kind badge
        kind_label = Gtk.Label(label=self._vm.kind.capitalize())
        kind_label.add_css_class("download-card-kind")
        kind_label.add_css_class("dim-label")
        title_row.append(kind_label)

        # Pause/play button
        self._pause_btn = Gtk.Button()
        self._pause_btn.set_icon_name(
            "media-playback-start-symbolic" if self._paused
            else "media-playback-pause-symbolic"
        )
        self._pause_btn.add_css_class("flat")
        self._pause_btn.add_css_class("circular")
        self._pause_btn.set_tooltip_text("Resume" if self._paused else "Pause")
        self._pause_btn.connect("clicked", self._on_pause_clicked)
        title_row.append(self._pause_btn)

        # Cancel button
        cancel_btn = Gtk.Button(icon_name="window-close-symbolic")
        cancel_btn.add_css_class("flat")
        cancel_btn.add_css_class("circular")
        cancel_btn.set_tooltip_text("Cancel")
        cancel_btn.connect("clicked", self._on_cancel_clicked)
        title_row.append(cancel_btn)

        content.append(title_row)

        # Progress bar
        self._progress = Gtk.ProgressBar()
        self._progress.set_fraction(self._vm.fraction)
        self._progress.set_show_text(True)
        self._progress.set_text(f"{self._vm.percent}%")
        self._progress.set_hexpand(True)
        self._progress.add_css_class("download-card-progress")
        content.append(self._progress)

        # Stats line
        self._stats_label = Gtk.Label(label=self._vm.stats_line())
        self._stats_label.set_xalign(0)
        self._stats_label.set_ellipsize(3)
        self._stats_label.add_css_class("dim-label")
        self._stats_label.add_css_class("caption")
        content.append(self._stats_label)

        self.append(content)

    # ---------------------------------------------------------------- #
    # Public update API                                                  #
    # ---------------------------------------------------------------- #

    def update_progress(self, vm: DownloadTaskViewModel) -> None:
        """Refresh all dynamic fields from an updated view-model."""
        self._vm = vm
        self._progress.set_fraction(vm.fraction)
        self._progress.set_text(f"{vm.percent}%")
        self._stats_label.set_label(vm.stats_line())

    def set_paused(self, paused: bool) -> None:
        self._paused = paused
        self._pause_btn.set_icon_name(
            "media-playback-start-symbolic" if paused
            else "media-playback-pause-symbolic"
        )
        self._pause_btn.set_tooltip_text("Resume" if paused else "Pause")

    def mark_done(self) -> None:
        self._progress.set_fraction(1.0)
        self._progress.set_text("Complete")
        self._stats_label.set_label(f"{self._vm.total_human} — Complete")
        self._pause_btn.set_sensitive(False)

    def mark_failed(self, reason: str) -> None:
        self._progress.set_text("Failed")
        self._stats_label.set_label(reason[:80])
        self._stats_label.add_css_class("error")
        self._pause_btn.set_sensitive(False)

    def set_thumbnail(self, path: Optional[Path]) -> None:
        """Hot-swap the thumbnail once the image cache has it."""
        if path is None or not path.exists():
            return
        # Replace the icon with a picture — recreate thumb contents
        child = self._thumb.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self._thumb.remove(child)
            child = nxt
        picture = Gtk.Picture()
        picture.set_filename(str(path))
        picture.set_content_fit(Gtk.ContentFit.COVER)
        picture.set_size_request(_THUMB_SIZE, _THUMB_SIZE)
        self._thumb.append(picture)

    # ---------------------------------------------------------------- #
    # Button handlers                                                    #
    # ---------------------------------------------------------------- #

    def _on_pause_clicked(self, _btn: Gtk.Button) -> None:
        if self._on_pause:
            self._on_pause(self._vm.task_id)

    def _on_cancel_clicked(self, _btn: Gtk.Button) -> None:
        if self._on_cancel:
            self._on_cancel(self._vm.task_id)
