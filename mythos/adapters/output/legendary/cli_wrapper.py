from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Any, Callable, Optional

from mythos.domain.value_objects import Progress

logger = logging.getLogger(__name__)

_PROGRESS_RE = re.compile(r"Progress:\s+([\d.]+)%")
_DOWNLOADED_RE = re.compile(r"Downloaded:\s+([\d.]+)\s+([A-Za-z]+)")
_SPEED_RE = re.compile(r"Download\s+-\s+([\d.]+)\s+([A-Za-z]+)/s")
_ETA_RE = re.compile(r"ETA:\s+(\d{2}):(\d{2}):(\d{2})")
_LOCK_ERROR_RE = re.compile(r"Failed to acquire installed data lock")

_SIZE_MULTIPLIERS: dict[str, int] = {
    "B": 1,
    "KiB": 1024,
    "MiB": 1024 * 1024,
    "GiB": 1024 * 1024 * 1024,
}


def _parse_size(value: float, unit: str) -> int:
    return int(value * _SIZE_MULTIPLIERS.get(unit, 1))


class LegendaryCliWrapper:
    def __init__(self, legendary_bin: str = "legendary") -> None:
        self._bin = legendary_bin
        self._last_downloaded: int = 0
        self._last_speed_bps: float = 0.0
        self._last_eta_seconds: float = 0.0

    def run_json(self, args: list[str]) -> Any:
        result = subprocess.run(
            [self._bin, *args],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"legendary {' '.join(args)} failed: {result.stderr.strip()}"
            )
        stdout = result.stdout
        stripped = stdout.lstrip()
        if stripped.startswith("["):
            json_end = stdout.rfind("]")
            return json.loads(stdout[: json_end + 1])
        if stripped.startswith("{"):
            json_end = stdout.rfind("}")
            return json.loads(stdout[: json_end + 1])
        raise RuntimeError(f"No JSON found in legendary output: {stdout[:500]}")

    def run(self, args: list[str]) -> None:
        self._run(args, retried=False)

    def _run(self, args: list[str], retried: bool = False) -> None:
        proc = subprocess.Popen(
            [self._bin, *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        from mythos.adapters.output.legendary.process_manager import LegendaryProcessManager
        LegendaryProcessManager.register_pid(proc.pid)
        try:
            stdout, stderr = proc.communicate()
            if proc.returncode != 0:
                if not retried and _LOCK_ERROR_RE.search(stderr):
                    from mythos.adapters.output.legendary.lock_manager import force_clear_lock
                    force_clear_lock()
                    self._run(args, retried=True)
                    return
                raise RuntimeError(
                    f"legendary {' '.join(args)} failed: {stderr.strip()}"
                )
        finally:
            LegendaryProcessManager.unregister_pid(proc.pid)

    def run_and_check(
        self,
        args: list[str],
        on_progress: Optional[Callable[[Progress], None]] = None,
    ) -> None:
        if on_progress:
            rc, lines = self._stream(args, on_progress=on_progress)
            output = "\n".join(lines)
            if rc != 0:
                if _LOCK_ERROR_RE.search(output):
                    from mythos.adapters.output.legendary.lock_manager import force_clear_lock
                    force_clear_lock()
                    rc, lines = self._stream(args, on_progress=on_progress)
                    output = "\n".join(lines)
                if rc != 0:
                    raise RuntimeError(
                        f"legendary {' '.join(args)} failed (exit={rc}): {output[:500]}"
                    )
        else:
            self._run(args)

    def _stream(
        self,
        args: list[str],
        on_progress: Optional[Callable[[Progress], None]] = None,
    ) -> tuple[int, list[str]]:
        self._last_downloaded = 0
        self._last_speed_bps = 0.0
        self._last_eta_seconds = 0.0

        collected: list[str] = []
        proc = subprocess.Popen(
            [self._bin, *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        from mythos.adapters.output.legendary.process_manager import LegendaryProcessManager
        LegendaryProcessManager.register_pid(proc.pid)
        try:
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                collected.append(line)
                logger.debug("legendary: %s", line)
                if on_progress:
                    progress = self._parse_progress(line)
                    if progress:
                        on_progress(progress)
            proc.wait()
            return proc.returncode, collected
        finally:
            LegendaryProcessManager.unregister_pid(proc.pid)

    def _parse_progress(self, line: str) -> Optional[Progress]:
        dm = _DOWNLOADED_RE.search(line)
        if dm:
            self._last_downloaded = _parse_size(float(dm.group(1)), dm.group(2))

        sm = _SPEED_RE.search(line)
        if sm:
            self._last_speed_bps = _parse_size(float(sm.group(1)), sm.group(2))

        em = _ETA_RE.search(line)
        if em:
            self._last_eta_seconds = (
                float(em.group(1)) * 3600
                + float(em.group(2)) * 60
                + float(em.group(3))
            )

        pm = _PROGRESS_RE.search(line)
        if not pm:
            return None

        return Progress(
            fraction=float(pm.group(1)) / 100.0,
            downloaded_bytes=self._last_downloaded,
            total_bytes=0,
            speed_bps=self._last_speed_bps,
            eta_seconds=self._last_eta_seconds,
        )
