from __future__ import annotations

from datetime import datetime
from typing import Optional

from redcam.core.ports.video_metadata import VideoMetadataPort
from redcam.domain.gps_types import GPSPoint
from redcam.infra.gopro.gopro_gps_extractor import GoProGPSExtractor


class GoProVideoMetadataAdapter(VideoMetadataPort):
    def __init__(self) -> None:
        self._extractor = GoProGPSExtractor()
        self._cache: dict[str, dict[str, object]] = {}

    def get_creation_time(self, video_path: str) -> Optional[datetime]:
        cached = self._cache.get(video_path)
        if cached and "creation_time" in cached:
            return cached["creation_time"]  # type: ignore[return-value]

        creation_time = self._extractor.get_video_creation_time(video_path)
        self._cache.setdefault(video_path, {})["creation_time"] = creation_time
        return creation_time

    def get_duration_seconds(self, video_path: str) -> Optional[float]:
        cached = self._cache.get(video_path)
        if cached and "duration_seconds" in cached:
            return cached["duration_seconds"]  # type: ignore[return-value]

        duration_seconds = self._extractor.get_video_duration_seconds(video_path)
        self._cache.setdefault(video_path, {})["duration_seconds"] = duration_seconds
        return duration_seconds

    def extract_embedded_gps(self, video_path: str) -> Optional[list[GPSPoint]]:
        cached = self._cache.get(video_path)
        if cached and "embedded_gps" in cached:
            return cached["embedded_gps"]  # type: ignore[return-value]

        points, _ = self._extractor.extract_gps(video_path)
        embedded = points if points else None
        self._cache.setdefault(video_path, {})["embedded_gps"] = embedded
        return embedded
