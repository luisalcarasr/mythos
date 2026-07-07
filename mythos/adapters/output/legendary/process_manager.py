from __future__ import annotations

import json
import logging
import os
import signal
from pathlib import Path
from typing import Set

logger = logging.getLogger(__name__)


class LegendaryProcessManager:
    _pids: Set[int] = set()
    _pids_file: Path | None = None

    @classmethod
    def _ensure_pids_file(cls) -> Path:
        if cls._pids_file is None:
            from mythos.config.paths import AppPaths
            cls._pids_file = AppPaths.config_dir / "legendary_pids.json"
        return cls._pids_file

    @classmethod
    def register_pid(cls, pid: int) -> None:
        cls._pids.add(pid)
        cls._persist()
        logger.debug("Registered legendary PID: %d", pid)

    @classmethod
    def unregister_pid(cls, pid: int) -> None:
        cls._pids.discard(pid)
        cls._persist()
        logger.debug("Unregistered legendary PID: %d", pid)

    @classmethod
    def _persist(cls) -> None:
        try:
            path = cls._ensure_pids_file()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(list(cls._pids)))
        except OSError as exc:
            logger.warning("Could not persist legendary PIDs: %s", exc)

    @classmethod
    def _load_persisted(cls) -> Set[int]:
        try:
            path = cls._ensure_pids_file()
            if path.exists():
                data = json.loads(path.read_text())
                return set(data)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not load persisted PIDs: %s", exc)
        return set()

    @classmethod
    def _clear_persisted(cls) -> None:
        try:
            path = cls._ensure_pids_file()
            if path.exists():
                path.unlink()
        except OSError as exc:
            logger.warning("Could not clear persisted PIDs: %s", exc)

    @classmethod
    def cleanup(cls) -> None:
        orphans = cls._load_persisted()
        all_pids = cls._pids | orphans

        if all_pids:
            logger.info(
                "Cleaning up %d legendary process(es)…", len(all_pids)
            )
            for pid in all_pids:
                try:
                    os.kill(pid, signal.SIGTERM)
                    logger.debug("Killed legendary PID: %d", pid)
                except ProcessLookupError:
                    pass

        cls._pids.clear()
        cls._clear_persisted()

        from mythos.adapters.output.legendary.lock_manager import force_clear_lock
        force_clear_lock()
