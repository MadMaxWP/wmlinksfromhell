"""small atomic JSON cache used for explicit Wikimedia metadata refreshes"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Optional

from .constants import CACHE_SCHEMA_VERSION
from .exceptions import CacheError


class MetadataCache:
    """persistent cache; a bad cache never destroys a good in-memory bootstrap"""

    def __init__(self, path: Optional[os.PathLike] = None):
        self.path = Path(path) if path is not None else self.default_path()

    @staticmethod
    def default_path() -> Path:
        base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
        return Path(base) / "wmlinksfromhell" / "metadata.json"

    def load(self) -> dict:
        if not self.path.exists():
            return self.empty()
        try:
            with self.path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            self._quarantine()
            return self.empty()
        if not isinstance(data, dict) or data.get("schema_version") != CACHE_SCHEMA_VERSION:
            self._quarantine()
            return self.empty()
        return data

    def save(self, data: dict) -> None:
        payload = dict(data)
        payload["schema_version"] = CACHE_SCHEMA_VERSION
        payload["updated_at"] = time.time()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), prefix=".metadata-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2, sort_keys=True)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.path)
        except OSError as exc:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise CacheError(f"couldn't write metadata cache to {self.path}") from exc

    def is_expired(self, max_age_seconds: float) -> bool:
        updated_at = self.load().get("updated_at")
        return updated_at is None or (time.time() - updated_at) > max_age_seconds

    def clear(self) -> None:
        try:
            self.path.unlink(missing_ok=True)
        except OSError:
            pass

    def empty(self) -> dict:
        return {
            "schema_version": CACHE_SCHEMA_VERSION,
            "updated_at": None,
            "wikis": {},
            "languages": {},
            "interwiki_maps": {},
            "global_interwikis": {},
            "global_interwiki_lists": {},
            "family_language_aliases": {},
            "family_language_prefixes": {},
            "namespaces": {},
            "http": {},
        }

    def _quarantine(self) -> None:
        try:
            target = self.path.with_suffix(self.path.suffix + ".corrupt")
            if target.exists():
                target = self.path.with_suffix(self.path.suffix + f".{int(time.time())}.corrupt")
            os.replace(self.path, target)
        except OSError:
            pass
