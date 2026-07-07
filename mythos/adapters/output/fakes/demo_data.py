# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Demo seed data for design mode.

``demo_games()`` returns a list of ``Game`` objects covering every
interesting ``GameStatus`` so every UI state is visible immediately:

  - Not installed (several, to fill the grid)
  - Installed (playable)
  - Installed + update available
  - Currently running (shows "Running" badge)
  - Queued for install
  - DLC entry
  - Error state

``demo_installed()`` returns the matching ``InstalledInfo`` list.
"""

from __future__ import annotations

from pathlib import Path

from mythos.domain.entities import AppSettings, Game, InstalledInfo
from mythos.domain.value_objects import (
    AppName,
    DiskSize,
    GameStatus,
    InstallPath,
    LaunchOptions,
    Platform,
    WineRunnerType,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_INSTALL_ROOT = Path("/games")


def _name(value: str) -> AppName:
    return AppName(value)


def _installed(app_name: str, version: str = "1.0.0", update: bool = False) -> InstalledInfo:
    return InstalledInfo(
        app_name=_name(app_name),
        install_path=InstallPath(_INSTALL_ROOT / app_name),
        version=version,
        platform=Platform.WINDOWS,
        install_size=DiskSize.from_gib(15),
        executable="game.exe",
        update_available=update,
        can_run_offline=True,
    )


# ---------------------------------------------------------------------------
# Public factories
# ---------------------------------------------------------------------------

def demo_games() -> list[Game]:
    """Return ~12 games spanning every GameStatus for design work."""

    games: list[Game] = [
        # ---------------------------------------------------------------- #
        # Installed — ready to play                                         #
        # ---------------------------------------------------------------- #
        Game(
            app_name=_name("Fortnite"),
            title="Fortnite",
            developer="Epic Games",
            publisher="Epic Games",
            description="The world's most popular battle royale. Drop in, build up, and be the last one standing.",
            genres=["Battle Royale", "Shooter", "Free to Play"],
            tags=["Multiplayer", "Online", "Free"],
            supports_cloud_saves=True,
            status=GameStatus.INSTALLED,
            installed_info=_installed("Fortnite", "29.10"),
        ),
        Game(
            app_name=_name("RocketLeague"),
            title="Rocket League",
            developer="Psyonix",
            publisher="Epic Games",
            description="Score goals with rocket-powered cars in the ultimate vehicular soccer game.",
            genres=["Sports", "Racing", "Action"],
            tags=["Multiplayer", "Competitive", "Free"],
            supports_cloud_saves=True,
            status=GameStatus.INSTALLED,
            installed_info=_installed("RocketLeague", "2.38"),
        ),
        Game(
            app_name=_name("Hades"),
            title="Hades",
            developer="Supergiant Games",
            publisher="Supergiant Games",
            description="Defy the god of the dead as you hack and slash out of the Underworld in this rogue-like dungeon crawler.",
            genres=["Roguelike", "Action", "RPG"],
            tags=["Single-player", "Story Rich", "Controller Support"],
            supports_cloud_saves=True,
            status=GameStatus.INSTALLED,
            installed_info=_installed("Hades", "1.38102"),
        ),

        # ---------------------------------------------------------------- #
        # Installed + update available                                      #
        # ---------------------------------------------------------------- #
        Game(
            app_name=_name("CyberPunk2077"),
            title="Cyberpunk 2077",
            developer="CD Projekt Red",
            publisher="CD Projekt",
            description="An open-world action RPG set in the megalopolis of Night City.",
            genres=["RPG", "Open World", "Action"],
            tags=["Single-player", "Story Rich", "Mature"],
            supports_cloud_saves=True,
            status=GameStatus.INSTALLED,
            installed_info=_installed("CyberPunk2077", "2.1", update=True),
        ),

        # ---------------------------------------------------------------- #
        # Running right now                                                 #
        # ---------------------------------------------------------------- #
        Game(
            app_name=_name("Borderlands3"),
            title="Borderlands 3",
            developer="Gearbox Software",
            publisher="2K",
            description="Shoot and loot your way through a chaotic world of all-new mayhem.",
            genres=["Shooter", "RPG", "Action"],
            tags=["Co-op", "Loot", "Humor"],
            supports_cloud_saves=True,
            status=GameStatus.RUNNING,
            installed_info=InstalledInfo(
                app_name=_name("Borderlands3"),
                install_path=InstallPath(_INSTALL_ROOT / "Borderlands3"),
                version="1.0.5.0",
                platform=Platform.WINDOWS,
                install_size=DiskSize.from_gib(47),
                executable="Borderlands3.exe",
                pid=98765,
            ),
        ),

        # ---------------------------------------------------------------- #
        # Queued for install                                                #
        # ---------------------------------------------------------------- #
        Game(
            app_name=_name("AlanWake2"),
            title="Alan Wake 2",
            developer="Remedy Entertainment",
            publisher="Epic Games Publishing",
            description="A psychological horror game about a writer trapped in a dark dimension.",
            genres=["Horror", "Action", "Thriller"],
            tags=["Single-player", "Story Rich", "Dark"],
            status=GameStatus.QUEUED,
        ),

        # ---------------------------------------------------------------- #
        # Not installed — various genres to fill the grid                   #
        # ---------------------------------------------------------------- #
        Game(
            app_name=_name("ControlUltimateEdition"),
            title="Control: Ultimate Edition",
            developer="Remedy Entertainment",
            publisher="505 Games",
            description="A supernatural third-person action-adventure set in a brutalist skyscraper.",
            genres=["Action", "Shooter", "Supernatural"],
            tags=["Single-player", "Atmospheric", "Metroidvania"],
            status=GameStatus.NOT_INSTALLED,
        ),
        Game(
            app_name=_name("Satisfactory"),
            title="Satisfactory",
            developer="Coffee Stain Studios",
            publisher="Coffee Stain Publishing",
            description="Build vast automated factories on an alien planet.",
            genres=["Simulation", "Building", "Exploration"],
            tags=["Co-op", "Open World", "Early Access"],
            status=GameStatus.NOT_INSTALLED,
        ),
        Game(
            app_name=_name("CitySkylinesII"),
            title="Cities: Skylines II",
            developer="Colossal Order",
            publisher="Paradox Interactive",
            description="The next generation of city-building simulation.",
            genres=["Simulation", "Strategy", "City Builder"],
            tags=["Single-player", "Sandbox", "Relaxing"],
            status=GameStatus.NOT_INSTALLED,
        ),
        Game(
            app_name=_name("DeadIsland2"),
            title="Dead Island 2",
            developer="Dambuster Studios",
            publisher="Deep Silver",
            description="Hack, slash and smash your way through the zombie apocalypse.",
            genres=["Action", "RPG", "Horror"],
            tags=["Co-op", "Gore", "Open World"],
            status=GameStatus.NOT_INSTALLED,
        ),

        # ---------------------------------------------------------------- #
        # Error state                                                       #
        # ---------------------------------------------------------------- #
        Game(
            app_name=_name("ReadyOrNotGame"),
            title="Ready or Not",
            developer="VOID Interactive",
            publisher="VOID Interactive",
            description="Command a SWAT team through tactical law enforcement operations.",
            genres=["Tactical", "Shooter", "Simulation"],
            tags=["Multiplayer", "Co-op", "Intense"],
            status=GameStatus.ERROR,
        ),

        # ---------------------------------------------------------------- #
        # DLC entry                                                         #
        # ---------------------------------------------------------------- #
        Game(
            app_name=_name("Hades_DLC_Chorus"),
            title="Hades — Chorus Pack (DLC)",
            developer="Supergiant Games",
            publisher="Supergiant Games",
            description="Additional voice lines and music tracks for Hades.",
            genres=["DLC"],
            tags=["DLC"],
            is_dlc=True,
            status=GameStatus.NOT_INSTALLED,
        ),
    ]

    return games


def demo_installed() -> list[InstalledInfo]:
    """Return InstalledInfo for every demo game that is installed/running."""
    result: list[InstalledInfo] = []
    for game in demo_games():
        if game.installed_info is not None:
            result.append(game.installed_info)
    return result


def demo_settings() -> AppSettings:
    """Return a realistic default settings object for design mode."""
    return AppSettings(
        language="en",
        theme="system",
        default_install_path=Path("/games"),
        default_wine_runner=WineRunnerType.PROTON,
        enable_discord_rpc=False,
        check_updates_on_startup=True,
        show_dlc_in_library=False,
        concurrent_downloads=2,
    )
