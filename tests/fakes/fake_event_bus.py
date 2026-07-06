# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""In-memory fake EventBus for testing."""

from __future__ import annotations

from collections import defaultdict
from typing import Callable

from mythos.domain.events import DomainEvent
from mythos.ports.output import EventBus


class FakeEventBus(EventBus):
    """Records all published events so tests can assert on them."""

    def __init__(self) -> None:
        self.published: list[DomainEvent] = []
        self._handlers: dict[type, list[Callable]] = defaultdict(list)

    def publish(self, event: DomainEvent) -> None:
        self.published.append(event)
        for handler in self._handlers.get(type(event), []):
            handler(event)

    def subscribe(self, event_type: type[DomainEvent], handler: Callable) -> None:
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: type[DomainEvent], handler: Callable) -> None:
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def events_of(self, event_type: type) -> list[DomainEvent]:
        return [e for e in self.published if isinstance(e, event_type)]
