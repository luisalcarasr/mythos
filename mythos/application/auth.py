# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Authentication use cases."""

from __future__ import annotations

import logging
from typing import Optional

from mythos.domain.events import UserLoggedIn, UserLoggedOut
from mythos.ports.input import GetSessionUseCase, LoginUseCase, LogoutUseCase
from mythos.ports.output import AuthSessionRepository, EventBus

logger = logging.getLogger(__name__)


class Login(LoginUseCase):
    def __init__(self, auth_session_repo: AuthSessionRepository, event_bus: Optional[EventBus] = None) -> None:
        self._repo = auth_session_repo
        self._bus = event_bus

    def execute(self, authorization_code: str) -> dict:
        logger.info("Logging in with authorisation code…")
        session = self._repo.login_with_code(authorization_code)
        if self._bus:
            self._bus.publish(
                UserLoggedIn(
                    display_name=session.get("display_name", ""),
                    account_id=session.get("account_id", ""),
                )
            )
        logger.info("Logged in as %s", session.get("display_name"))
        return session


class Logout(LogoutUseCase):
    def __init__(self, auth_session_repo: AuthSessionRepository, event_bus: Optional[EventBus] = None) -> None:
        self._repo = auth_session_repo
        self._bus = event_bus

    def execute(self) -> None:
        logger.info("Logging out…")
        self._repo.logout()
        if self._bus:
            self._bus.publish(UserLoggedOut())
        logger.info("Logged out.")


class GetSession(GetSessionUseCase):
    def __init__(self, auth_session_repo: AuthSessionRepository) -> None:
        self._repo = auth_session_repo

    def execute(self) -> Optional[dict]:
        return self._repo.get_session()
