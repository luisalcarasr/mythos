# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for domain services."""

from __future__ import annotations

from pathlib import Path

import pytest

from mythos.domain.entities import AppSettings
from mythos.domain.exceptions import DiskSpaceError
from mythos.domain.services import InstallPlanningService
from mythos.domain.value_objects import DiskSize


def test_validate_space_ok() -> None:
    svc = InstallPlanningService()
    # 1 GiB required, 10 GiB available → no error
    svc.validate_space(
        required=DiskSize.from_gib(1),
        available=DiskSize.from_gib(10),
    )


def test_validate_space_insufficient() -> None:
    svc = InstallPlanningService()
    with pytest.raises(DiskSpaceError):
        svc.validate_space(
            required=DiskSize.from_gib(10),
            available=DiskSize.from_gib(2),
        )


def test_validate_space_margin() -> None:
    """10% margin means 1 GiB required needs 1.1 GiB available."""
    svc = InstallPlanningService()
    exactly_enough = DiskSize(int(DiskSize.from_gib(1).bytes_ * 1.09))
    with pytest.raises(DiskSpaceError):
        svc.validate_space(
            required=DiskSize.from_gib(1),
            available=exactly_enough,
        )


def test_resolve_install_path_uses_preferred() -> None:
    svc = InstallPlanningService()
    preferred = Path("/my/custom/path")
    result = svc.resolve_install_path(preferred, AppSettings())
    assert result == preferred


def test_resolve_install_path_falls_back_to_settings() -> None:
    svc = InstallPlanningService()
    settings = AppSettings(default_install_path=Path("/default/games"))
    result = svc.resolve_install_path(None, settings)
    assert result == Path("/default/games")


def test_resolve_install_path_falls_back_to_home_games() -> None:
    svc = InstallPlanningService()
    result = svc.resolve_install_path(None, AppSettings())
    assert result == Path.home() / "Games"
