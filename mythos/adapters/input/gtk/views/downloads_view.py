# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
DownloadsView — vertical stack of DownloadCards.

Each active download (game install/update/repair or Proton runner
install) gets its own DownloadCard with thumbnail, title, progress
bar, pause/play button, cancel button, and a stats line.

The view:
  - Pre-populates from ``download_queue_port.list_tasks()`` on build.
  - Subscribes to domain events to add / update / remove cards live.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from mythos.adapters.input.gtk.view_models import DownloadTaskViewModel  # noqa: E402
from mythos.adapters.input.gtk.widgets.download_card import DownloadCard  # noqa: E402
from mythos.config.container import Container  # noqa: E402
from mythos.domain.entities import DownloadTask  # noqa: E402
from mythos.domain.events import (  # noqa: E402
    DownloadCancelled,
    DownloadCompleted,
    DownloadEnqueued,
    DownloadFailed,
    DownloadPaused,
    DownloadProgressed,
    DownloadResumed,
)
from mythos.domain.value_objects import AppName, GameStatus  # noqa: E402

logger = logging.getLogger(__name__)

def _vm_from_task(task: DownloadTask, image_cache=None) -> DownloadTaskViewModel:
    vm = DownloadTaskViewModel.from_task(task)
    if image_cache:
        try:
            vm.thumbnail_path = image_cache.get(task.app_name)
        except Exception:
            pass
    return vm


class DownloadsView(Gtk.Box):
    def __init__(self, container: Container) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._c = container
        self._cards: dict[str, DownloadCard] = {}

        self._build_ui()
        self._subscribe_events()
        self._prepopulate()

    # ---------------------------------------------------------------- #
    # UI construction                                                    #
    # ---------------------------------------------------------------- #

    def _build_ui(self) -> None:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        self.append(scrolled)

        # Clamp content to a reasonable max-width
        clamp = Adw.Clamp()
        clamp.set_maximum_size(1080)
        clamp.set_valign(Gtk.Align.START)
        clamp.set_margin_top(16)
        clamp.set_margin_bottom(16)
        scrolled.set_child(clamp)

        self._stack = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._stack.set_margin_start(16)
        self._stack.set_margin_end(16)
        self._stack.set_valign(Gtk.Align.START)
        self._stack.set_vexpand(False)
        self._stack.set_vexpand_set(True)
        clamp.set_child(self._stack)

        self._empty = Adw.StatusPage()
        self._empty.set_icon_name("folder-download-symbolic")
        self._empty.set_title("No active downloads")
        self._empty.set_description(
            "Install a game from the Library to start downloading."
        )
        self._empty.set_vexpand(True)
        self.append(self._empty)

        self._update_empty_state()

    def _subscribe_events(self) -> None:
        bus = self._c.event_bus
        bus.subscribe(DownloadEnqueued, self._on_enqueued)
        bus.subscribe(DownloadProgressed, self._on_progress)
        bus.subscribe(DownloadPaused, self._on_paused)
        bus.subscribe(DownloadResumed, self._on_resumed)
        bus.subscribe(DownloadCompleted, self._on_completed)
        bus.subscribe(DownloadFailed, self._on_failed)
        bus.subscribe(DownloadCancelled, self._on_cancelled)
    def _prepopulate(self) -> None:
        """Show tasks already in the queue when the view is first created."""
        try:
            queue = self._c.download_queue_port
            if queue is None:
                return
            for task in queue.list_tasks():
                vm = _vm_from_task(task, self._c.image_cache_port)
                self._add_card(vm)
        except Exception as exc:
            logger.warning("Could not pre-populate downloads: %s", exc)

    # ---------------------------------------------------------------- #
    # Card management                                                    #
    # ---------------------------------------------------------------- #

    def _add_card(self, vm: DownloadTaskViewModel) -> DownloadCard:
        card = DownloadCard(
            vm=vm,
            on_pause=self._handle_pause,
            on_cancel=self._handle_cancel,
        )
        self._cards[vm.task_id] = card
        self._stack.append(card)
        self._update_empty_state()
        return card

    def _update_empty_state(self) -> None:
        has_cards = bool(self._cards)
        self._stack.set_visible(has_cards)
        self._empty.set_visible(not has_cards)

    # ---------------------------------------------------------------- #
    # Pause / cancel callbacks (from card buttons)                       #
    # ---------------------------------------------------------------- #

    def _handle_pause(self, task_id: str) -> None:
        card = self._cards.get(task_id)
        if card is None:
            return
        # Toggle between pause and resume
        if card._paused:
            try:
                self._c.resume_download_use_case.execute(task_id)
            except Exception as exc:
                logger.error("Resume failed: %s", exc)
        else:
            try:
                self._c.pause_download_use_case.execute(task_id)
            except Exception as exc:
                logger.error("Pause failed: %s", exc)

    def _handle_cancel(self, task_id: str) -> None:
        try:
            self._c.cancel_download_use_case.execute(task_id)
        except Exception as exc:
            logger.error("Cancel failed: %s", exc)
            # Remove the card immediately so the UI is responsive
            self._remove_card(task_id)

    def _remove_card(self, task_id: str) -> None:
        card = self._cards.pop(task_id, None)
        if card:
            self._stack.remove(card)
        self._update_empty_state()

    # ---------------------------------------------------------------- #
    # Game download event handlers                                       #
    # ---------------------------------------------------------------- #

    def _on_enqueued(self, event: DownloadEnqueued) -> None:
        image_cache = self._c.image_cache_port
        thumbnail: Optional[Path] = None
        if image_cache:
            try:
                thumbnail = image_cache.get(AppName(event.app_name))
            except Exception:
                pass

        from mythos.domain.value_objects import Progress
        p = Progress(total_bytes=event.total_bytes)
        vm = DownloadTaskViewModel(
            task_id=event.task_id,
            app_name=event.app_name,
            title=event.title or event.app_name,
            kind=event.kind,
            percent=0,
            fraction=0.0,
            speed_human="",
            downloaded_human=p.downloaded_human,
            total_human=p.total_human,
            eta_human="—",
            status=GameStatus.QUEUED,
            error_message="",
            thumbnail_path=thumbnail,
        )
        self._add_card(vm)

    def _on_progress(self, event: DownloadProgressed) -> None:
        card = self._cards.get(event.task_id)
        if card and event.progress:
            p = event.progress
            vm = DownloadTaskViewModel(
                task_id=event.task_id,
                app_name=event.app_name,
                title=card._vm.title,
                kind=card._vm.kind,
                percent=p.percent,
                fraction=p.fraction,
                speed_human=p.speed_human(),
                downloaded_human=p.downloaded_human,
                total_human=p.total_human,
                eta_human=p.eta_human,
                status=GameStatus.INSTALLING,
                error_message="",
                is_runner=card._vm.is_runner,
                thumbnail_path=card._vm.thumbnail_path,
            )
            card.update_progress(vm)

    def _on_paused(self, event: DownloadPaused) -> None:
        card = self._cards.get(event.task_id)
        if card:
            card.set_paused(True)

    def _on_resumed(self, event: DownloadResumed) -> None:
        card = self._cards.get(event.task_id)
        if card:
            card.set_paused(False)

    def _on_completed(self, event: DownloadCompleted) -> None:
        card = self._cards.get(event.task_id)
        if card:
            card.mark_done()

    def _on_failed(self, event: DownloadFailed) -> None:
        card = self._cards.get(event.task_id)
        if card:
            card.mark_failed(event.reason)

    def _on_cancelled(self, event: DownloadCancelled) -> None:
        self._remove_card(event.task_id)


