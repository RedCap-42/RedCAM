from __future__ import annotations

from datetime import datetime
from typing import Optional, Protocol

from redcam.domain.gps_types import GPSPoint


class VideoMetadataPort(Protocol):
    def get_creation_time(self, video_path: str) -> Optional[datetime]: ...

    def get_duration_seconds(self, video_path: str) -> Optional[float]: ...

    def extract_embedded_gps(self, video_path: str) -> Optional[list[GPSPoint]]: ...
