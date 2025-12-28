#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilitaires FFmpeg partagés pour l'extraction de métadonnées vidéo.
"""

import os
import subprocess
from datetime import datetime, timezone
from typing import Optional, List

class FFmpegUtils:
    """
    Classe utilitaire pour interagir avec FFmpeg/FFprobe.
    """
    
    def __init__(self) -> None:
        self.ffprobe = self._find_ffprobe()
        self.ffmpeg = self._find_ffmpeg()
    
    def _find_ffprobe(self) -> str:
        """Trouve le chemin vers ffprobe."""
        import platform
        if platform.system() == 'Windows':
            return 'ffprobe.exe'
        return 'ffprobe'
    
    def _find_ffmpeg(self) -> str:
        """Trouve le chemin vers ffmpeg."""
        import platform
        if platform.system() == 'Windows':
            return 'ffmpeg.exe'
        return 'ffmpeg'
    
    def run_command(self, cmd: List[str]) -> bytes:
        """Exécute une commande et retourne la sortie."""
        try:
            result = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            return result.stdout
        except Exception as e:
            return b''

    def _parse_creation_time(self, time_str: str) -> Optional[datetime]:
        """Parse une chaîne de date ISO 8601."""
        try:
            if time_str.endswith('Z'):
                time_str = time_str[:-1]
            
            if '.' in time_str:
                base, micro = time_str.split('.')
                micro = micro[:6]
                time_str = f"{base}.{micro}"
                dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S.%f")
            else:
                dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S")
            
            return dt.replace(tzinfo=timezone.utc)
            
        except Exception:
            return None

    def get_video_creation_time(self, video_path: str) -> Optional[datetime]:
        """
        Obtient le temps de création de la vidéo.
        
        Args:
            video_path: Chemin vers la vidéo
            
        Returns:
            datetime de création (UTC) ou None
        """
        try:
            # Essayer d'abord les tags de format
            args = [
                self.ffprobe, '-v', 'quiet',
                '-show_entries', 'format_tags=creation_time',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            output = self.run_command(args).decode('utf-8').strip()
            
            if not output:
                # Fallback: tags du stream vidéo
                args = [
                    self.ffprobe, '-v', 'quiet',
                    '-select_streams', 'v:0',
                    '-show_entries', 'stream_tags=creation_time',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    video_path
                ]
                output = self.run_command(args).decode('utf-8').strip()
            
            if not output:
                # Dernier fallback: date de modification du fichier
                mtime = os.path.getmtime(video_path)
                return datetime.fromtimestamp(mtime, tz=timezone.utc)
            
            return self._parse_creation_time(output)
            
        except Exception:
            try:
                mtime = os.path.getmtime(video_path)
                return datetime.fromtimestamp(mtime, tz=timezone.utc)
            except:
                return None

    def get_video_duration_seconds(self, video_path: str) -> Optional[float]:
        """Retourne la durée (en secondes) via ffprobe."""
        try:
            args = [
                self.ffprobe, '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            output = self.run_command(args).decode('utf-8').strip()
            if not output:
                return None
                
            duration = float(output)
            return duration if duration > 0 else None
        except Exception:
            return None
