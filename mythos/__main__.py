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
import sys


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> int:
    _setup_logging()
    logger = logging.getLogger("mythos")

    # 1. XDG paths
    from mythos.config.paths import AppPaths
    AppPaths.ensure_all()

    # 2. i18n
    from mythos.config.i18n import setup as i18n_setup, get_system_language
    i18n_setup(get_system_language())

    # 3. Dependency container
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
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
