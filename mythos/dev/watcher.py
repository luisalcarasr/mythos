# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
File-system watcher for the auto-reload dev mode.

Polls ``mythos/`` recursively for changes to ``*.py`` files using
``os.stat`` — no third-party dependencies needed.  When a change is
detected it schedules ``app.quit()`` on the GLib main loop and marks
the process exit code as ``_EXIT_RELOAD`` (3) so the outer launcher
loop re-execs the process.

Architecture
------------
The watcher runs in a daemon thread so it never blocks the GTK loop.
Communication back to GTK is done exclusively through ``GLib.idle_add``
so there are no threading / GIL issues.

Exit codes
----------
0  — clean exit (user closed the window)
1  — error
3  — reload requested (re-exec the process)
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Sentinel exit code recognised by the outer launcher loop.
EXIT_RELOAD = 3

# How often to check for changes (seconds).
_POLL_INTERVAL = 0.8


def _collect_mtimes(root: Path) -> dict[Path, float]:
    """Return a mapping of path → mtime for every .py file under *root*."""
    mtimes: dict[Path, float] = {}
    for path in root.rglob("*.py"):
        try:
            mtimes[path] = path.stat().st_mtime
        except OSError:
            pass
    return mtimes


class FileWatcher:
    """
    Watches a directory tree for ``*.py`` changes.

    Parameters
    ----------
    watch_dir:
        Root of the source tree to monitor (typically ``mythos/``).
    on_change:
        Callable invoked (from the watcher thread) when a change is
        detected.  Should be thread-safe; use ``GLib.idle_add`` inside.
    poll_interval:
        Seconds between each scan.
    """

    def __init__(
        self,
        watch_dir: Path,
        on_change: callable,
        poll_interval: float = _POLL_INTERVAL,
    ) -> None:
        self._root = watch_dir
        self._on_change = on_change
        self._interval = poll_interval
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the watcher daemon thread."""
        self._thread = threading.Thread(
            target=self._run,
            name="mythos-watcher",
            daemon=True,
        )
        self._thread.start()
        logger.info("Auto-reload watcher started (watching %s)", self._root)

    def stop(self) -> None:
        self._stop.set()

    # ---------------------------------------------------------------- #
    # Internal                                                           #
    # ---------------------------------------------------------------- #

    def _run(self) -> None:
        snapshot = _collect_mtimes(self._root)
        while not self._stop.is_set():
            time.sleep(self._interval)
            current = _collect_mtimes(self._root)
            changed = self._diff(snapshot, current)
            if changed:
                rel = [str(p.relative_to(self._root)) for p in changed]
                logger.info("Reload triggered by: %s", ", ".join(rel))
                self._on_change()
                return  # hand off; the process will be re-execed
            snapshot = current

    @staticmethod
    def _diff(old: dict[Path, float], new: dict[Path, float]) -> list[Path]:
        """Return paths that are new, deleted, or modified."""
        changed: list[Path] = []
        for path, mtime in new.items():
            if old.get(path) != mtime:
                changed.append(path)
        for path in old:
            if path not in new:
                changed.append(path)
        return changed
