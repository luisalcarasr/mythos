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
        result = subprocess.run(
            [self._bin, *args],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"legendary {' '.join(args)} failed: {result.stderr.strip()}"
            )

    def stream(
        self,
        args: list[str],
        on_progress: Optional[Callable[[Progress], None]] = None,
    ) -> int:
        with subprocess.Popen(
            [self._bin, *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        ) as proc:
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                logger.debug("legendary: %s", line)
                if on_progress:
                    progress = self._parse_progress(line)
                    if progress:
                        on_progress(progress)
            proc.wait()
            return proc.returncode

    def run_and_check(
        self,
        args: list[str],
        on_progress: Optional[Callable[[Progress], None]] = None,
    ) -> None:
        if on_progress:
            rc = self.stream(args, on_progress=on_progress)
        else:
            rc = subprocess.run(
                [self._bin, *args],
                capture_output=True,
                text=True,
            ).returncode
        if rc != 0:
            raise RuntimeError(f"legendary {' '.join(args)} failed (exit={rc})")

    @staticmethod
    def _parse_progress(line: str) -> Optional[Progress]:
        match = _PROGRESS_RE.search(line)
        if not match:
            return None
        fraction = float(match.group(1)) / 100.0

        downloaded_bytes = 0
        total_bytes = 0
        speed_bps = 0.0
        eta_seconds = 0.0

        dm = _DOWNLOADED_RE.search(line)
        if dm:
            downloaded_bytes = _parse_size(float(dm.group(1)), dm.group(2))

        sm = _SPEED_RE.search(line)
        if sm:
            speed_bps = _parse_size(float(sm.group(1)), sm.group(2))

        em = _ETA_RE.search(line)
        if em:
            eta_seconds = (
                float(em.group(1)) * 3600
                + float(em.group(2)) * 60
                + float(em.group(3))
            )

        return Progress(
            fraction=fraction,
            downloaded_bytes=downloaded_bytes,
            total_bytes=total_bytes,
            speed_bps=speed_bps,
            eta_seconds=eta_seconds,
        )
