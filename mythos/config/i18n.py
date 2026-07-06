# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Internationalisation bootstrap.

Uses Python's built-in `gettext` module pointing at the ``po/`` directory
compiled into ``locale/<lang>/LC_MESSAGES/mythos.mo`` files.

Usage anywhere in the codebase::

    from mythos.config.i18n import _
    label = _("Install")
"""

from __future__ import annotations

import gettext
import locale
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_LOCALE_DIR = Path(__file__).parent.parent.parent / "locale"
_DOMAIN = "mythos"

_translation: gettext.NullTranslations | None = None


def setup(language: str | None = None) -> None:
    """
    Initialise gettext translations.

    Parameters
    ----------
    language:
        ISO 639-1 language code (e.g. ``"es"``, ``"en"``). When *None* the
        system locale is used.
    """
    global _translation

    languages = [language] if language else None

    try:
        _translation = gettext.translation(
            domain=_DOMAIN,
            localedir=_LOCALE_DIR,
            languages=languages,
            fallback=True,
        )
        _translation.install()
        logger.debug("Loaded translations for language=%s", language or "system")
    except Exception:  # noqa: BLE001
        logger.warning("Could not load translations; falling back to source strings.")
        _translation = gettext.NullTranslations()
        _translation.install()


def _(message: str) -> str:  # noqa: N802
    """Translate *message* using the active locale."""
    if _translation is None:
        setup()
    return _translation.gettext(message)  # type: ignore[union-attr]


def get_system_language() -> str:
    """Return the two-letter system language code (e.g. ``'es'``)."""
    try:
        lang, _ = locale.getlocale()
        if lang:
            return lang[:2]
    except Exception:  # noqa: BLE001
        pass
    return "en"
