from __future__ import annotations

import os
from datetime import datetime, timezone

from redcam.core.ports.file_stat import FileStatPort


class OSFileStat(FileStatPort):
    def mtime_utc(self, path: str) -> datetime:
        ts = os.path.getmtime(path)
        return datetime.fromtimestamp(ts, tz=timezone.utc)
