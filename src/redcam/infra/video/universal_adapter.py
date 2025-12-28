#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Adapter universel qui délègue à l'implémentation appropriée selon le type de caméra.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from redcam.core.ports.video_metadata import VideoMetadataPort
from redcam.domain.gps_types import GPSPoint
from redcam.infra.video.gopro_metadata_adapter import GoProVideoMetadataAdapter
from redcam.infra.video.generic_metadata_adapter import GenericVideoMetadataAdapter


class UniversalVideoMetadataAdapter(VideoMetadataPort):
    """
    Adapter composite qui choisit la stratégie d'extraction selon la configuration.
    """
    
    def __init__(self) -> None:
        self._gopro_adapter = GoProVideoMetadataAdapter()
        self._generic_adapter = GenericVideoMetadataAdapter()
        self._current_adapter: VideoMetadataPort = self._gopro_adapter
        self._camera_type = "Auto"

    def set_camera_type(self, camera_type: str) -> None:
        """
        Définit le type de caméra pour choisir l'adapter.
        
        Args:
            camera_type: "GoPro", "DJI", "Insta360", "Auto", etc.
        """
        self._camera_type = camera_type
        
        if "DJI" in camera_type or "Insta360" in camera_type:
            self._current_adapter = self._generic_adapter
        elif "Hero 12" in camera_type:
             # Hero 12 n'a pas de GPS, on peut utiliser le générique ou le GoPro (qui retournera None)
             # Utiliser le générique évite de chercher inutilement le GPMF
             self._current_adapter = self._generic_adapter
        else:
            # Par défaut (Auto, Hero 10+, etc.) on utilise l'adapter GoPro
            # qui tentera de trouver le GPS, et fallbackera sur la date si besoin.
            self._current_adapter = self._gopro_adapter

    def get_creation_time(self, video_path: str) -> Optional[datetime]:
        return self._current_adapter.get_creation_time(video_path)

    def get_duration_seconds(self, video_path: str) -> Optional[float]:
        return self._current_adapter.get_duration_seconds(video_path)

    def extract_embedded_gps(self, video_path: str) -> Optional[list[GPSPoint]]:
        return self._current_adapter.extract_embedded_gps(video_path)
