from __future__ import annotations

from datetime import datetime
from typing import Protocol


class FileStatPort(Protocol):
    def mtime_utc(self, path: str) -> datetime: ...
