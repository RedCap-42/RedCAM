#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extracteur GPS pour vidéos GoPro - Implémentation complète.
Réimplémentation du parsing GPMF sans dépendance à gopro2gpx.
Utilise ffmpeg/ffprobe directement.
"""

import os
import subprocess
import struct
import json
import array
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Tuple, NamedTuple
from dataclasses import dataclass

from redcam.domain.gps_types import GPSPoint
from redcam.infra.video.ffmpeg_utils import FFmpegUtils


# =============================================================================
# Types de données GPMF
# =============================================================================

class GPS5Data(NamedTuple):
    """Données GPS5 (Hero 10 et antérieur)"""
    lat: float
    lon: float
    alt: float
    speed: float
    speed3d: float


class GPS9Data(NamedTuple):
    """Données GPS9 (Hero 11+)"""
    lat: float
    lon: float
    alt: float
    speed: float
    speed3d: float
    days_since_2000: float
    secs_since_midnight: float
    dop: float
    fix: float


# =============================================================================
# Parser GPMF
# =============================================================================

class GpmfParser:
    """
    Parser pour le format GPMF (GoPro Metadata Format).
    Extrait les données GPS directement depuis les métadonnées vidéo.
    """
    
    # Format de l'en-tête KLV: fourCC (4 bytes), type (1), size (1), repeat (2)
    HEADER_FORMAT = '>4sBBH'
    HEADER_SIZE = 8
    
    # Mapping des types
    TYPE_MAP = {
        ord('c'): 'c', ord('L'): 'L', ord('s'): 'h', ord('S'): 'H',
        ord('f'): 'f', ord('U'): 'c', ord('l'): 'l', ord('B'): 'B', ord('J'): 'Q'
    }
    
    def __init__(self) -> None:
        self.scale = [1, 1, 1, 1, 1, 1, 1, 1, 1]
        self.gps_fix = 0
        self.gps_precision = 0
        self.gps_time: Optional[datetime] = None
        
    def parse(self, raw_data: bytes) -> List[GPSPoint]:
        """
        Parse les données GPMF et extrait les points GPS.
        
        Args:
            raw_data: Données binaires GPMF
            
        Returns:
            Liste de GPSPoint
        """
        data = array.array('b')
        data.frombytes(raw_data)
        
        points: List[GPSPoint] = []
        offset = 0
        
        while offset < len(data):
            try:
                # Lire l'en-tête
                header_data = raw_data[offset:offset + self.HEADER_SIZE]
                if len(header_data) < self.HEADER_SIZE:
                    break
                
                fourcc_bytes, type_byte, size, repeat = struct.unpack(
                    self.HEADER_FORMAT, header_data
                )
                
                # Décoder le fourCC
                try:
                    fourcc = fourcc_bytes.decode('utf-8')
                except:
                    fourcc = "ERRU"
                
                # Calculer la longueur des données
                length = size * repeat
                padded_length = self._pad(length)
                
                # Lire les données
                data_start = offset + self.HEADER_SIZE
                data_end = data_start + padded_length
                raw_content = raw_data[data_start:data_end] if type_byte != 0 else None
                
                # Traiter selon le type de données
                new_points = self._process_klv(fourcc, type_byte, size, repeat, raw_content)
                if new_points:
                    points.extend(new_points)
                
                # Avancer l'offset
                offset += self.HEADER_SIZE
                if type_byte != 0:
                    offset += padded_length
                    
            except Exception as e:
                # Continuer en cas d'erreur
                offset += self.HEADER_SIZE
                continue
        
        return points
    
    def _pad(self, n: int, base: int = 4) -> int:
        """Arrondit au multiple de base supérieur."""
        while n % base != 0:
            n += 1
        return n
    
    def _map_type(self, type_byte: int) -> str:
        """Convertit le type byte en format struct."""
        return self.TYPE_MAP.get(type_byte, chr(type_byte))
    
    def _process_klv(
        self, 
        fourcc: str, 
        type_byte: int, 
        size: int, 
        repeat: int, 
        raw_content: Optional[bytes]
    ) -> Optional[List[GPSPoint]]:
        """
        Traite une entrée KLV.
        
        Returns:
            Liste de GPSPoint pour GPS5/GPS9, None sinon
        """
        if fourcc == 'SCAL':
            # Facteurs d'échelle
            self._parse_scale(type_byte, repeat, raw_content)
            
        elif fourcc == 'GPSU':
            # Timestamp GPS
            self._parse_gps_time(raw_content)
            
        elif fourcc == 'GPSF':
            # GPS Fix status
            if raw_content:
                stype = self._map_type(type_byte)
                s = struct.Struct('>' + stype)
                self.gps_fix = s.unpack_from(raw_content)[0]
                
        elif fourcc == 'GPSP':
            # GPS Precision (DOP)
            if raw_content:
                stype = self._map_type(type_byte)
                s = struct.Struct('>' + stype)
                self.gps_precision = s.unpack_from(raw_content)[0]
                
        elif fourcc == 'GPS5':
            # Données GPS (Hero 10 et antérieur)
            return self._parse_gps5(type_byte, size, repeat, raw_content)
            
        elif fourcc == 'GPS9':
            # Données GPS (Hero 11+)
            return self._parse_gps9(type_byte, size, repeat, raw_content)
        
        return None
    
    def _parse_scale(self, type_byte: int, repeat: int, raw_content: Optional[bytes]) -> None:
        """Parse les facteurs d'échelle SCAL."""
        if not raw_content:
            return
        
        stype = self._map_type(type_byte)
        
        if repeat == 1:
            s = struct.Struct('>' + stype)
            self.scale = [s.unpack_from(raw_content)[0]] * 9
        else:
            fmt = '>' + stype * repeat
            s = struct.Struct(fmt)
            self.scale = list(s.unpack_from(raw_content))
            # Compléter avec des 1 si nécessaire
            while len(self.scale) < 9:
                self.scale.append(1)
    
    def _parse_gps_time(self, raw_content: Optional[bytes]) -> None:
        """Parse le timestamp GPS (format: yymmddhhmmss.ffffff)."""
        if not raw_content:
            return
        
        try:
            s = raw_content.decode('utf-8', errors='replace')
            fmt = '%y%m%d%H%M%S.%f'
            self.gps_time = datetime.strptime(s, fmt)
            self.gps_time = self.gps_time.replace(tzinfo=timezone.utc)
        except:
            pass
    
    def _parse_gps5(
        self, 
        type_byte: int, 
        size: int, 
        repeat: int, 
        raw_content: Optional[bytes]
    ) -> List[GPSPoint]:
        """Parse les données GPS5."""
        points = []
        
        if not raw_content:
            return points
        
        # Ignorer si pas de fix GPS valide
        if self.gps_fix == 0:
            return points
        
        # Ignorer si précision trop mauvaise (DOP > 2000)
        if self.gps_precision > 2000:
            return points
        
        stype = self._map_type(type_byte)
        item_size = size * 5  # 5 champs
        
        for r in range(repeat):
            try:
                s = struct.Struct('>' + stype * 5)
                data = s.unpack_from(raw_content[r * item_size:(r + 1) * item_size])
                
                # Appliquer l'échelle
                lat = data[0] / self.scale[0] if self.scale[0] else data[0]
                lon = data[1] / self.scale[1] if self.scale[1] else data[1]
                alt = data[2] / self.scale[2] if self.scale[2] else data[2]
                speed = data[3] / self.scale[3] if self.scale[3] else data[3]
                
                # Ignorer les points invalides
                if lat == 0 and lon == 0:
                    continue
                
                # Calculer le temps pour ce point (interpolation)
                point_time = self.gps_time
                if self.gps_time and repeat > 1:
                    # ~18 Hz pour GPS5
                    delta = timedelta(seconds=r * (1/18.0))
                    point_time = self.gps_time + delta
                
                point = GPSPoint(
                    latitude=lat,
                    longitude=lon,
                    elevation=alt,
                    timestamp=point_time,
                    speed=speed
                )
                
                if point.is_valid():
                    points.append(point)
                    
            except Exception:
                continue
        
        return points
    
    def _parse_gps9(
        self, 
        type_byte: int, 
        size: int, 
        repeat: int, 
        raw_content: Optional[bytes]
    ) -> List[GPSPoint]:
        """Parse les données GPS9 (Hero 11+)."""
        points = []
        
        if not raw_content:
            return points
        
        # Structure GPS9: 7 x int32 + 2 x uint16 = 32 bytes
        item_size = 4 * 7 + 2 * 2
        
        for r in range(repeat):
            try:
                s = struct.Struct('>lllllllHH')
                data = s.unpack_from(raw_content[r * item_size:(r + 1) * item_size])
                
                # Données GPS9
                fix = data[8]
                dop = data[7]
                
                # Ignorer si pas de fix
                if fix == 0:
                    continue
                
                # Ignorer si DOP trop élevé
                if dop > 2000:
                    continue
                
                # Appliquer l'échelle
                lat = data[0] / self.scale[0] if self.scale[0] else data[0]
                lon = data[1] / self.scale[1] if self.scale[1] else data[1]
                alt = data[2] / self.scale[2] if self.scale[2] else data[2]
                speed = data[3] / self.scale[3] if self.scale[3] else data[3]
                
                # Ignorer les points invalides
                if lat == 0 and lon == 0:
                    continue
                
                # Calculer le temps depuis les données GPS9
                days = data[5] / self.scale[5] if self.scale[5] else data[5]
                secs = data[6] / self.scale[6] if self.scale[6] else data[6]
                
                # Date de référence: 1er janvier 2000
                target_date = datetime(2000, 1, 1, tzinfo=timezone.utc)
                point_time = target_date + timedelta(days=days, seconds=secs)
                
                point = GPSPoint(
                    latitude=lat,
                    longitude=lon,
                    elevation=alt,
                    timestamp=point_time,
                    speed=speed
                )
                
                if point.is_valid():
                    points.append(point)
                    
            except Exception:
                continue
        
        return points


# =============================================================================
# Extracteur principal
# =============================================================================

class GoProGPSExtractor:
    """
    Extracteur GPS pour vidéos GoPro.
    Utilise ffmpeg/ffprobe directement sans dépendance externe.
    """
    
    def __init__(self) -> None:
        """Initialise l'extracteur."""
        self.ffmpeg_utils = FFmpegUtils()
        self.ffprobe = self.ffmpeg_utils.ffprobe
        self.ffmpeg = self.ffmpeg_utils.ffmpeg
    
    def _get_metadata_track(self, video_path: str) -> Optional[int]:
        """
        Trouve le numéro de piste contenant les métadonnées GPMF.
        
        Args:
            video_path: Chemin vers la vidéo
            
        Returns:
            Numéro de piste ou None
        """
        try:
            args = [
                self.ffprobe, '-print_format', 'json', 
                '-show_streams', video_path
            ]
            output = self.ffmpeg_utils.run_command(args)
            
            if not output:
                return None
            
            data = json.loads(output)
            
            for stream in data.get('streams', []):
                if stream.get('codec_tag_string') == 'gpmd':
                    return int(stream['index'])
            
            return None
            
        except Exception:
            return None
    
    def _extract_metadata(self, video_path: str, track: int) -> bytes:
        """
        Extrait les données binaires de métadonnées.
        
        Args:
            video_path: Chemin vers la vidéo
            track: Numéro de piste
            
        Returns:
            Données binaires
        """
        try:
            args = [
                self.ffmpeg, '-y', '-i', video_path,
                '-codec', 'copy', '-map', f'0:{track}',
                '-f', 'rawvideo', '-'
            ]
            return self.ffmpeg_utils.run_command(args)
        except Exception:
            return b''
    
    def get_video_creation_time(self, video_path: str) -> Optional[datetime]:
        """Obtient le temps de création de la vidéo."""
        return self.ffmpeg_utils.get_video_creation_time(video_path)

    def get_video_duration_seconds(self, video_path: str) -> Optional[float]:
        """Retourne la durée (en secondes) via ffprobe."""
        return self.ffmpeg_utils.get_video_duration_seconds(video_path)
    
    def extract_gps(self, video_path: str) -> Tuple[Optional[List[GPSPoint]], Optional[datetime]]:
        """
        Extrait les points GPS d'une vidéo GoPro.
        
        Args:
            video_path: Chemin vers la vidéo
            
        Returns:
            (Liste de GPSPoint, datetime de création) ou (None, datetime)
        """
        video_name = os.path.basename(video_path)
        
        if not os.path.exists(video_path):
            return None, None
        
        # Obtenir le temps de création
        creation_time = self.get_video_creation_time(video_path)
        
        # Trouver la piste de métadonnées
        track = self._get_metadata_track(video_path)
        
        if track is None:
            print(f"  → {video_name}: Pas de données GPS")
            return None, creation_time
        
        # Extraire les métadonnées
        raw_data = self._extract_metadata(video_path, track)
        
        if not raw_data:
            print(f"  → {video_name}: Impossible d'extraire les métadonnées")
            return None, creation_time
        
        # Parser les données GPMF
        parser = GpmfParser()
        points = parser.parse(raw_data)
        
        if points:
            print(f"  → {video_name}: {len(points)} points GPS extraits")
            return points, creation_time
        else:
            print(f"  → {video_name}: Pas de points GPS valides")
            return None, creation_time
    
    def has_gps_track(self, video_path: str) -> bool:
        """
        Vérifie rapidement si une vidéo contient des données GPS.
        
        Args:
            video_path: Chemin vers la vidéo
            
        Returns:
            True si des données GPS sont présentes
        """
        return self._get_metadata_track(video_path) is not None

    def detect_camera_model(self, video_path: str) -> str:
        """
        Tente de détecter le modèle de caméra via les métadonnées.
        
        Args:
            video_path: Chemin vers la vidéo
            
        Returns:
            Nom du modèle (ex: "GoPro Hero 11") ou "Inconnu"
        """
        try:
            # Chercher dans les tags globaux (model, firmware)
            args = [
                self.ffprobe, '-v', 'quiet',
                '-show_entries', 'format_tags=model:format_tags=firmware',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            output = self.ffmpeg_utils.run_command(args).decode('utf-8', errors='ignore').strip()
            
            if "HERO" in output.upper():
                # Nettoyer et retourner la ligne contenant HERO
                for line in output.split('\n'):
                    if "HERO" in line.upper():
                        return line.strip()
            
            # Essayer de lire le nom du handler (souvent GoPro MET)
            args = [
                self.ffprobe, '-v', 'quiet',
                '-show_streams', '-select_streams', 'd',
                '-show_entries', 'stream_tags=handler_name',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            output = self.ffmpeg_utils.run_command(args).decode('utf-8', errors='ignore')
            
            if "HERO" in output.upper():
                 for line in output.split('\n'):
                    if "HERO" in line.upper():
                        return line.strip()
                        
            return "GoPro Inconnue"
            
        except Exception:
            return "Inconnu"
