# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""In-memory fake EventBus."""

from __future__ import annotations

from collections import defaultdict
from typing import Callable

from mythos.domain.events import DomainEvent
from mythos.ports.output import EventBus


class FakeEventBus(EventBus):
    """
    Records all published events and dispatches to subscribers.

    Useful both for unit-test assertions and for design mode (the GTK
    views subscribe to events here and still receive them).
    """

    def __init__(self) -> None:
        self.published: list[DomainEvent] = []
        self._handlers: dict[type, list[Callable]] = defaultdict(list)

    def publish(self, event: DomainEvent) -> None:
        self.published.append(event)
        for handler in list(self._handlers.get(type(event), [])):
            handler(event)

    def subscribe(self, event_type: type[DomainEvent], handler: Callable) -> None:
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: type[DomainEvent], handler: Callable) -> None:
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def events_of(self, event_type: type) -> list[DomainEvent]:
        """Helper for test assertions."""
        return [e for e in self.published if isinstance(e, event_type)]
