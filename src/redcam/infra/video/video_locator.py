#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Localisateur de vidéos pour RedCAM.
Implémente la logique de priorité GPS/Timestamp.
"""

import os
from datetime import datetime, timezone, timedelta
from typing import Optional, List
import pytz

from redcam.domain.gps_types import GPSPoint, GPSTrack, VideoLocation, LocationSource
from redcam.infra.gopro.gopro_gps_extractor import GoProGPSExtractor
from redcam.infra.garmin.fit_parser import FitParser


class VideoLocator:
    """
    Localise les vidéos GoPro sur la trace GPS.
    
    Logique de priorité:
    1. GPS intégré dans la vidéo (via gopro2gpx)
    2. Synchronisation timestamp avec fichier .fit
    """
    
    def __init__(
        self, 
        fit_parser: Optional[FitParser] = None,
        local_timezone: str = "Europe/Paris"
    ) -> None:
        """
        Initialise le localisateur.
        
        Args:
            fit_parser: Parser .fit pour la synchronisation
            local_timezone: Timezone locale des vidéos GoPro
        """
        self.fit_parser = fit_parser
        self.gps_extractor = GoProGPSExtractor()
        self.local_tz = pytz.timezone(local_timezone)
        self.cache = {} # Cache pour éviter de re-parser les fichiers
    
    def _smart_correct_timestamp(self, video_path: str, creation_time: Optional[datetime]) -> Optional[datetime]:
        """
        Corrige intelligemment le timestamp en le comparant au mtime du fichier
        ET à la trace GPS (.fit) si disponible.
        """
        if not creation_time:
            return None
            
        # 1. Correction basée sur la trace FIT (Priorité absolue)
        # Si le timestamp décalé tombe dans la trace alors que l'original non, c'est gagné.
        if self.fit_parser and self.fit_parser.track:
            # Essayer différents décalages horaires courants (UTC+1, UTC+2, etc.)
            offsets = [0, -3600, 3600, -7200, 7200] # 0h, -1h, +1h, -2h, +2h
            
            for offset in offsets:
                shifted_time = creation_time + timedelta(seconds=offset)
                if self.fit_parser.is_time_in_track(shifted_time):
                    if offset != 0:
                        print(f"  ! Correction FIT Sync appliquée: {creation_time} -> {shifted_time} (Offset {offset}s)")
                    return shifted_time

        # 2. Fallback: Correction basée sur le mtime (File System)
        try:
            # Obtenir le mtime (UTC fiable sur la plupart des OS modernes)
            mtime_ts = os.path.getmtime(video_path)
            mtime = datetime.fromtimestamp(mtime_ts, tz=timezone.utc)
            
            # Calculer la version corrigée (Local -> UTC)
            # On suppose que creation_time est en fait l'heure locale
            naive = creation_time.replace(tzinfo=None)
            local_dt = self.local_tz.localize(naive)
            corrected_time = local_dt.astimezone(timezone.utc)
            
            # Comparer les écarts avec mtime
            diff_original = abs((mtime - creation_time).total_seconds())
            diff_corrected = abs((mtime - corrected_time).total_seconds())
            
            # Si la version corrigée est significativement plus proche du mtime
            if diff_corrected < diff_original and diff_corrected < 7200: 
                 print(f"  ! Correction Timezone (mtime) appliquée: {creation_time} -> {corrected_time}")
                 return corrected_time
                 
            return creation_time
            
        except Exception as e:
            print(f"  ! Erreur correction timestamp: {e}")
            return creation_time

    def locate_video(
        self, 
        video_path: str,
        force_timestamp_sync: bool = False,
        camera_filter: str = "Auto (Détection)"
    ) -> VideoLocation:
        """
        Localise une vidéo sur la carte.
        
        Args:
            video_path: Chemin absolu vers le fichier vidéo
            force_timestamp_sync: Si True, ignore le GPS intégré et force la synchro timestamp
            camera_filter: Filtre de modèle de caméra
            
        Returns:
            VideoLocation avec la position et la source
        """
        video_name = os.path.basename(video_path)
        gps_points = None
        creation_time = None
        duration_seconds: Optional[float] = None
        
        # Logique spécifique au filtre caméra
        if camera_filter == "Hero 12 (Pas de GPS)":
            force_timestamp_sync = True
            
        # Vérifier le cache
        if video_path in self.cache:
            cached_data = self.cache[video_path]
            creation_time = cached_data.get('creation_time')
            gps_points = cached_data.get('gps_points')
            duration_seconds = cached_data.get('duration_seconds')
        else:
            # Extraction initiale (coûteux)
            raw_creation_time = self.gps_extractor.get_video_creation_time(video_path)
            
            # Correction intelligente du timestamp (Local vs UTC)
            creation_time = self._smart_correct_timestamp(video_path, raw_creation_time)

            # Durée vidéo (pour UI timeline)
            duration_seconds = self.gps_extractor.get_video_duration_seconds(video_path)
            
            # Tenter d'extraire le GPS sauf si on sait que c'est une Hero 12
            if not force_timestamp_sync or camera_filter != "Hero 12 (Pas de GPS)":
                raw_gps_points, _ = self.gps_extractor.extract_gps(video_path)
                gps_points = raw_gps_points if raw_gps_points and len(raw_gps_points) > 0 else None
            else:
                gps_points = None
                
            # Stocker en cache
            self.cache[video_path] = {
                'creation_time': creation_time,
                'gps_points': gps_points,
                'duration_seconds': duration_seconds
            }
        
        # Logique de décision (rapide avec le cache)
        
        # Priorité 1: Utiliser GPS intégré extrait (si disponible et non forcé)
        if not force_timestamp_sync and gps_points:
            # GPS trouvé et mode Weak GPS désactivé
            first_point = gps_points[0]
            print(f"✓ {video_name}: GPS intégré trouvé (Cache utilisé)")
            
            return VideoLocation(
                video_path=video_path,
                video_name=video_name,
                position=first_point,
                source=LocationSource.EMBEDDED_GPS,
                creation_time=creation_time,
                duration_seconds=duration_seconds
            )
        elif force_timestamp_sync:
             if camera_filter == "Hero 12 (Pas de GPS)":
                 print(f"  {video_name}: Hero 12 détectée, synchro .fit activée (Pas de GPS intégré)")
             elif gps_points:
                 print(f"  {video_name}: Synchro forcée (GPS intégré ignoré)")
        
        # Priorité 2: Synchronisation avec le fichier .fit
        if self.fit_parser is not None and self.fit_parser.track is not None:
            if creation_time:
                # Convertir en UTC si nécessaire
                video_time_utc = self._ensure_utc(creation_time)
                
                # Chercher la position dans la trace .fit
                position = self.fit_parser.get_position_at_time(video_time_utc)
                
                if position:
                    print(f"✓ {video_name}: Synchronisé avec trace .fit")
                    return VideoLocation(
                        video_path=video_path,
                        video_name=video_name,
                        position=position,
                        source=LocationSource.FIT_SYNC,
                        creation_time=creation_time,
                        duration_seconds=duration_seconds
                    )
                else:
                    print(f"✗ {video_name}: Timestamp hors de la trace .fit")
            else:
                print(f"✗ {video_name}: Impossible de lire le timestamp")
        else:
            print(f"✗ {video_name}: Pas de GPS et pas de fichier .fit chargé")
        
        # Aucune localisation trouvée
        return VideoLocation(
            video_path=video_path,
            video_name=video_name,
            position=None,
            source=LocationSource.UNKNOWN,
            creation_time=creation_time,
            duration_seconds=duration_seconds
        )
    
    def locate_videos_in_folder(
        self, 
        folder_path: str,
        extensions: Optional[List[str]] = None,
        progress_callback = None,
        force_timestamp_sync: bool = False,
        camera_filter: str = "Auto (Détection)"
    ) -> List[VideoLocation]:
        """
        Localise toutes les vidéos d'un dossier.
        
        Args:
            folder_path: Chemin vers le dossier
            extensions: Extensions à rechercher (défaut: .mp4, .MP4)
            progress_callback: Fonction de callback (current, total)
            force_timestamp_sync: Forcer la synchro timestamp
            camera_filter: Filtre de modèle de caméra
            
        Returns:
            Liste de VideoLocation
        """
        if extensions is None:
            extensions = [".mp4", ".MP4"]

        
        # Lister les fichiers vidéo
        video_files = []
        for filename in os.listdir(folder_path):
            _, ext = os.path.splitext(filename)
            if ext in extensions:
                video_files.append(os.path.join(folder_path, filename))
        
        if not video_files:
            print(f"Aucune vidéo trouvée dans {folder_path}")
            return []
        
        print(f"Traitement de {len(video_files)} vidéos...")
        
        # Traiter chaque vidéo
        locations = []
        for i, video_path in enumerate(video_files):
            location = self.locate_video(video_path, force_timestamp_sync)
            locations.append(location)
            
            if progress_callback:
                progress_callback(i + 1, len(video_files))
        
        # Statistiques
        located = sum(1 for loc in locations if loc.is_located())
        embedded = sum(1 for loc in locations if loc.source == LocationSource.EMBEDDED_GPS)
        synced = sum(1 for loc in locations if loc.source == LocationSource.FIT_SYNC)
        
        print(f"\nRésultat: {located}/{len(locations)} vidéos localisées")
        print(f"  - GPS intégré: {embedded}")
        print(f"  - Synchronisé .fit: {synced}")
        
        return locations
    
    def _ensure_utc(self, dt: datetime) -> datetime:
        """
        S'assure que le datetime est en UTC.
        
        Args:
            dt: datetime à convertir
            
        Returns:
            datetime en UTC
        """
        if dt.tzinfo is None:
            # Assumer que c'est en heure locale
            dt = self.local_tz.localize(dt)
        
        return dt.astimezone(timezone.utc)
    
    def set_fit_parser(self, fit_parser: FitParser) -> None:
        """
        Configure le parser .fit pour la synchronisation.
        
        Args:
            fit_parser: Instance de FitParser avec track parsée
        """
        self.fit_parser = fit_parser
