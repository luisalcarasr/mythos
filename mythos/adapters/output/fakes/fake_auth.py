# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""In-memory fake AuthSessionRepository."""

from __future__ import annotations

from typing import Optional

from mythos.ports.output import AuthSessionRepository


class FakeAuthSession(AuthSessionRepository):
    """
    In-memory auth session.

    Pass ``logged_in=True`` to start with an existing session (skips
    the login dialog in design mode).
    """

    def __init__(
        self,
        logged_in: bool = False,
        display_name: str = "Demo User",
        account_id: str = "demo-account-001",
    ) -> None:
        self._session: Optional[dict] = (
            {
                "display_name": display_name,
                "account_id": account_id,
                "access_token": "fake-token-aabbccdd",
            }
            if logged_in
            else None
        )

    def login_with_code(self, authorization_code: str) -> dict:
        self._session = {
            "display_name": "Demo User",
            "account_id": "demo-account-001",
            "access_token": f"fake-token-{authorization_code[:8]}",
        }
        return self._session

    def logout(self) -> None:
        self._session = None

    def get_session(self) -> Optional[dict]:
        return self._session

    def is_logged_in(self) -> bool:
        return self._session is not None
