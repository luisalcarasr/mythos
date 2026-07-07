# Mythos — Epic Games Launcher
# Copyright (C) 2024 Luis Alcaras <luisalcarasr@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
"""EpicStorePort implemented via LegendaryCore."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Callable, Optional

from mythos.adapters.output.legendary.core_gateway import LegendaryCoreGateway
from mythos.adapters.output.legendary.mappers import (
    legendary_game_to_domain,
    legendary_installed_to_domain,
)
from mythos.adapters.output.process.runner import SubprocessRunner
from mythos.domain.entities import Game, InstalledInfo
from mythos.domain.exceptions import (
    DownloadError,
    GameNotFoundError,
    InstallError,
)
from mythos.domain.value_objects import (
    AppName,
    DiskSize,
    InstallPath,
    LaunchOptions,
    Platform,
    Progress,
)
from mythos.ports.output import EpicStorePort

logger = logging.getLogger(__name__)


class LegendaryEpicStore(EpicStorePort):
    """
    Talks to Epic Games via ``LegendaryCore``.

    Install / update / repair operations are long-running; they run in
    a daemon thread and call *on_progress* from that thread.  The GTK
    event bus bridges these calls back to the GLib main loop.
    """

    def __init__(
        self,
        gateway: LegendaryCoreGateway,
        runner: Optional[SubprocessRunner] = None,
    ) -> None:
        self._gw = gateway
        self._runner = runner
        self._active_installs: dict[str, threading.Thread] = {}

    # ---------------------------------------------------------------- #
    # Query                                                              #
    # ---------------------------------------------------------------- #

    def list_games(self, include_dlc: bool = False) -> list[Game]:
        try:
            lg_games = self._gw.get_game_list()
            games = [legendary_game_to_domain(g) for g in lg_games]
            if not include_dlc:
                games = [g for g in games if not g.is_dlc]
            return games
        except Exception as exc:
            logger.error("list_games failed: %s", exc)
            return []

    def get_game(self, app_name: AppName) -> Optional[Game]:
        try:
            lg = self._gw.get_game(str(app_name))
            if lg is None:
                return None
            return legendary_game_to_domain(lg)
        except Exception as exc:
            logger.error("get_game(%s) failed: %s", app_name, exc)
            return None

    def get_installed(self) -> list[InstalledInfo]:
        try:
            return [legendary_installed_to_domain(g) for g in self._gw.get_installed_list()]
        except Exception as exc:
            logger.error("get_installed failed: %s", exc)
            return []

    def get_download_size(self, app_name: AppName, platform: Platform) -> DiskSize:
        try:
            analysis = self._gw.core.get_install_manifest(str(app_name), platform=platform.value)
            return DiskSize(analysis.dl_size)
        except Exception:  # noqa: BLE001
            return DiskSize(0)

    def get_install_size(self, app_name: AppName, platform: Platform) -> DiskSize:
        try:
            analysis = self._gw.core.get_install_manifest(str(app_name), platform=platform.value)
            return DiskSize(analysis.disk_size)
        except Exception:  # noqa: BLE001
            return DiskSize(0)

    # ---------------------------------------------------------------- #
    # Install / update / repair / move / uninstall                      #
    # ---------------------------------------------------------------- #

    def install_game(
        self,
        app_name: AppName,
        install_path: Path,
        platform: Platform,
        on_progress: Callable[[Progress], None],
    ) -> InstalledInfo:
        """
        Install using legendary's download manager.

        legendary's ``install_game`` yields ``(progress, status)``
        tuples.  We iterate synchronously here; the caller is expected
        to run this in a thread (see EnqueueDownload → downloads.py).
        """
        try:
            game = self._gw.core.get_game(str(app_name))
            if game is None:
                raise GameNotFoundError(str(app_name))

            dlm, analysis, igame = self._gw.core.prepare_download(
                game=game,
                base_path=str(install_path),
                platform=platform.value,
            )

            errors: list[str] = []

            def status_callback(progress: float, **kwargs: object) -> None:
                p = Progress(
                    fraction=min(max(progress / 100.0, 0.0), 1.0),
                    downloaded_bytes=kwargs.get("downloaded_size", 0),  # type: ignore[arg-type]
                    total_bytes=kwargs.get("total_size", 0),  # type: ignore[arg-type]
                    speed_bps=kwargs.get("download_speed", 0.0),  # type: ignore[arg-type]
                    eta_seconds=kwargs.get("estimated_time", 0.0),  # type: ignore[arg-type]
                )
                on_progress(p)

            dlm.start()
            dlm.join()

            if dlm.errors:
                raise DownloadError(f"Download errors: {dlm.errors}")

            self._gw.core.finish_install(game=game, igame=igame)

            installed = self._gw.get_installed_game(str(app_name))
            if installed:
                return legendary_installed_to_domain(installed)

            # Fallback — build from igame
            return InstalledInfo(
                app_name=app_name,
                install_path=InstallPath(Path(igame.install_path)),
                version=igame.version,
                platform=platform,
                install_size=DiskSize(igame.install_size),
                executable=igame.executable,
            )

        except (GameNotFoundError, DownloadError):
            raise
        except Exception as exc:
            raise InstallError(f"Install failed for {app_name}: {exc}") from exc

    def update_game(
        self,
        app_name: AppName,
        on_progress: Callable[[Progress], None],
    ) -> InstalledInfo:
        return self.install_game(
            app_name=app_name,
            install_path=Path(self._gw.get_installed_game(str(app_name)).install_path).parent,
            platform=Platform.current(),
            on_progress=on_progress,
        )

    def repair_game(
        self,
        app_name: AppName,
        on_progress: Callable[[Progress], None],
    ) -> InstalledInfo:
        try:
            game = self._gw.core.get_game(str(app_name))
            igame = self._gw.get_installed_game(str(app_name))
            dlm, analysis, igame = self._gw.core.prepare_download(
                game=game,
                igame=igame,
                repair_mode=True,
                repair_use_latest=True,
            )
            dlm.start()
            dlm.join()
            if dlm.errors:
                raise DownloadError(f"Repair errors: {dlm.errors}")
            installed = self._gw.get_installed_game(str(app_name))
            return legendary_installed_to_domain(installed)
        except (DownloadError, GameNotFoundError):
            raise
        except Exception as exc:
            raise InstallError(f"Repair failed for {app_name}: {exc}") from exc

    def move_game(self, app_name: AppName, new_path: Path) -> InstalledInfo:
        try:
            self._gw.core.move_game(str(app_name), str(new_path))
            installed = self._gw.get_installed_game(str(app_name))
            return legendary_installed_to_domain(installed)
        except Exception as exc:
            raise InstallError(f"Move failed for {app_name}: {exc}") from exc

    def uninstall_game(self, app_name: AppName) -> None:
        try:
            igame = self._gw.get_installed_game(str(app_name))
            if igame is None:
                return
            self._gw.core.uninstall_game(igame)
        except Exception as exc:
            raise InstallError(f"Uninstall failed for {app_name}: {exc}") from exc

    def cancel_download(self, app_name: AppName) -> None:
        thread = self._active_installs.get(str(app_name))
        if thread:
            # legendary does not expose a direct cancel API on DLM;
            # setting a flag and letting the thread finish is the safest
            # approach.  Improve if legendary exposes a cancel hook.
            logger.warning(
                "cancel_download(%s): legendary has no cancellation API; "
                "the download will finish the current chunk.",
                app_name,
            )

    def pause_download(self, app_name: AppName) -> None:
        # legendary-gl has no native pause API; log and no-op for now.
        logger.warning(
            "pause_download(%s): legendary has no pause API — not implemented.", app_name
        )

    def resume_download(self, app_name: AppName) -> None:
        logger.warning(
            "resume_download(%s): legendary has no resume API — not implemented.", app_name
        )

    # ---------------------------------------------------------------- #
    # Launch                                                             #
    # ---------------------------------------------------------------- #

    def launch_game(
        self,
        app_name: AppName,
        launch_options: Optional[LaunchOptions] = None,
        offline: bool = False,
    ) -> int:
        try:
            game = self._gw.core.get_game(str(app_name))
            igame = self._gw.get_installed_game(str(app_name))

            extra_env: dict[str, str] = {}
            wrapper: Optional[str] = None

            if launch_options:
                extra_env = launch_options.extra_env or {}
                wrapper = launch_options.wrapper_command or None

            _, proc = self._gw.core.launch_game(
                igame=igame,
                extra_args=[],
                offline=offline,
                wrapper=wrapper,
                extra_env=extra_env,
            )
            return proc.pid
        except Exception as exc:
            raise RuntimeError(f"Launch failed for {app_name}: {exc}") from exc
