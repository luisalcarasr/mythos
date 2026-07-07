from __future__ import annotations

import logging
from typing import Callable, Optional

from mythos.adapters.output.legendary.cli_wrapper import LegendaryCliWrapper
from mythos.domain.exceptions import CloudSaveError
from mythos.domain.value_objects import AppName, SyncDirection
from mythos.ports.output import CloudSavePort

logger = logging.getLogger(__name__)


class LegendaryCloudSaves(CloudSavePort):
    def __init__(self, cli: Optional[LegendaryCliWrapper] = None) -> None:
        self._cli = cli or LegendaryCliWrapper()

    def supports(self, app_name: AppName) -> bool:
        try:
            raw = self._cli.run_json(
                ["info", str(app_name), "--json", "--platform", "Windows"]
            )
            game_data = raw.get("game", {})
            return bool(game_data.get("cloud_saves_supported", False))
        except Exception:
            return False

    def sync(
        self,
        app_name: AppName,
        direction: SyncDirection,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> None:
        try:
            if on_progress:
                on_progress(f"Syncing cloud saves for {app_name}…")

            args = ["sync-saves", str(app_name)]

            if direction == SyncDirection.DOWNLOAD:
                args.append("--skip-upload")
            elif direction == SyncDirection.UPLOAD:
                args.append("--skip-download")
            elif direction == SyncDirection.BOTH:
                pass

            self._cli.run(args)
            if on_progress:
                on_progress("Cloud save sync complete.")
        except Exception as exc:
            raise CloudSaveError(
                f"Cloud save sync failed for {app_name}: {exc}"
            ) from exc
