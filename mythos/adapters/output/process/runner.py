# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
SubprocessRunner — runs long-lived processes and bridges output back
to the GLib main loop via the EventBus.

This adapter is responsible for:
  - Spawning background subprocesses (install workers, game processes).
  - Monitoring stdout / stderr without blocking the GLib main loop.
  - Publishing domain events (DownloadProgressed, GameStopped, etc.)
    via the EventBus so GTK views react without polling.
"""

from __future__ import annotations

import logging
import subprocess
import threading
from typing import Callable, Optional

from mythos.ports.output import EventBus

logger = logging.getLogger(__name__)


class SubprocessRunner:
    """
    Thread-based subprocess manager.

    Runs commands in daemon threads; callback *on_line* is called from
    that thread, so callers must use ``GLib.idle_add`` if they update
    GTK widgets.
    """

    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self._bus = event_bus
        self._active: dict[int, subprocess.Popen] = {}
        self._lock = threading.Lock()

    def run_background(
        self,
        command: list[str],
        on_line: Optional[Callable[[str], None]] = None,
        on_exit: Optional[Callable[[int], None]] = None,
        env: Optional[dict[str, str]] = None,
    ) -> int:
        """
        Start *command* in a background thread.

        Parameters
        ----------
        command:
            The command list passed to ``subprocess.Popen``.
        on_line:
            Called for each line of combined stdout/stderr output.
        on_exit:
            Called with the exit code when the process terminates.
        env:
            Extra environment variables merged with the current process
            environment.

        Returns
        -------
        int
            The PID of the spawned process.
        """
        import os

        merged_env = {**os.environ}
        if env:
            merged_env.update(env)

        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=merged_env,
        )

        with self._lock:
            self._active[proc.pid] = proc

        thread = threading.Thread(
            target=self._monitor,
            args=(proc, on_line, on_exit),
            daemon=True,
            name=f"runner-{proc.pid}",
        )
        thread.start()
        logger.debug("Started process PID=%d: %s", proc.pid, command[:3])
        return proc.pid

    def terminate(self, pid: int) -> None:
        """Send SIGTERM to a running process."""
        with self._lock:
            proc = self._active.get(pid)
        if proc:
            logger.debug("Terminating PID=%d", pid)
            proc.terminate()

    # ---------------------------------------------------------------- #
    # Private                                                            #
    # ---------------------------------------------------------------- #

    def _monitor(
        self,
        proc: subprocess.Popen,
        on_line: Optional[Callable[[str], None]],
        on_exit: Optional[Callable[[int], None]],
    ) -> None:
        try:
            for line in proc.stdout:  # type: ignore[union-attr]
                line = line.rstrip("\n")
                if on_line:
                    on_line(line)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Runner read error: %s", exc)
        finally:
            proc.wait()
            with self._lock:
                self._active.pop(proc.pid, None)
            if on_exit:
                on_exit(proc.returncode)
            logger.debug("Process PID=%d exited with code %d", proc.pid, proc.returncode)
