#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Widget carte pour RedCAM.
Affiche la trace GPS et les marqueurs vidéo via folium.
Gère les interactions (clic sur marqueur) pour lancer les vidéos.
"""

import os
import json
import math
import tempfile
from typing import Optional, List
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QDialog, QFormLayout, QLineEdit, 
    QComboBox, QDialogButtonBox, QPushButton, QColorDialog, QLabel, QHBoxLayout
)
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl, QTimer, pyqtSignal, Qt
from PyQt6.QtGui import QColor

import folium

from redcam.domain.gps_types import GPSTrack, VideoLocation, LocationSource
from ..theme.styles import GROUPBOX_STYLE


class EditVideoDialog(QDialog):
    """Dialogue pour éditer les propriétés d'une vidéo (Nom, Couleur, Icône)."""
    def __init__(self, video: VideoLocation, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Propriétés de la vidéo")
        self.resize(400, 250)
        self.video = video
        self.selected_color = video.marker_color
        
        layout = QFormLayout(self)
        
        # Nom
        self.name_edit = QLineEdit(video.custom_name or video.video_name)
        layout.addRow("Nom:", self.name_edit)
        
        # Couleur
        self.color_btn = QPushButton()
        self.color_btn.setStyleSheet(f"background-color: {self.selected_color}; border: none; height: 24px;")
        self.color_btn.clicked.connect(self._pick_color)
        layout.addRow("Couleur:", self.color_btn)
        
        # Icône (Forme)
        self.icon_combo = QComboBox()
        self.icon_combo.addItems(["circle", "square", "triangle", "star"])
        self.icon_combo.setCurrentText(video.marker_icon)
        layout.addRow("Forme:", self.icon_combo)

        # Note
        self.note_edit = QLineEdit(video.custom_note or "")
        self.note_edit.setPlaceholderText("Note affichée sur la carte...")
        layout.addRow("Note:", self.note_edit)
        
        # Boutons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
        # Style
        self.setStyleSheet("""
            QDialog { background: #252525; color: #e0e0e0; }
            QLabel { color: #e0e0e0; font-weight: bold; }
            QLineEdit, QComboBox { 
                background: #1e1e1e; color: #e0e0e0; border: 1px solid #3a3a3a; padding: 6px;
            }
            QPushButton { border-radius: 4px; }
        """)

    def _pick_color(self):
        color = QColorDialog.getColor(QColor(self.selected_color), self, "Choisir une couleur")
        if color.isValid():
            self.selected_color = color.name()
            self.color_btn.setStyleSheet(f"background-color: {self.selected_color}; border: none; height: 24px;")

    def get_data(self):
        return {
            'custom_name': self.name_edit.text(),
            'custom_note': self.note_edit.text(),
            'marker_color': self.selected_color,
            'marker_icon': self.icon_combo.currentText()
        }


class ConsoleInterceptor(QWebEnginePage):
    """Intercepte les messages console JS pour la communication."""
    
    def __init__(self, parent_widget):
        super().__init__(parent_widget)
        self.parent_widget = parent_widget
        
    def javaScriptConsoleMessage(self, level, message, line, source_id):
        # Interception du clic vidéo
        if message.startswith("VIDEO:"):
            video_path = message[6:]
            self.parent_widget.video_clicked.emit(video_path)
            return
        
        # Interception de l'édition
        if message.startswith("EDIT:"):
            video_path = message[5:]
            self.parent_widget.open_edit_dialog(video_path)
            return
            
        super().javaScriptConsoleMessage(level, message, line, source_id)


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
        html = self._generate_map_html()
        self._display_html(html)
    
    def display_track(
        self, 
        track: GPSTrack, 
        video_locations: Optional[List[VideoLocation]] = None
    ) -> None:
        """Affiche la trace GPS et les marqueurs sur la carte."""
        self.current_track = track
        self.current_videos = video_locations
        
        html = self._generate_map_html(track, video_locations)
        self._display_html(html)
    
    def display_videos_only(self, videos: List[VideoLocation]) -> None:
        """Affiche uniquement les marqueurs vidéo sans trace."""
        if not videos:
            return
            
        dummy_track = GPSTrack(name="dummy", points=[])
        html = self._generate_map_html(dummy_track, videos)
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

    def _haversine(self, lat1, lon1, lat2, lon2):
        """Calcule la distance en km entre deux points."""
        R = 6371  # Rayon de la Terre en km
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def _generate_map_html(
        self, 
        track: Optional[GPSTrack] = None,
        videos: Optional[List[VideoLocation]] = None
    ) -> str:
        """Crée le code HTML complet de la carte (Dark Mode)."""
        
        center_lat = 46.603354
        center_lon = 1.888334
        zoom = 6
        
        points = []
        if track and not track.is_empty():
            points = [(p.latitude, p.longitude) for p in track.points if p.latitude and p.longitude]
            if points:
                center_lat = points[0][0]
                center_lon = points[0][1]
                zoom = 13
        elif videos:
             for v in videos:
                 if v.is_located():
                     center_lat = v.position.latitude
                     center_lon = v.position.longitude
                     zoom = 13
                     break

        html_head = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin=""/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>
    <style>
        html, body {{ width: 100%; height: 100%; margin: 0; padding: 0; background: #1e1e1e; }}
        #map {{ width: 100%; height: 100%; background: #1e1e1e; }}
        .runner-icon {{ transition: all 0.1s linear; }}
        .leaflet-popup-content-wrapper, .leaflet-popup-tip {{
            background: #252525;
            color: #E0E0E0;
            box-shadow: 0 3px 14px rgba(0,0,0,0.4);
        }}
        .leaflet-container a.leaflet-popup-close-button {{
            color: #E0E0E0;
        }}
        /* Tooltip personnalisé pour les notes */
        .note-tooltip {{
            background-color: rgba(30, 30, 30, 0.9);
            border: 1px solid #444;
            color: #fff;
            font-family: "Segoe UI", sans-serif;
            font-size: 12px;
            padding: 4px 8px;
            border-radius: 4px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.5);
        }}
        .note-tooltip::before {{
            border-right-color: rgba(30, 30, 30, 0.9);
        }}
        /* Styles pour les formes personnalisées */
        .custom-marker {{
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        .marker-shape {{
            width: 100%;
            height: 100%;
            box-sizing: border-box;
            transition: all 0.2s ease;
        }}
        .marker-circle {{
            border-radius: 50%;
            border: 2px solid #121212;
        }}
        .marker-square {{
            border-radius: 2px;
            border: 2px solid #121212;
        }}
        .marker-triangle {{
            width: 0;
            height: 0;
            border-left: 7px solid transparent;
            border-right: 7px solid transparent;
            border-bottom: 14px solid; /* Color set inline */
            background: transparent !important;
        }}
        .marker-star {{
            clip-path: polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%);
            border: none;
        }}
        
        /* Effet Glow pour la sélection */
        .marker-selected .marker-shape {{
            box-shadow: 0 0 15px 4px rgba(255, 255, 255, 0.8);
            border-color: white;
            transform: scale(1.2);
            z-index: 1000;
        }}
        /* Glow spécifique pour triangle et étoile (pas de box-shadow simple) */
        .marker-selected .marker-triangle, .marker-selected .marker-star {{
            box-shadow: none;
            filter: drop-shadow(0 0 8px rgba(255, 255, 255, 0.8));
            transform: scale(1.2);
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        var map = L.map('map', {{
            zoomControl: false,
            attributionControl: false
        }}).setView([{center_lat}, {center_lon}], {zoom});
        
        L.control.zoom({{
            position: 'bottomright'
        }}).addTo(map);

        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 20
        }}).addTo(map);
'''
        
        coords_json = json.dumps(points)
        
        html_body = ""
        
        if points:
            html_body += f'''
        var latlngs = {coords_json};
        // Trace en Cyan technique
        var polyline = L.polyline(latlngs, {{color: '#00E5FF', weight: 3, opacity: 0.8}}).addTo(map);
        map.fitBounds(polyline.getBounds());
        
        // Marqueurs début/fin stylisés
        var startIcon = L.divIcon({{
            className: 'custom-div-icon',
            html: "<div style='background-color:#4CAF50;width:10px;height:10px;border-radius:50%;border:2px solid white;'></div>",
            iconSize: [14, 14],
            iconAnchor: [7, 7]
        }});
        var endIcon = L.divIcon({{
            className: 'custom-div-icon',
            html: "<div style='background-color:#F44336;width:10px;height:10px;border-radius:50%;border:2px solid white;'></div>",
            iconSize: [14, 14],
            iconAnchor: [7, 7]
        }});

        L.marker(latlngs[0], {{icon: startIcon}}).addTo(map).bindPopup("Départ");
        L.marker(latlngs[latlngs.length - 1], {{icon: endIcon}}).addTo(map).bindPopup("Arrivée");
'''

        # Calculer les distances cumulées de la trace pour le KM
        track_distances = [] # List of (timestamp, distance_km)
        if track and not track.is_empty():
            total_dist = 0.0
            prev_p = None
            for p in track.points:
                if not p.is_valid(): continue
                if prev_p:
                    dist = self._haversine(prev_p.latitude, prev_p.longitude, p.latitude, p.longitude)
                    total_dist += dist
                track_distances.append((p.timestamp, total_dist))
                prev_p = p

        # Ajouter les marqueurs vidéo
        if videos:
            html_body += "var videoMarkers = {};\n"
            for v in videos:
                if v.is_located() and v.position:
                    # Couleurs et icônes personnalisées
                    color = v.marker_color if hasattr(v, 'marker_color') else ("#2a4d69" if v.source.value == "GPS intégré" else "#4caf50")
                    shape = v.marker_icon if hasattr(v, 'marker_icon') else "circle"
                    name = v.custom_name if hasattr(v, 'custom_name') and v.custom_name else v.video_name
                    
                    safe_path = v.video_path.replace('\\', '/')
                    
                    # Calculer KM et Heure
                    video_time_str = ""
                    video_km_str = ""
                    
                    if v.creation_time:
                        video_time_str = v.creation_time.strftime("%H:%M:%S")
                        # Trouver la distance la plus proche
                        closest_dist = 0.0
                        min_diff = float('inf')
                        # Recherche simple (optimisable)
                        for t, d in track_distances:
                            if t and v.creation_time:
                                diff = abs((t - v.creation_time).total_seconds())
                                if diff < min_diff:
                                    min_diff = diff
                                    closest_dist = d
                        
                        # Si on a trouvé une correspondance proche (< 5 min)
                        if min_diff < 300:
                            video_km_str = f"{closest_dist:.2f} km"
                    
                    # Style DaVinci pour le popup
                    popup_content = f"""
                        <div style='font-family: "Segoe UI", sans-serif; min-width: 180px;'>
                            <div style='border-bottom: 1px solid #444; padding-bottom: 6px; margin-bottom: 8px;'>
                                <b style='color: #fff; font-size: 14px;'>{name}</b>
                            </div>
                            <div style='color: #aaa; font-size: 11px; margin-bottom: 10px;'>
                                {v.source.value}<br/>
                                {v.position.latitude:.5f}, {v.position.longitude:.5f}<br/>
                                <span style='color: #00E5FF;'>{video_time_str}</span> • <span style='color: #4CAF50;'>{video_km_str}</span>
                            </div>
                            <div style='display: flex; gap: 8px;'>
                                <button onclick='console.log("VIDEO:{safe_path}")' style='flex: 1; background: #2a4d69; color: white; border: none; padding: 6px 10px; border-radius: 2px; cursor: pointer; font-weight: 600; font-size: 11px;'>▶ LIRE</button>
                                <button onclick='console.log("EDIT:{safe_path}")' style='flex: 1; background: #333; color: #ddd; border: 1px solid #555; padding: 6px 10px; border-radius: 2px; cursor: pointer; font-weight: 600; font-size: 11px;'>✎ ÉDITER</button>
                            </div>
                        </div>
                    """.replace('\n', '').replace('"', '\\"')
                    
                    # Forme du marqueur via DivIcon
                    icon_html = ""
                    icon_class = ""
                    icon_size = [14, 14]
                    anchor = [7, 7]
                    
                    if shape == "square":
                        icon_class = "marker-square"
                        icon_html = f"<div class='marker-shape marker-square' style='background-color: {color};'></div>"
                    elif shape == "triangle":
                        icon_class = "marker-triangle"
                        # Triangle uses border hack, color is border-bottom-color
                        icon_html = f"<div class='marker-shape marker-triangle' style='border-bottom-color: {color};'></div>"
                        icon_size = [14, 14]
                    elif shape == "star":
                        icon_class = "marker-star"
                        icon_html = f"<div class='marker-shape marker-star' style='background-color: {color};'></div>"
                        icon_size = [16, 16]
                        anchor = [8, 8]
                    else: # circle default
                        icon_class = "marker-circle"
                        icon_html = f"<div class='marker-shape marker-circle' style='background-color: {color};'></div>"

                    html_body += f'''
        var myIcon = L.divIcon({{
            className: 'custom-marker',
            html: "{icon_html}",
            iconSize: {icon_size},
            iconAnchor: {anchor}
        }});

        var marker = L.marker([{v.position.latitude}, {v.position.longitude}], {{
            icon: myIcon
        }}).addTo(map).bindPopup("{popup_content}");
        
        // Enregistrer le marqueur avec le chemin comme clé
        videoMarkers["{safe_path}"] = marker;
        
        // Ajouter une note si présente
        var note = "{v.custom_note if hasattr(v, 'custom_note') and v.custom_note else ''}";
        if (note) {{
            marker.bindTooltip(note, {{
                permanent: true, 
                direction: 'right',
                className: 'note-tooltip',
                offset: [10, 0]
            }});
        }}
        
        // Clic direct sur le marqueur
        marker.on('click', function() {{
            console.log("VIDEO:{safe_path}");
        }});
'''

        html_end = '''
        // Marqueur coureur (Flèche directionnelle)
        // On utilise un SVG rotatif pour la direction si disponible, sinon un point brillant
        var runnerIcon = L.divIcon({
            className: 'runner-icon',
            html: '<div style="background-color: #2a4d69; width: 14px; height: 14px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 10px rgba(42, 77, 105, 0.9);"></div>',
            iconSize: [18, 18],
            iconAnchor: [9, 9]
        });
        var runnerMarker = L.marker([0, 0], {icon: runnerIcon, zIndexOffset: 1000});
        
        function updateRunner(lat, lon) {
            if (!map.hasLayer(runnerMarker)) {
                runnerMarker.addTo(map);
            }
            runnerMarker.setLatLng([lat, lon]);
        }
        
        // Fonction pour sélectionner/highlighter une vidéo
        var currentSelectionMarker = null;
        function selectVideo(path) {
            // Reset précédent
            if (currentSelectionMarker) {
                var el = currentSelectionMarker.getElement();
                if (el) {
                    L.DomUtil.removeClass(el, 'marker-selected');
                }
            }
            
            var marker = videoMarkers[path];
            if (marker) {
                var el = marker.getElement();
                if (el) {
                    L.DomUtil.addClass(el, 'marker-selected');
                }
                marker.openPopup();
                map.panTo(marker.getLatLng());
                currentSelectionMarker = marker;
            }
        }

        // Légende Dark Mode
        var legend = L.control({position: 'bottomleft'});
        legend.onAdd = function (map) {
            var div = L.DomUtil.create('div', 'info legend');
            div.style.backgroundColor = 'rgba(30, 30, 30, 0.9)';
            div.style.color = '#eee';
            div.style.padding = '10px';
            div.style.borderRadius = '4px';
            div.style.fontSize = '11px';
            div.style.border = '1px solid #444';
            div.style.fontFamily = '"Segoe UI", sans-serif';
            
            div.innerHTML += '<div style="margin-bottom:4px"><i style="background: #2a4d69; border-radius: 50%; display: inline-block; width: 8px; height: 8px; margin-right: 8px;"></i> GPS Intégré</div>';
            div.innerHTML += '<div style="margin-bottom:4px"><i style="background: #4caf50; border-radius: 50%; display: inline-block; width: 8px; height: 8px; margin-right: 8px;"></i> Synchro .fit</div>';
            div.innerHTML += '<div><i style="background: #00E5FF; display: inline-block; width: 12px; height: 2px; margin-right: 6px; vertical-align: middle;"></i> Trace GPS</div>';
            return div;
        };
        legend.addTo(map);
    </script>
</body>
</html>'''

        return html_head + html_body + html_end
    
    def update_current_position(self, timestamp) -> None:
        """
        Met à jour la position du coureur sur la carte.
        
        Args:
            timestamp: Timestamp (datetime ou int/float timestamp)
        """
        if not self.current_track or self.current_track.is_empty():
            return
            
        # Trouver la position approximative
        # timestamp peut être un datetime ou un float (selon ce que TimelineWidget émet)
        # Supposons datetime pour l'instant car TimelineWidget émet self.time_changed(datetime)
        
        # Trouver le point le plus proche (ou interpoler)
        # Optimisation possible: utiliser bisect, mais pour <10k points une boucle simple ou min() suffit
        
        # TODO: Implémenter interpolation pour fluidité
        # Pour l'instant: point le plus proche
        
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
                # Si la différence augmente, on s'éloigne (suppose points triés)
                # Mais attention aux trous, donc on continue un peu ou on break si vraiment grand
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
