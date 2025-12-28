from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

import pytz

from redcam.core.models.sync_models import ProgressEvent, SyncPhase, SyncRequest, SyncResult
from redcam.core.ports.file_stat import FileStatPort
from redcam.core.ports.progress import ProgressReporter
from redcam.core.ports.track_sync import TrackSyncPort
from redcam.core.ports.video_catalog import VideoCatalogPort
from redcam.core.ports.video_metadata import VideoMetadataPort
from redcam.domain.gps_types import LocationSource, VideoLocation


@dataclass
class SyncVideosUseCase:
    """Use-case principal: synchroniser vidéos GoPro avec une trace GPS."""

    track_sync: Optional[TrackSyncPort]
    video_catalog: VideoCatalogPort
    video_metadata: VideoMetadataPort
    file_stat: FileStatPort
    local_timezone: str = "Europe/Paris"

    def execute(self, request: SyncRequest, reporter: Optional[ProgressReporter] = None) -> SyncResult:
        if reporter:
            reporter.report(ProgressEvent(SyncPhase.LIST_VIDEOS, "Recherche des vidéos..."))

        extensions = [".mp4", ".MP4"]
        video_paths = self.video_catalog.list_videos(request.video_folder, extensions)

        if not video_paths:
            if reporter:
                reporter.report(ProgressEvent(SyncPhase.DONE, "Aucune vidéo trouvée"))
            return SyncResult(track=self.track_sync.track if self.track_sync else None, video_locations=[])

        total = len(video_paths)
        results: list[VideoLocation] = []

        for idx, video_path in enumerate(video_paths, start=1):
            if reporter:
                reporter.report(
                    ProgressEvent(
                        SyncPhase.PROCESS_VIDEO,
                        f"Vidéo {idx}/{total}",
                        current=idx,
                        total=total,
                        video_path=video_path,
                    )
                )

            results.append(self._locate_one(request, video_path))

        if reporter:
            reporter.report(ProgressEvent(SyncPhase.DONE, "Terminé", current=total, total=total))

        return SyncResult(track=self.track_sync.track if self.track_sync else None, video_locations=results)

    def _locate_one(self, request: SyncRequest, video_path: str) -> VideoLocation:
        video_name = os.path.basename(video_path)

        force_timestamp_sync = request.force_timestamp_sync
        if request.camera_filter == "Hero 12 (Pas de GPS)":
            force_timestamp_sync = True

        raw_creation_time = self.video_metadata.get_creation_time(video_path)
        
        # Appliquer le décalage manuel
        if raw_creation_time and request.manual_offset_seconds != 0:
            raw_creation_time = raw_creation_time + timedelta(seconds=request.manual_offset_seconds)
            
        creation_time = self._smart_correct_timestamp(raw_creation_time, video_path, 0.0) # Offset déjà appliqué
        duration_seconds = self.video_metadata.get_duration_seconds(video_path)

        embedded_points = None
        if not force_timestamp_sync and request.camera_filter != "Hero 12 (Pas de GPS)":
            embedded_points = self.video_metadata.extract_embedded_gps(video_path)
            if embedded_points and len(embedded_points) == 0:
                embedded_points = None

        if not force_timestamp_sync and embedded_points:
            return VideoLocation(
                video_path=video_path,
                video_name=video_name,
                position=embedded_points[0],
                source=LocationSource.EMBEDDED_GPS,
                creation_time=creation_time,
                duration_seconds=duration_seconds,
                track_points=embedded_points
            )

        if self.track_sync and self.track_sync.track and creation_time:
            utc_time = self._ensure_utc(creation_time)
            position = self.track_sync.get_position_at_time(utc_time)
            if position:
                track_segment = self.track_sync.get_track_segment(utc_time, duration_seconds or 0)
                return VideoLocation(
                    video_path=video_path,
                    video_name=video_name,
                    position=position,
                    source=LocationSource.FIT_SYNC,
                    creation_time=creation_time,
                    duration_seconds=duration_seconds,
                    track_points=track_segment
                )

        return VideoLocation(
            video_path=video_path,
            video_name=video_name,
            position=None,
            source=LocationSource.UNKNOWN,
            creation_time=creation_time,
            duration_seconds=duration_seconds,
        )

    def _smart_correct_timestamp(self, creation_time: Optional[datetime], video_path: str, manual_offset: float = 0.0) -> Optional[datetime]:
        if not creation_time:
            return None
            
        # 0) Appliquer le décalage manuel
        if manual_offset != 0.0:
            creation_time = creation_time + timedelta(seconds=manual_offset)

        # 1) FIT sync (prioritaire) : tester décalages usuels
        if self.track_sync and self.track_sync.track:
            offsets = [0, -3600, 3600, -7200, 7200]
            for offset in offsets:
                shifted = creation_time + timedelta(seconds=offset)
                if self.track_sync.is_time_in_track(self._ensure_utc(shifted)):
                    return shifted

        # 2) Fallback: correction via mtime + timezone locale
        try:
            mtime = self.file_stat.mtime_utc(video_path)
            local_tz = pytz.timezone(self.local_timezone)
            naive = creation_time.replace(tzinfo=None)
            local_dt = local_tz.localize(naive)
            corrected = local_dt.astimezone(timezone.utc)

            diff_original = abs((mtime - self._ensure_utc(creation_time)).total_seconds())
            diff_corrected = abs((mtime - corrected).total_seconds())

            if diff_corrected < diff_original and diff_corrected < 7200:
                return corrected
            return creation_time
        except Exception:
            return creation_time

    def _ensure_utc(self, dt: datetime) -> datetime:
        if dt.tzinfo is None:
            local_tz = pytz.timezone(self.local_timezone)
            dt = local_tz.localize(dt)
        return dt.astimezone(timezone.utc)
