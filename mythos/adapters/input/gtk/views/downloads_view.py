# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
DownloadsView — real-time download queue.

Subscribes to domain events (DownloadProgressed, DownloadCompleted,
DownloadFailed, DownloadEnqueued) via the EventBus and updates rows
on the GLib main loop.
"""

from __future__ import annotations

import logging

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from mythos.config.container import Container  # noqa: E402
from mythos.domain.events import (  # noqa: E402
    DownloadCancelled,
    DownloadCompleted,
    DownloadEnqueued,
    DownloadFailed,
    DownloadProgressed,
)

logger = logging.getLogger(__name__)


class _DownloadRow(Adw.ActionRow):
    """A single row representing a queued or active download."""

    def __init__(self, task_id: str, app_name: str, kind: str) -> None:
        super().__init__()
        self.task_id = task_id
        self.set_title(app_name)
        self.set_subtitle(kind.capitalize())

        self._progress = Gtk.ProgressBar()
        self._progress.set_valign(Gtk.Align.CENTER)
        self._progress.set_hexpand(True)
        self._progress.set_show_text(True)
        self.add_suffix(self._progress)

        self._status = Gtk.Label()
        self._status.add_css_class("dim-label")
        self.add_suffix(self._status)

    def update_progress(self, fraction: float, speed: str) -> None:
        self._progress.set_fraction(fraction)
        self._progress.set_text(f"{int(fraction * 100)}%  {speed}")

    def mark_done(self) -> None:
        self._progress.set_fraction(1.0)
        self._progress.set_text("Complete")
        self._status.set_text("✓")

    def mark_failed(self, reason: str) -> None:
        self._progress.set_text("Failed")
        self._status.set_markup(f'<span color="red">✗</span>')
        self.set_subtitle(reason[:60])


class DownloadsView(Gtk.Box):
    def __init__(self, container: Container) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._c = container
        self._rows: dict[str, _DownloadRow] = {}

        self._build_ui()
        self._subscribe_events()

    def _build_ui(self) -> None:
        # Header
        label = Gtk.Label(label="Download Queue")
        label.add_css_class("title-2")
        label.set_margin_top(16)
        label.set_margin_start(16)
        label.set_xalign(0)
        self.append(label)

        self.append(Gtk.Separator())

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        self.append(scrolled)

        self._list = Gtk.ListBox()
        self._list.set_selection_mode(Gtk.SelectionMode.NONE)
        self._list.add_css_class("boxed-list")
        self._list.set_margin_top(12)
        self._list.set_margin_bottom(12)
        self._list.set_margin_start(12)
        self._list.set_margin_end(12)
        scrolled.set_child(self._list)

        self._empty = Adw.StatusPage()
        self._empty.set_icon_name("folder-download-symbolic")
        self._empty.set_title("No active downloads")
        self._empty.set_description("Install a game from the Library to start downloading.")
        self._empty.set_vexpand(True)
        self.append(self._empty)

    def _subscribe_events(self) -> None:
        bus = self._c.event_bus
        bus.subscribe(DownloadEnqueued, self._on_enqueued)
        bus.subscribe(DownloadProgressed, self._on_progress)
        bus.subscribe(DownloadCompleted, self._on_completed)
        bus.subscribe(DownloadFailed, self._on_failed)
        bus.subscribe(DownloadCancelled, self._on_cancelled)

    # ---------------------------------------------------------------- #
    # Event handlers (run on GLib main loop via GLibEventBus)           #
    # ---------------------------------------------------------------- #

    def _on_enqueued(self, event: DownloadEnqueued) -> None:  # type: ignore[name-defined]
        row = _DownloadRow(event.task_id, event.app_name, event.kind)
        self._rows[event.task_id] = row
        self._list.append(row)
        self._empty.set_visible(False)
        self._list.set_visible(True)

    def _on_progress(self, event: DownloadProgressed) -> None:  # type: ignore[name-defined]
        row = self._rows.get(event.task_id)
        if row and event.progress:
            row.update_progress(event.progress.fraction, event.progress.speed_human())

    def _on_completed(self, event: DownloadCompleted) -> None:  # type: ignore[name-defined]
        row = self._rows.get(event.task_id)
        if row:
            row.mark_done()

    def _on_failed(self, event: DownloadFailed) -> None:  # type: ignore[name-defined]
        row = self._rows.get(event.task_id)
        if row:
            row.mark_failed(event.reason)

    def _on_cancelled(self, event: DownloadCancelled) -> None:  # type: ignore[name-defined]
        row = self._rows.pop(event.task_id, None)
        if row:
            self._list.remove(row)
        if not self._rows:
            self._empty.set_visible(True)
            self._list.set_visible(False)
