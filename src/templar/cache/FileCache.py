import sys
import hashlib
import json
import os
import tempfile
import time
import re
from pathlib import Path
from .CacheProvider import CacheProvider

sys.dont_write_bytecode = True

class FileCache(CacheProvider):
    _CACHE_FILE = re.compile(r"^[0-9a-f]{64}\.json$")
    def __init__(self, directory=".templar-cache"):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        if not isinstance(key, str):
            raise TypeError("Cache keys must be strings")

        return self.directory / f"{hashlib.sha256(key.encode('utf-8')).hexdigest()}.json"

    def get(self, key: str):
        path = self._path(key)

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, json.JSONDecodeError):
            path.unlink(missing_ok=True)
            return None

        if payload.get("expires_at") is not None and payload["expires_at"] <= time.time():
            path.unlink(missing_ok=True)
            return None

        return payload.get("value")

    def set(self, key: str, value, ttl=None):
        if ttl is not None and ttl <= 0:
            self.delete(key)

            return

        path = self._path(key)

        try:
            data = json.dumps({"key": key, "expires_at": None if ttl is None else time.time() + float(ttl), "value": value})
        except (TypeError, ValueError) as exc:
            raise TypeError("FileCache values must be JSON serializable") from exc

        fd, temporary_name = tempfile.mkstemp(prefix=".templar-cache-", dir=self.directory)

        try:
            with os.fdopen(fd, "w", encoding="utf-8") as temporary:
                temporary.write(data)

            Path(temporary_name).replace(path)
        finally:
            Path(temporary_name).unlink(missing_ok=True)

    def delete(self, key: str):
        self._path(key).unlink(missing_ok=True)

    def clear(self):
        for path in self.directory.glob("*.json"):
            # Cache entries are SHA-256 key digests. Never treat arbitrary JSON files in a user-selected directory as
            # disposable cache data.
            if self._CACHE_FILE.fullmatch(path.name):
                path.unlink(missing_ok=True)

    def clear_prefix(self, prefix: str):
        if not isinstance(prefix, str):
            raise TypeError("Cache prefixes must be strings")

        for path in self.directory.glob("*.json"):
            if not self._CACHE_FILE.fullmatch(path.name):
                continue

            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue

            if isinstance(payload.get("key"), str) and payload["key"].startswith(prefix):
                path.unlink(missing_ok=True)
