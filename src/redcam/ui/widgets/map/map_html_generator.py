#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import math
from typing import Optional, List
from redcam.domain.gps_types import GPSTrack, VideoLocation, LocationSource

class MapHTMLGenerator:
    """Générateur de code HTML pour la carte Folium/Leaflet."""

    @staticmethod
    def _haversine(lat1, lon1, lat2, lon2):
        """Calcule la distance en km entre deux points."""
        R = 6371  # Rayon de la Terre en km
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    @staticmethod
    def generate(
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
            background: rgba(30, 30, 30, 0.85); /* Glassmorphism base */
            color: #E0E0E0;
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            box-shadow: 0 4px 16px rgba(0,0,0,0.5);
            border: 1px solid rgba(255,255,255,0.1);
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
            border-color: #FFFFFF;
            transform: scale(1.2);
            z-index: 1000;
        }}
        /* Glow spécifique pour triangle et étoile (pas de box-shadow simple) */
        .marker-selected .marker-triangle, .marker-selected .marker-star {{
            box-shadow: none;
            filter: drop-shadow(0 0 8px rgba(255, 255, 255, 0.8));
            transform: scale(1.2);
        }}
        
        /* Style pour la trace sélectionnée (Glow) */
        .selected-track-glow {{
            filter: drop-shadow(0 0 8px rgba(255, 255, 255, 0.8));
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
                    dist = MapHTMLGenerator._haversine(prev_p.latitude, prev_p.longitude, p.latitude, p.longitude)
                    total_dist += dist
                track_distances.append((p.timestamp, total_dist))
                prev_p = p

        # Ajouter les marqueurs vidéo
        if videos:
            html_body += "var videoMarkers = {};\n"
            html_body += "var videoTracks = {};\n"
            html_body += "var currentDottedLine = null;\n"
            
            for v in videos:
                if v.is_located() and v.position:
                    # Couleurs et icônes personnalisées
                    # GPS intégré -> Violet (#9C27B0), Synchro -> Vert (#4caf50)
                    default_color = "#9C27B0" if v.source == LocationSource.EMBEDDED_GPS else "#4caf50"
                    color = v.marker_color if hasattr(v, 'marker_color') and v.marker_color else default_color
                    shape = v.marker_icon if hasattr(v, 'marker_icon') else "circle"
                    name = v.custom_name if hasattr(v, 'custom_name') and v.custom_name else v.video_name
                    
                    safe_path = v.video_path.replace('\\', '/')
                    
                    # Préparer la trace (complet pour sélection, simplifié pour affichage persistant)
                    track_points_json = "[]"
                    if v.track_points and len(v.track_points) > 0:
                        full_coords = [(p.latitude, p.longitude) for p in v.track_points]
                        if len(full_coords) == 1:
                            full_coords.append(full_coords[0])
                        track_points_json = json.dumps(full_coords)
                        html_body += f'videoTracks["{safe_path}"] = {track_points_json};\n'

                        # Simplification pour la ligne grise persistante
                        if len(full_coords) <= 50:
                            display_coords = full_coords
                        else:
                            display_coords = [pt for i, pt in enumerate(full_coords) if i % 5 == 0]
                            if display_coords[-1] != full_coords[-1]:
                                display_coords.append(full_coords[-1])
                        display_json = json.dumps(display_coords)

                        html_body += f'''
        L.polyline({display_json}, {{
            color: '#AAAAAA',
            weight: 3,
            opacity: 0.5,
            lineCap: 'round'
        }}).addTo(map);
'''
                    else:
                        # Pas de track: entrée vide pour éviter undefined côté JS
                        html_body += f'videoTracks["{safe_path}"] = [];' + "\n"
                    
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
            selectVideo("{safe_path}");
        }});
'''
        html_end = '''
        // Marqueur coureur (Flèche directionnelle)
        // On utilise un SVG rotatif pour la direction si disponible, sinon un point brillant
        var runnerIcon = L.divIcon({
            className: 'runner-icon',
            html: '<div style="background-color: #E53935; width: 14px; height: 14px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 15px 3px rgba(229, 57, 53, 0.8);"></div>',
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
        
        // Fonction pour afficher la trace d'une vidéo
        var currentVideoTrack = null;
        function showVideoTrack(path) {
            if (currentVideoTrack) {
                map.removeLayer(currentVideoTrack);
                currentVideoTrack = null;
            }
            
            var points = videoTracks[path];
            if (points && points.length > 0) {
                currentVideoTrack = L.polyline(points, {
                    color: '#FFFFFF',
                    weight: 5,
                    opacity: 0.9,
                    dashArray: '10, 10',
                    className: 'selected-track-glow',
                    lineCap: 'round'
                }).addTo(map);
            }
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
                
                // Afficher aussi la trace
                showVideoTrack(path);
            }
        }

        // Légende supprimée
    </script>
</body>
</html>'''

        return html_head + html_body + html_end
