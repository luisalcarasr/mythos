from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_LOCK_FILES = ["installed.json.lock", "user.json.lock"]


def _legendary_config_dir() -> Path:
    xdg_config = os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
    return Path(xdg_config) / "legendary"


def has_lock() -> bool:
    conf = _legendary_config_dir()
    return any((conf / name).exists() for name in _LOCK_FILES)


def is_legendary_running() -> bool:
    try:
        result = subprocess.run(
            ["pgrep", "-x", "legendary"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def can_clear_lock() -> bool:
    return has_lock() and not is_legendary_running()


def clear_lock() -> None:
    conf = _legendary_config_dir()
    for name in _LOCK_FILES:
        path = conf / name
        if path.exists():
            try:
                path.unlink()
                logger.info("Cleared orphaned legendary lock: %s", path)
            except OSError as exc:
                logger.warning("Could not remove lock %s: %s", path, exc)


def force_clear_lock() -> None:
    """Kill any orphaned legendary processes and clear lock files."""
    logger.warning("Force-clearing legendary locks…")
    try:
        subprocess.run(
            ["pkill", "-x", "legendary"],
            capture_output=True,
            timeout=5,
        )
        logger.info("Killed orphaned legendary process(es)")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    clear_lock()
