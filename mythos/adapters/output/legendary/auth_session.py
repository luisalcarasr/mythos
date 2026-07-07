from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from mythos.adapters.output.legendary.cli_wrapper import LegendaryCliWrapper
from mythos.domain.exceptions import AuthenticationError
from mythos.ports.output import AuthSessionRepository

logger = logging.getLogger(__name__)

_USER_JSON_PATH = Path.home() / ".config" / "legendary" / "user.json"


class LegendaryAuthSession(AuthSessionRepository):
    def __init__(self, cli: Optional[LegendaryCliWrapper] = None) -> None:
        self._cli = cli or LegendaryCliWrapper()

    def login_with_code(self, authorization_code: str) -> dict:
        try:
            self._cli.run(["auth", "--code", authorization_code])
        except Exception as exc:
            raise AuthenticationError(f"Login failed: {exc}") from exc

        session = self._build_session_dict()
        if not session:
            raise AuthenticationError(
                "Epic rejected the authorisation code. "
                "The code may have already been used or has expired — "
                "please open the login page again and use the new code."
            )
        return session

    def logout(self) -> None:
        try:
            self._cli.run(["auth", "--delete"])
        except Exception as exc:
            logger.warning("Logout error (ignored): %s", exc)

    def get_session(self) -> Optional[dict]:
        if not self.is_logged_in():
            return None
        return self._build_session_dict()

    def is_logged_in(self) -> bool:
        if not _USER_JSON_PATH.exists():
            return False
        try:
            data = json.loads(_USER_JSON_PATH.read_text())
            return bool(data.get("access_token"))
        except Exception:
            return False

    def _build_session_dict(self) -> Optional[dict]:
        try:
            if not _USER_JSON_PATH.exists():
                return None
            ud = json.loads(_USER_JSON_PATH.read_text())
            return {
                "display_name": ud.get("displayName", ""),
                "account_id": ud.get("account_id", ""),
                "access_token": ud.get("access_token", ""),
            }
        except Exception as exc:
            logger.error("Could not read session data: %s", exc)
            return None
