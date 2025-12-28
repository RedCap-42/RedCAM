#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Workers QThread pour RedCAM.
Gère le traitement asynchrone pour ne pas bloquer l'UI.
"""

from typing import Optional, List
from PyQt6.QtCore import QThread, pyqtSignal

from redcam.domain.gps_types import GPSTrack, VideoLocation
from redcam.services.sync_controller import SyncController


class ProcessingWorker(QThread):
    """
    Worker pour le traitement des fichiers en arrière-plan.
    Émet des signaux pour la progression et les résultats.
    """
    
    # Signaux
    progress = pyqtSignal(int, int)  # (current, total)
    fit_loaded = pyqtSignal(object)  # GPSTrack
    videos_processed = pyqtSignal(list)  # List[VideoLocation]
    error = pyqtSignal(str)
    finished_processing = pyqtSignal()
    status_update = pyqtSignal(str)  # Message de statut
    
    def __init__(
        self, 
        controller: SyncController,
        fit_path: Optional[str] = None,
        video_folder: Optional[str] = None
    ) -> None:
        """
        Initialise le worker.
        
        Args:
            controller: Contrôleur de synchronisation
            fit_path: Chemin vers le fichier .fit (optionnel)
            video_folder: Chemin vers le dossier vidéos (optionnel)
        """
        super().__init__()
        self.controller = controller
        self.fit_path = fit_path
        self.video_folder = video_folder
    
    def run(self) -> None:
        """Exécute le traitement en arrière-plan."""
        try:
            # Charger le fichier .fit si spécifié
            if self.fit_path:
                self.status_update.emit("Chargement du fichier .fit...")
                success = self.controller.load_fit_file(self.fit_path)
                
                if success and self.controller.track:
                    self.fit_loaded.emit(self.controller.track)
                    self.status_update.emit(
                        f"Trace GPS chargée: {len(self.controller.track.points)} points"
                    )
                elif self.fit_path:
                    self.error.emit(
                        f"Impossible de lire le fichier .fit: {self.fit_path}"
                    )
            
            # Définir le dossier vidéo si spécifié
            if self.video_folder:
                self.controller.set_video_folder(self.video_folder)
            
            # Traiter les vidéos
            if self.controller.video_folder:
                self.status_update.emit("Traitement des vidéos...")
                
                def on_progress(current: int, total: int):
                    self.progress.emit(current, total)
                    self.status_update.emit(f"Vidéo {current}/{total}...")
                
                locations = self.controller.process_videos(
                    progress_callback=on_progress,
                    force_timestamp_sync=getattr(self, 'force_timestamp_sync', False),
                    camera_filter=getattr(self, 'camera_filter', "Auto (Détection)"),
                    manual_offset_seconds=getattr(self, 'manual_offset_seconds', 0.0)
                )
                
                self.videos_processed.emit(locations)
                
                # Résumé
                summary = self.controller.get_summary()
                self.status_update.emit(
                    f"Terminé: {summary['located_videos']}/{summary['total_videos']} "
                    f"vidéos localisées"
                )
            
            self.finished_processing.emit()
            
        except Exception as e:
            self.error.emit(f"Erreur de traitement: {str(e)}")
            self.finished_processing.emit()


class FitLoadWorker(QThread):
    """Worker dédié au chargement du fichier .fit."""
    
    loaded = pyqtSignal(object)  # GPSTrack
    error = pyqtSignal(str)
    
    def __init__(self, controller: SyncController, fit_path: str) -> None:
        super().__init__()
        self.controller = controller
        self.fit_path = fit_path
    
    def run(self) -> None:
        try:
            success = self.controller.load_fit_file(self.fit_path)
            if success and self.controller.track:
                self.loaded.emit(self.controller.track)
            else:
                self.error.emit("Impossible de lire le fichier .fit")
        except Exception as e:
            self.error.emit(str(e))


class VideoProcessWorker(QThread):
    """Worker dédié au traitement des vidéos."""
    
    progress = pyqtSignal(int, int)
    processed = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(
        self, 
        controller: SyncController, 
        video_folder: str
    ) -> None:
        super().__init__()
        self.controller = controller
        self.video_folder = video_folder
    
    def run(self) -> None:
        try:
            self.controller.set_video_folder(self.video_folder)
            
            def on_progress(current: int, total: int):
                self.progress.emit(current, total)
            
            locations = self.controller.process_videos(
                progress_callback=on_progress
            )
            self.processed.emit(locations)
            
        except Exception as e:
            self.error.emit(str(e))
