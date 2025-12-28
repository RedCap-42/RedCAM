#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Widget carte pour RedCAM.
Affiche la trace GPS et les marqueurs vidéo via folium.
Gère les interactions (clic sur marqueur) pour lancer les vidéos.
"""

from typing import Optional, List

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl, QTimer, pyqtSignal

from redcam.domain.gps_types import GPSTrack, VideoLocation
from redcam.ui.dialogs.edit_video_dialog import EditVideoDialog
from redcam.ui.widgets.map.console_interceptor import ConsoleInterceptor
from redcam.ui.widgets.map.map_html_generator import MapHTMLGenerator


class MapWidget(QWidget):
    """
    Widget affichant une carte interactive avec trace GPS et marqueurs.
    Permet de cliquer sur un marqueur pour jouer la vidéo.
    """
    
    # Signal émis quand un marqueur vidéo est cliqué
    video_clicked = pyqtSignal(str)  # Chemin du fichier vidéo
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialise le widget carte."""
        super().__init__(parent)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # WebView pour afficher la carte
        self.web_view = QWebEngineView()
        
        # Installer l'intercepteur
        self.page = ConsoleInterceptor(self)
        self.web_view.setPage(self.page)
        
        # Configurer pour permettre le chargement de ressources
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        
        layout.addWidget(self.web_view)
        
        # Map cache
        self.current_track = None
        self.current_videos = None
        
        # Afficher une carte vide après initialisation
        self.web_view.setHtml("<html><body style='background-color: #222; color: white; display: flex; justify-content: center; align-items: center; height: 100%; margin: 0; font-family: sans-serif;'><h1>Chargement de la carte...</h1></body></html>")
        QTimer.singleShot(500, self.display_initial_map)
        
    def display_initial_map(self) -> None:
        """Affiche une carte vide initiale."""
        html = MapHTMLGenerator.generate()
        self._display_html(html)
    
    def display_track(
        self, 
        track: GPSTrack, 
        video_locations: Optional[List[VideoLocation]] = None
    ) -> None:
        """Affiche la trace GPS et les marqueurs sur la carte."""
        self.current_track = track
        self.current_videos = video_locations
        
        html = MapHTMLGenerator.generate(track, video_locations)
        self._display_html(html)
    
    def display_videos_only(self, videos: List[VideoLocation]) -> None:
        """Affiche uniquement les marqueurs vidéo sans trace."""
        if not videos:
            return
            
        dummy_track = GPSTrack(name="dummy", points=[])
        html = MapHTMLGenerator.generate(dummy_track, videos)
        self._display_html(html)

    def open_edit_dialog(self, video_path: str):
        """Ouvre le dialogue d'édition pour une vidéo."""
        if not self.current_videos:
            return
            
        # Trouver la vidéo
        video = next((v for v in self.current_videos if v.video_path.replace('\\', '/') == video_path), None)
        if not video:
            return
            
        dialog = EditVideoDialog(video, self)
        if dialog.exec():
            data = dialog.get_data()
            video.custom_name = data['custom_name']
            video.custom_note = data['custom_note']
            video.marker_color = data['marker_color']
            video.marker_icon = data['marker_icon']
            
            # Rafraîchir la carte
            self.display_track(self.current_track, self.current_videos)

    def update_cursor(self, time_ratio: float) -> None:
        """
        Met à jour la position du curseur sur la trace.
        
        Args:
            time_ratio: Ratio temporel (0.0 à 1.0)
        """
        if not self.current_track:
            return
            
        # TODO: Implémenter le curseur dynamique via JavaScript
        # self.web_view.page().runJavaScript(f"updateCursor({time_ratio});")
        pass

    def update_current_position(self, timestamp) -> None:
        """
        Met à jour la position du coureur sur la carte.
        
        Args:
            timestamp: Timestamp (datetime ou int/float timestamp)
        """
        if not self.current_track or self.current_track.is_empty():
            return
            
        # Trouver le point le plus proche
        closest_point = None
        min_diff = float('inf')
        
        for p in self.current_track.points:
            if not p.timestamp:
                continue
            
            diff = abs((p.timestamp - timestamp).total_seconds())
            if diff < min_diff:
                min_diff = diff
                closest_point = p
            else:
                if diff > 300: # 5 min
                    break
                    
        if closest_point:
            self.web_view.page().runJavaScript(
                f"updateRunner({closest_point.latitude}, {closest_point.longitude});"
            )
            
    def select_video(self, video_path: str) -> None:
        """Sélectionne visuellement une vidéo sur la carte."""
        safe_path = video_path.replace('\\', '/')
        self.web_view.page().runJavaScript(f"selectVideo('{safe_path}');")

    def _display_html(self, html: str) -> None:
        """Affiche le HTML."""
        try:
            self.web_view.setHtml(html, QUrl("https://raw.githubusercontent.com/"))
        except Exception as e:
            print(f"Erreur affichage carte: {e}")
            
    def cleanup(self) -> None:
        pass
