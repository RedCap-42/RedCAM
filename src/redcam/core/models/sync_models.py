from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from redcam.domain.gps_types import GPSTrack, VideoLocation


class SyncPhase(str, Enum):
    LOAD_FIT = "load_fit"
    LIST_VIDEOS = "list_videos"
    PROCESS_VIDEO = "process_video"
    DONE = "done"


@dataclass(frozen=True)
class SyncRequest:
    fit_path: Optional[str]
    video_folder: str
    force_timestamp_sync: bool = False
    camera_filter: str = "Auto (Détection)"
    local_timezone: str = "Europe/Paris"


@dataclass(frozen=True)
class ProgressEvent:
    phase: SyncPhase
    message: str
    current: int = 0
    total: int = 0
    video_path: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass(frozen=True)
class SyncResult:
    track: Optional[GPSTrack]
    video_locations: list[VideoLocation]
