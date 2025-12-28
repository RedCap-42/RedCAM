#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Façade "application" utilisée par l'UI.

Objectif: l'UI PyQt ne doit pas connaître l'infra (ffmpeg/fitparse/fs).
Le calcul est déporté dans `redcam.core` (usecase + ports).
"""

from typing import Optional, List, Callable
import os

from redcam.core.models.sync_models import SyncRequest
from redcam.core.usecases.sync_videos import SyncVideosUseCase
from redcam.domain.gps_types import GPSTrack, VideoLocation
from redcam.infra.garmin.fit_parser import FitParser
from redcam.infra.system.file_stat import OSFileStat
from redcam.infra.video.universal_adapter import UniversalVideoMetadataAdapter
from redcam.infra.video.os_video_catalog import OSVideoCatalog


class SyncController:
    """
    Contrôleur principal pour la synchronisation GPS/Vidéo.
    Gère le flux de traitement complet.
    """
    
    def __init__(self, local_timezone: str = "Europe/Paris") -> None:
        """
        Initialise le contrôleur.
        
        Args:
            local_timezone: Timezone locale pour les vidéos
        """
        self.local_timezone = local_timezone
        self.fit_parser: Optional[FitParser] = None
        self.track: Optional[GPSTrack] = None
        self.video_locations: List[VideoLocation] = []

        # Adapters infra (cache côté metadata)
        self._video_catalog = OSVideoCatalog()
        self._video_metadata = UniversalVideoMetadataAdapter()
        self._file_stat = OSFileStat()
        
        # Chemins chargés
        self.fit_path: Optional[str] = None
        self.video_folder: Optional[str] = None

    def set_camera_type(self, camera_type: str) -> None:
        """Définit le type de caméra (GoPro, DJI, Insta360...)."""
        self._video_metadata.set_camera_type(camera_type)
    
    def load_fit_file(self, filepath: str) -> bool:
        """
        Charge et parse un fichier .fit.
        
        Args:
            filepath: Chemin vers le fichier .fit
            
        Returns:
            True si le parsing a réussi
        """
        self.fit_path = filepath
        self.fit_parser = FitParser(filepath)
        self.track = self.fit_parser.parse()
        
        if self.track and not self.track.is_empty():
            return True
        
        return False
    
    def set_video_folder(self, folder_path: str) -> bool:
        """
        Définit le dossier contenant les vidéos.
        
        Args:
            folder_path: Chemin vers le dossier
            
        Returns:
            True si le dossier existe
        """
        if os.path.isdir(folder_path):
            self.video_folder = folder_path
            return True
        return False
    
    def process_videos(
        self, 
        progress_callback: Optional[Callable[[int, int], None]] = None,
        force_timestamp_sync: bool = False,
        camera_filter: str = "Auto (Détection)",
        manual_offset_seconds: float = 0.0
    ) -> List[VideoLocation]:
        """
        Traite toutes les vidéos du dossier sélectionné.
        
        Args:
            progress_callback: Fonction de callback (current, total)
            force_timestamp_sync: Forcer la synchro timestamp
            camera_filter: Filtre de modèle de caméra
            manual_offset_seconds: Décalage temporel manuel en secondes
            
        Returns:
            Liste des VideoLocation
        """
        if not self.video_folder:
            print("Erreur: Aucun dossier vidéo sélectionné")
            return []

        # Configurer l'adapter selon le filtre caméra
        self.set_camera_type(camera_filter)

        request = SyncRequest(
            fit_path=self.fit_path,
            video_folder=self.video_folder,
            force_timestamp_sync=force_timestamp_sync,
            camera_filter=camera_filter,
            local_timezone=self.local_timezone,
            manual_offset_seconds=manual_offset_seconds
        )

        # Use-case core
        usecase = SyncVideosUseCase(
            track_sync=self.fit_parser,
            video_catalog=self._video_catalog,
            video_metadata=self._video_metadata,
            file_stat=self._file_stat,
            local_timezone=self.local_timezone,
        )

        reporter = _CallbackProgressReporter(progress_callback) if progress_callback else None
        result = usecase.execute(request, reporter=reporter)
        self.video_locations = result.video_locations
        
        return self.video_locations

    def get_track(self) -> Optional[GPSTrack]:
        """Retourne la trace GPS chargée."""
        return self.track
    
    def get_video_locations(self) -> List[VideoLocation]:
        """Retourne les localisations des vidéos."""
        return self.video_locations
    
    def is_ready_to_process(self) -> bool:
        """Vérifie si les données sont prêtes pour le traitement."""
        return self.video_folder is not None
    
    def has_track(self) -> bool:
        """Vérifie si une trace GPS est chargée."""
        return self.track is not None and not self.track.is_empty()
    
    def get_summary(self) -> dict:
        """Retourne un résumé du traitement."""
        total = len(self.video_locations)
        located = sum(1 for v in self.video_locations if v.is_located())
        embedded = sum(
            1 for v in self.video_locations 
            if v.source.value == "GPS intégré"
        )
        synced = sum(
            1 for v in self.video_locations 
            if v.source.value == "Synchronisé .fit"
        )
        
        return {
            "total_videos": total,
            "located_videos": located,
            "embedded_gps": embedded,
            "fit_synced": synced,
            "not_located": total - located,
            "track_points": len(self.track.points) if self.track else 0,
        }


class _CallbackProgressReporter:
    def __init__(self, callback: Callable[[int, int], None]) -> None:
        self._callback = callback

    def report(self, event) -> None:
        if event.total and event.current:
            self._callback(event.current, event.total)
