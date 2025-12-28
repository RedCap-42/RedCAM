#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Types de données GPS pour RedCAM.
Définit les dataclasses utilisées dans toute l'application.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class LocationSource(Enum):
    """Source de la localisation d'une vidéo."""
    EMBEDDED_GPS = "GPS intégré"      # GPS extrait directement de la vidéo GoPro
    FIT_SYNC = "Synchronisé .fit"     # Position interpolée depuis le fichier .fit
    UNKNOWN = "Inconnu"               # Source inconnue


@dataclass
class GPSPoint:
    """
    Représente un point GPS unique.
    
    Attributes:
        latitude: Latitude en degrés décimaux
        longitude: Longitude en degrés décimaux
        elevation: Altitude en mètres
        timestamp: Horodatage du point (timezone-aware si possible)
        speed: Vitesse en m/s (optionnel)
    """
    latitude: float
    longitude: float
    elevation: float = 0.0
    timestamp: Optional[datetime] = None
    speed: float = 0.0
    
    def is_valid(self) -> bool:
        """Vérifie si le point a des coordonnées valides."""
        return (
            self.latitude != 0.0 or self.longitude != 0.0
        ) and (
            -90 <= self.latitude <= 90
        ) and (
            -180 <= self.longitude <= 180
        )


@dataclass
class GPSTrack:
    """
    Représente une trace GPS complète.
    
    Attributes:
        name: Nom de la trace (ex: nom du fichier)
        points: Liste des points GPS
        start_time: Temps de début de la trace
        end_time: Temps de fin de la trace
    """
    name: str
    points: List[GPSPoint] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def is_empty(self) -> bool:
        """Vérifie si la trace est vide."""
        return len(self.points) == 0
    
    def get_bounds(self) -> tuple:
        """
        Retourne les limites géographiques de la trace.
        
        Returns:
            Tuple (min_lat, min_lon, max_lat, max_lon)
        """
        if self.is_empty():
            return (0.0, 0.0, 0.0, 0.0)
        
        lats = [p.latitude for p in self.points if p.is_valid()]
        lons = [p.longitude for p in self.points if p.is_valid()]
        
        if not lats or not lons:
            return (0.0, 0.0, 0.0, 0.0)
        
        return (min(lats), min(lons), max(lats), max(lons))
    
    def get_center(self) -> tuple:
        """
        Retourne le centre géographique de la trace.
        
        Returns:
            Tuple (lat, lon)
        """
        bounds = self.get_bounds()
        center_lat = (bounds[0] + bounds[2]) / 2
        center_lon = (bounds[1] + bounds[3]) / 2
        return (center_lat, center_lon)


@dataclass
class VideoLocation:
    """
    Représente la localisation d'une vidéo sur la carte.
    
    Attributes:
        video_path: Chemin absolu vers le fichier vidéo
        video_name: Nom du fichier vidéo
        position: Point GPS de la position
        source: Source de la localisation (GPS intégré ou sync)
        creation_time: Horodatage de création de la vidéo
        duration_seconds: Durée de la vidéo en secondes (si connue)
    """
    video_path: str
    video_name: str
    position: Optional[GPSPoint]
    source: LocationSource = LocationSource.UNKNOWN
    creation_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    # Custom properties (User editable)
    custom_name: Optional[str] = None
    custom_note: Optional[str] = None  # Note affichée sur la carte
    marker_color: str = "#3388ff"  # Default blue
    marker_icon: str = "circle"    # Default shape
    
    def is_located(self) -> bool:
        """Vérifie si la vidéo a une position valide."""
        return self.position is not None and self.position.is_valid()
