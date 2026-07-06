# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""In-memory fake AuthSessionRepository."""

from __future__ import annotations

from typing import Optional

from mythos.ports.output import AuthSessionRepository


class FakeAuthSession(AuthSessionRepository):
    def __init__(self, logged_in: bool = False) -> None:
        self._session: Optional[dict] = (
            {"display_name": "TestUser", "account_id": "abc123", "access_token": "tok"}
            if logged_in
            else None
        )

    def login_with_code(self, authorization_code: str) -> dict:
        self._session = {
            "display_name": "TestUser",
            "account_id": "abc123",
            "access_token": "tok_" + authorization_code,
        }
        return self._session

    def logout(self) -> None:
        self._session = None

    def get_session(self) -> Optional[dict]:
        return self._session

    def is_logged_in(self) -> bool:
        return self._session is not None
