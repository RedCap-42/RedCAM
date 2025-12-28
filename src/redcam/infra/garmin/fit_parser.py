#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Parser de fichiers Garmin .fit pour RedCAM.
Extrait les points GPS et construit une trace.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List
import os

from redcam.domain.gps_types import GPSPoint, GPSTrack


# Constante de conversion semicircles -> degrés
SEMICIRCLES_TO_DEGREES: float = 180.0 / (2 ** 31)


class FitParser:
    """
    Parser pour les fichiers Garmin .fit.
    Utilise la bibliothèque fitparse pour extraire les données GPS.
    """
    
    def __init__(self, filepath: str) -> None:
        """
        Initialise le parser avec le chemin du fichier .fit.
        
        Args:
            filepath: Chemin absolu vers le fichier .fit
        """
        self.filepath = filepath
        self.track: Optional[GPSTrack] = None
        
    def parse(self) -> Optional[GPSTrack]:
        """
        Parse le fichier .fit et retourne la trace GPS.
        
        Returns:
            GPSTrack contenant tous les points GPS, ou None si erreur
        """
        try:
            from fitparse import FitFile
        except ImportError:
            print("Erreur: La bibliothèque 'fitparse' n'est pas installée.")
            print("Installez-la avec: pip install fitparse")
            return None
        
        if not os.path.exists(self.filepath):
            print(f"Erreur: Le fichier n'existe pas: {self.filepath}")
            return None
        
        try:
            fit_file = FitFile(self.filepath)
            points: List[GPSPoint] = []
            
            # Parcourir les messages "record" qui contiennent les données GPS
            for record in fit_file.get_messages("record"):
                point = self._extract_point_from_record(record)
                if point and point.is_valid():
                    points.append(point)
            
            if not points:
                print(f"Avertissement: Aucun point GPS trouvé dans {self.filepath}")
                return None
            
            # Créer la trace GPS
            name = os.path.basename(self.filepath)
            start_time = points[0].timestamp if points else None
            end_time = points[-1].timestamp if points else None
            
            # Afficher la plage temporelle de la trace
            print(f"\n=== TRACE GPS ===")
            if start_time:
                print(f"  Début: {start_time}")
            if end_time:
                print(f"  Fin:   {end_time}")
            print(f"=================\n")
            
            self.track = GPSTrack(
                name=name,
                points=points,
                start_time=start_time,
                end_time=end_time
            )
            
            print(f"Fichier .fit parsé: {len(points)} points GPS trouvés")
            return self.track
            
        except Exception as e:
            print(f"Erreur lors du parsing du fichier .fit: {e}")
            return None
    
    def _extract_point_from_record(self, record) -> Optional[GPSPoint]:
        """
        Extrait un point GPS depuis un enregistrement .fit.
        
        Args:
            record: Enregistrement fitparse
            
        Returns:
            GPSPoint ou None si données invalides
        """
        lat_semicircles = None
        lon_semicircles = None
        elevation = 0.0
        timestamp = None
        speed = 0.0
        
        for field in record:
            if field.name == "position_lat" and field.value is not None:
                lat_semicircles = field.value
            elif field.name == "position_long" and field.value is not None:
                lon_semicircles = field.value
            elif field.name == "altitude" and field.value is not None:
                # L'altitude peut être en enhanced_altitude ou altitude
                elevation = float(field.value)
            elif field.name == "enhanced_altitude" and field.value is not None:
                elevation = float(field.value)
            elif field.name == "timestamp" and field.value is not None:
                # Les timestamps .fit sont en UTC
                timestamp = field.value
                if timestamp and timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
            elif field.name == "speed" and field.value is not None:
                speed = float(field.value)
            elif field.name == "enhanced_speed" and field.value is not None:
                speed = float(field.value)
        
        # Conversion semicircles -> degrés
        if lat_semicircles is None or lon_semicircles is None:
            return None
        
        latitude = lat_semicircles * SEMICIRCLES_TO_DEGREES
        longitude = lon_semicircles * SEMICIRCLES_TO_DEGREES
        
        return GPSPoint(
            latitude=latitude,
            longitude=longitude,
            elevation=elevation,
            timestamp=timestamp,
            speed=speed
        )
    
    def is_time_in_track(self, time_to_check: datetime, tolerance_seconds: float = 300.0) -> bool:
        """
        Vérifie si un temps donné est inclus dans la plage temporelle de la trace.
        
        Args:
            time_to_check: Temps à vérifier (UTC)
            tolerance_seconds: Tolérance en secondes (défaut 5 min)
            
        Returns:
            True si le temps est dans la trace (avec tolérance)
        """
        if not self.track or not self.track.start_time or not self.track.end_time:
            return False
            
        start = self.track.start_time - timedelta(seconds=tolerance_seconds)
        end = self.track.end_time + timedelta(seconds=tolerance_seconds)
        
        return start <= time_to_check <= end

    def get_position_at_time(
        self, 
        target_time: datetime,
        tolerance_hours: float = 2.0
    ) -> Optional[GPSPoint]:
        """
        Retourne la position GPS à un instant donné par interpolation.
        
        Args:
            target_time: Horodatage cible (timezone-aware)
            tolerance_hours: Tolérance en heures pour le décalage horaire
            
        Returns:
            GPSPoint interpolé ou None si hors limites
        """
        if self.track is None or self.track.is_empty():
            return None
        
        points = self.track.points
        
        # S'assurer que le timestamp cible est timezone-aware
        if target_time.tzinfo is None:
            target_time = target_time.replace(tzinfo=timezone.utc)
        
        # D'abord essayer une correspondance exacte
        result = self._find_position_exact(points, target_time)
        if result:
            return result
        
        # Sinon, essayer avec des décalages horaires courants
        # (problème fréquent: GoPro en heure locale vs .fit en UTC)
        for offset_hours in [0, 1, -1, 2, -2]:
            adjusted_time = target_time + timedelta(hours=offset_hours)
            result = self._find_position_exact(points, adjusted_time)
            if result:
                if offset_hours != 0:
                    print(f"    [Décalage horaire détecté: {offset_hours:+d}h]")
                return result
        
        # Si toujours rien, retourner le point le plus proche si dans la tolérance
        nearest = self._find_nearest_point(target_time)
        if nearest and nearest.timestamp:
            diff_hours = abs((nearest.timestamp - target_time).total_seconds()) / 3600
            if diff_hours <= tolerance_hours:
                print(f"    [Point le plus proche à {diff_hours:.1f}h]")
                return nearest
        
        return None
    
    def _find_position_exact(
        self, 
        points: list, 
        target_time: datetime
    ) -> Optional[GPSPoint]:
        """
        Cherche une position exacte dans la trace.
        
        Args:
            points: Liste de points GPS
            target_time: Temps cible
            
        Returns:
            GPSPoint ou None
        """
        # Vérifier les limites
        if points[0].timestamp and target_time < points[0].timestamp:
            return None
        if points[-1].timestamp and target_time > points[-1].timestamp:
            return None
        
        # Rechercher les deux points encadrant le timestamp
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]
            
            if p1.timestamp is None or p2.timestamp is None:
                continue
            
            if p1.timestamp <= target_time <= p2.timestamp:
                return self._interpolate(p1, p2, target_time)
        
        return None
    
    def _interpolate(
        self, 
        p1: GPSPoint, 
        p2: GPSPoint, 
        target_time: datetime
    ) -> GPSPoint:
        """
        Interpole linéairement entre deux points GPS.
        
        Args:
            p1: Premier point (avant)
            p2: Deuxième point (après)
            target_time: Temps cible
            
        Returns:
            Point GPS interpolé
        """
        if p1.timestamp is None or p2.timestamp is None:
            return p1
        
        # Calculer le ratio d'interpolation
        total_seconds = (p2.timestamp - p1.timestamp).total_seconds()
        if total_seconds == 0:
            return p1
        
        elapsed_seconds = (target_time - p1.timestamp).total_seconds()
        ratio = elapsed_seconds / total_seconds
        
        # Interpoler les coordonnées
        lat = p1.latitude + (p2.latitude - p1.latitude) * ratio
        lon = p1.longitude + (p2.longitude - p1.longitude) * ratio
        elev = p1.elevation + (p2.elevation - p1.elevation) * ratio
        speed = p1.speed + (p2.speed - p1.speed) * ratio
        
        return GPSPoint(
            latitude=lat,
            longitude=lon,
            elevation=elev,
            timestamp=target_time,
            speed=speed
        )
    
    def _find_nearest_point(self, target_time: datetime) -> Optional[GPSPoint]:
        """
        Trouve le point GPS le plus proche temporellement.
        
        Args:
            target_time: Temps cible
            
        Returns:
            Point GPS le plus proche
        """
        if self.track is None or self.track.is_empty():
            return None
        
        nearest = None
        min_diff = float('inf')
        
        for point in self.track.points:
            if point.timestamp is None:
                continue
            
            diff = abs((point.timestamp - target_time).total_seconds())
            if diff < min_diff:
                min_diff = diff
                nearest = point
        
        return nearest
