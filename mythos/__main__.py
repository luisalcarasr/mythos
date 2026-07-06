# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Application entry point.

    python -m mythos
    mythos               # after pip install

Bootstraps:
  1. XDG paths
  2. Logging
  3. i18n
  4. Dependency container (composition root)
  5. GTK4 / Adwaita application
"""

from __future__ import annotations

import logging
import os
import sys

# ---------------------------------------------------------------------------
# macOS: Homebrew GTK4 library path bootstrap
# ---------------------------------------------------------------------------
# On macOS with a python.org interpreter, dyld does not search /opt/homebrew
# by default.  PyGObject's C extension (_gi.so) is linked with an absolute
# rpath, but libgirepository resolves further libraries by bare name at
# runtime.  We must have DYLD_LIBRARY_PATH set *before the process starts*, so
# we re-exec ourselves with the correct environment if it is not already set.
# This is a no-op on Linux and on macOS when the user already set the var.
def _ensure_macos_gtk_env() -> None:
    import os
    if sys.platform != "darwin":
        return
    homebrew_lib = "/opt/homebrew/lib"
    if os.environ.get("DYLD_LIBRARY_PATH", "").startswith(homebrew_lib):
        return  # already set — nothing to do
    os.environ["DYLD_LIBRARY_PATH"] = homebrew_lib
    os.environ.setdefault(
        "GI_TYPELIB_PATH", f"{homebrew_lib}/girepository-1.0"
    )
    # Re-exec this process so dyld picks up the new DYLD_LIBRARY_PATH.
    os.execv(sys.executable, [sys.executable] + sys.argv)


_ensure_macos_gtk_env()


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


_DEV_FLAGS = frozenset(["--fake", "--reload"])

# Exit code used as a "please restart" signal between the inner process
# and the outer launcher loop.  Matches the convention used by Django /
# uvicorn / watchfiles.
_EXIT_RELOAD = 3


def _parse_dev_flags() -> tuple[bool, bool, list[str]]:
    """
    Return (fake_mode, reload_mode, cleaned_argv).

    Strips all Mythos-specific dev flags from argv before passing it to
    GTK so the framework does not choke on unknown options.

    fake_mode   — MYTHOS_FAKE env var or --fake flag
    reload_mode — MYTHOS_RELOAD env var or --reload flag
    """
    env_fake   = bool(os.environ.get("MYTHOS_FAKE",   "").strip())
    env_reload = bool(os.environ.get("MYTHOS_RELOAD", "").strip())
    flag_fake   = "--fake"   in sys.argv
    flag_reload = "--reload" in sys.argv
    cleaned = [a for a in sys.argv if a not in _DEV_FLAGS]
    return (env_fake or flag_fake), (env_reload or flag_reload), cleaned


def _run_with_reload(fake_mode: bool, clean_argv: list[str]) -> None:
    """
    Outer launcher loop for auto-reload mode.

    Spawns the current Python interpreter as a child process (passing
    ``_MYTHOS_CHILD=1`` so it skips this outer loop) and re-execs it
    whenever the child exits with ``_EXIT_RELOAD`` (3).
    """
    import subprocess

    _log = logging.getLogger("mythos.reload")

    env = os.environ.copy()
    env["_MYTHOS_CHILD"] = "1"
    # Propagate fake mode to the child process.
    if fake_mode:
        env["MYTHOS_FAKE"] = "1"

    cmd = [sys.executable, "-m", "mythos"] + clean_argv[1:]

    _log.info("Auto-reload launcher started (watching mythos/ for changes).")
    while True:
        result = subprocess.run(cmd, env=env)
        if result.returncode == _EXIT_RELOAD:
            _log.info("Change detected — reloading…")
            continue
        break  # clean exit or error — propagate


def main() -> int:
    _setup_logging()
    logger = logging.getLogger("mythos")

    fake_mode, reload_mode, clean_argv = _parse_dev_flags()

    # ---------------------------------------------------------------- #
    # Auto-reload: outer launcher loop                                   #
    # Runs only in the top-level process (not in the child it spawns).  #
    # ---------------------------------------------------------------- #
    if reload_mode and not os.environ.get("_MYTHOS_CHILD"):
        _run_with_reload(fake_mode, clean_argv)
        return 0

    # ---------------------------------------------------------------- #
    # Inner process (or plain run without --reload)                     #
    # ---------------------------------------------------------------- #

    # 1. XDG paths
    from mythos.config.paths import AppPaths
    AppPaths.ensure_all()

    # 2. i18n
    from mythos.config.i18n import setup as i18n_setup, get_system_language
    i18n_setup(get_system_language())

    # 3. Dependency container
    if fake_mode:
        logger.warning(
            "╔══════════════════════════════════════════╗\n"
            "║  FAKE / DESIGN MODE — no Epic connection ║\n"
            "╚══════════════════════════════════════════╝"
        )
        from mythos.config.container_fake import build_fake
        container = build_fake()
    else:
        from mythos.config.container import build
        container = build()

    # 4. GTK application
    try:
        import gi  # noqa: F401
    except ImportError:
        logger.critical(
            "PyGObject (gi) is not installed. "
            "Install it via your system package manager:\n"
            "  macOS:  brew install pygobject3 gtk4 libadwaita webkitgtk\n"
            "  Fedora: sudo dnf install python3-gobject gtk4 libadwaita\n"
            "  Debian: sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1"
        )
        return 1

    from mythos.adapters.input.gtk.application import MythosApplication
    app = MythosApplication(container=container)

    # 5. File watcher (only in child/plain reload mode)
    if reload_mode or os.environ.get("_MYTHOS_CHILD"):
        from mythos.dev.watcher import EXIT_RELOAD, FileWatcher
        from pathlib import Path
        from gi.repository import GLib

        watch_root = Path(__file__).parent  # mythos/

        def _on_change() -> None:
            logger.info("Source change detected — requesting reload.")
            app._reload_requested = True
            GLib.idle_add(app.quit)

        watcher = FileWatcher(watch_dir=watch_root, on_change=_on_change)
        watcher.start()

    exit_code = app.run(clean_argv)

    # Signal the outer loop to restart if the watcher requested it.
    if getattr(app, "_reload_requested", False):
        return _EXIT_RELOAD
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
