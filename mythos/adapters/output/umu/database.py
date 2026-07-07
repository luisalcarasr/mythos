from __future__ import annotations

import csv
import io
import logging
import threading
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_UMU_DB_URL = (
    "https://raw.githubusercontent.com/"
    "Open-Wine-Components/umu-database/main/umu-database.csv"
)
_REFRESH_INTERVAL = timedelta(days=7)
_MIN_REFRESH_INTERVAL = timedelta(hours=1)


@dataclass
class UmuEntry:
    title: str
    store: str
    codename: str
    umu_id: str
    acronym: str = ""
    note: str = ""
    exe_strings: str = ""


class UmuDatabase:
    def __init__(self, cache_dir: Path | str) -> None:
        self._cache_dir = Path(cache_dir)
        self._cache_file = self._cache_dir / "umu-database.csv"
        self._entries: list[UmuEntry] = []
        self._last_refresh: Optional[datetime] = None
        self._loaded = False
        self._lock = threading.Lock()

    # ---------------------------------------------------------------- #
    # Public API                                                        #
    # ---------------------------------------------------------------- #

    def refresh(self) -> None:
        with self._lock:
            if not self._should_refresh():
                logger.debug("UMU database cache is fresh, skipping refresh")
                return
            content = self._download()
            if content:
                self._write_cache(content)
                self._entries = self._parse(content)
                self._last_refresh = datetime.now()
                self._loaded = True

    def lookup(self, store: str, codename: str) -> Optional[UmuEntry]:
        self._ensure_loaded()
        for entry in self._entries:
            if entry.store == store and entry.codename == codename:
                return entry
        return None

    def lookup_by_title(self, title: str) -> list[UmuEntry]:
        self._ensure_loaded()
        return [e for e in self._entries if e.title.lower() == title.lower()]

    def fuzzy_search(self, query: str, store: str = "") -> Optional[UmuEntry]:
        self._ensure_loaded()
        q = query.lower().strip()
        if not q:
            return None

        candidates: list[tuple[UmuEntry, float]] = []

        for entry in self._entries:
            if store and entry.store != store:
                continue
            t = entry.title.lower()
            if t == q:
                return entry
            if t.startswith(q):
                candidates.append((entry, 1.0 - (len(t) - len(q)) / len(t)))
            elif q in t:
                candidates.append((entry, len(q) / len(t)))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[1], reverse=True)
        best = candidates[0]
        logger.debug(
            "fuzzy_search(%r, store=%r) → %r (score=%.2f)",
            query, store, best[0].title, best[1],
        )
        return best[0]

    # ---------------------------------------------------------------- #
    # Internal                                                          #
    # ---------------------------------------------------------------- #

    def _should_refresh(self) -> bool:
        if not self._cache_file.exists():
            return True
        if self._last_refresh is not None:
            return datetime.now() - self._last_refresh > _MIN_REFRESH_INTERVAL
        mtime = datetime.fromtimestamp(self._cache_file.stat().st_mtime)
        return datetime.now() - mtime > _REFRESH_INTERVAL

    def _download(self) -> str:
        logger.info("Downloading UMU database from %s", _UMU_DB_URL)
        try:
            with urllib.request.urlopen(_UMU_DB_URL, timeout=10) as resp:
                return resp.read().decode("utf-8")
        except Exception as exc:
            logger.warning("Failed to download UMU database: %s", exc)
            return ""

    def _parse(self, content: str) -> list[UmuEntry]:
        entries: list[UmuEntry] = []
        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            entries.append(
                UmuEntry(
                    title=row.get("TITLE", ""),
                    store=row.get("STORE", ""),
                    codename=row.get("CODENAME", ""),
                    umu_id=row.get("UMU_ID", ""),
                    acronym=row.get("COMMON ACRONYM (Optional)", ""),
                    note=row.get("NOTE (Optional)", ""),
                    exe_strings=row.get("EXE_STRINGS (Optional)", ""),
                )
            )
        return entries

    def _read_cache(self) -> list[UmuEntry]:
        try:
            return self._parse(self._cache_file.read_text())
        except (FileNotFoundError, OSError) as exc:
            logger.debug("No UMU database cache found: %s", exc)
            return []

    def _write_cache(self, content: str) -> None:
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._cache_file.write_text(content)
            logger.info("UMU database cached to %s", self._cache_file)
        except OSError as exc:
            logger.warning("Failed to write UMU database cache: %s", exc)

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        if self._cache_file.exists():
            self._entries = self._read_cache()
            self._loaded = True
        else:
            self.refresh()
