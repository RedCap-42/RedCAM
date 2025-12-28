#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Adapter générique pour les caméras sans extraction GPS spécifique (DJI, Insta360, etc.).
Se base uniquement sur les métadonnées standard (date de création) pour la synchro .fit.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from redcam.core.ports.video_metadata import VideoMetadataPort
from redcam.domain.gps_types import GPSPoint
from redcam.infra.video.ffmpeg_utils import FFmpegUtils


class GenericVideoMetadataAdapter(VideoMetadataPort):
    """
    Adapter pour les vidéos génériques (DJI, Insta360, etc.).
    Ne supporte pas (encore) l'extraction GPS embarqué, mais permet la synchro via .fit.
    """
    
    def __init__(self) -> None:
        self._ffmpeg = FFmpegUtils()
        self._cache: dict[str, dict[str, object]] = {}

    def get_creation_time(self, video_path: str) -> Optional[datetime]:
        cached = self._cache.get(video_path)
        if cached and "creation_time" in cached:
            return cached["creation_time"]  # type: ignore[return-value]

        creation_time = self._ffmpeg.get_video_creation_time(video_path)
        self._cache.setdefault(video_path, {})["creation_time"] = creation_time
        return creation_time

    def get_duration_seconds(self, video_path: str) -> Optional[float]:
        cached = self._cache.get(video_path)
        if cached and "duration_seconds" in cached:
            return cached["duration_seconds"]  # type: ignore[return-value]

        duration_seconds = self._ffmpeg.get_video_duration_seconds(video_path)
        self._cache.setdefault(video_path, {})["duration_seconds"] = duration_seconds
        return duration_seconds

    def extract_embedded_gps(self, video_path: str) -> Optional[list[GPSPoint]]:
        """
        Pas d'extraction GPS embarqué pour le moment pour ces caméras.
        Retourne None pour forcer l'utilisation du fichier .fit.
        """
        return None
