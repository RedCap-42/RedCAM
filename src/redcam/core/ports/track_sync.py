from __future__ import annotations

from datetime import datetime
from typing import Optional, Protocol

from redcam.domain.gps_types import GPSPoint, GPSTrack


class TrackSyncPort(Protocol):
    """Accès au track + interpolation temporelle (core-friendly)."""

    @property
    def track(self) -> Optional[GPSTrack]: ...

    def parse(self) -> Optional[GPSTrack]: ...

    def is_time_in_track(self, time_to_check: datetime, tolerance_seconds: float = 300.0) -> bool: ...

    def get_position_at_time(self, target_time: datetime, tolerance_hours: float = 2.0) -> Optional[GPSPoint]: ...
