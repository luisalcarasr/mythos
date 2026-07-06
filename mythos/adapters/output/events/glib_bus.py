# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
GLibEventBus — EventBus that marshals handler calls onto the GLib main loop.

Domain events can be published from background threads (e.g. the
install download thread).  GTK is single-threaded, so any handler
that updates a widget MUST run on the GLib main loop.

This adapter wraps every handler call in ``GLib.idle_add()`` so the
caller never has to think about threading.

If GLib is not available (e.g. during unit tests), it falls back to
direct synchronous dispatch.
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from typing import Callable

from mythos.domain.events import DomainEvent
from mythos.ports.output import EventBus

logger = logging.getLogger(__name__)


def _idle_add_safe(fn: Callable, *args: object) -> None:
    """Call *fn* via ``GLib.idle_add`` when available; otherwise call directly."""
    try:
        from gi.repository import GLib  # type: ignore[import]
        GLib.idle_add(fn, *args)
    except ImportError:
        fn(*args)


class GLibEventBus(EventBus):
    """
    Thread-safe publish–subscribe bus that delivers events on the GLib
    main loop.

    Handlers are called with the ``DomainEvent`` instance as their sole
    argument.
    """

    def __init__(self) -> None:
        self._handlers: dict[type, list[Callable[[DomainEvent], None]]] = defaultdict(list)
        self._lock = threading.Lock()

    def publish(self, event: DomainEvent) -> None:
        event_type = type(event)
        with self._lock:
            handlers = list(self._handlers.get(event_type, []))

        logger.debug("Publishing %s to %d handler(s)", event_type.__name__, len(handlers))

        for handler in handlers:
            _idle_add_safe(handler, event)

    def subscribe(
        self,
        event_type: type[DomainEvent],
        handler: Callable[[DomainEvent], None],
    ) -> None:
        with self._lock:
            self._handlers[event_type].append(handler)
        logger.debug("Subscribed to %s", event_type.__name__)

    def unsubscribe(
        self,
        event_type: type[DomainEvent],
        handler: Callable[[DomainEvent], None],
    ) -> None:
        with self._lock:
            handlers = self._handlers.get(event_type, [])
            if handler in handlers:
                handlers.remove(handler)
