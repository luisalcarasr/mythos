# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""AuthSessionRepository implemented via LegendaryCore."""

from __future__ import annotations

import logging
from typing import Optional

from mythos.adapters.output.legendary.core_gateway import LegendaryCoreGateway
from mythos.domain.exceptions import AuthenticationError, SessionExpiredError
from mythos.ports.output import AuthSessionRepository

logger = logging.getLogger(__name__)


class LegendaryAuthSession(AuthSessionRepository):
    """
    Delegates authentication to LegendaryCore.

    legendary stores its own session tokens in
    ``~/.config/legendary/user.json`` (or OS equivalent).
    """

    def __init__(self, gateway: LegendaryCoreGateway) -> None:
        self._gw = gateway

    def login_with_code(self, authorization_code: str) -> dict:
        """
        Exchange an Epic authorisation code for a session.

        legendary's ``auth_code()`` method does the OAuth exchange and
        persists the token automatically.  It returns ``False`` (instead
        of raising) when Epic rejects the code, so we must check the
        return value explicitly.
        """
        try:
            success = self._gw.core.auth_code(authorization_code)
        except Exception as exc:
            raise AuthenticationError(f"Login failed: {exc}") from exc

        if not success:
            raise AuthenticationError(
                "Epic rejected the authorisation code. "
                "The code may have already been used or has expired — "
                "please open the login page again and use the new code."
            )

        return self._build_session_dict()

    def logout(self) -> None:
        try:
            self._gw.core.logout()
        except Exception as exc:
            logger.warning("Logout error (ignored): %s", exc)

    def get_session(self) -> Optional[dict]:
        if not self.is_logged_in():
            return None
        return self._build_session_dict()

    def is_logged_in(self) -> bool:
        try:
            return bool(self._gw.core.login())
        except Exception:  # noqa: BLE001
            return False

    def _build_session_dict(self) -> dict:
        try:
            ud = self._gw.core.lgd.userdata
            if ud is None:
                raise AuthenticationError("Session data is empty after login.")
            return {
                "display_name": ud.get("displayName", ""),
                "account_id": ud.get("account_id", ""),
                "access_token": ud.get("access_token", ""),
            }
        except AuthenticationError:
            raise
        except Exception as exc:
            raise AuthenticationError(f"Could not read session data: {exc}") from exc
