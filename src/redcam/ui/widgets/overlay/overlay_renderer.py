#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Renderer amélioré pour overlays PNG avec style personnalisable et 3D.
"""

from typing import Optional, List, Tuple
from datetime import datetime
import math

from PyQt6.QtGui import (
    QPainter, QImage, QColor, QPen, QBrush, QFont,
    QPainterPath, QRadialGradient
)
from PyQt6.QtCore import Qt, QPointF

from redcam.domain.gps_types import GPSTrack, GPSPoint, VideoLocation
from .overlay_style import OverlayStyle


class OverlayRenderer:
    """
    Génère des overlays avec support de la personnalisation avancée.
    Supporte la transformation pseudo-3D via OverlayStyle.
    """
    
    def __init__(self, width: int = 1920, height: int = 1080, padding: int = 100):
        self.width = width
        self.height = height
        self.padding = padding
    
    def render(
        self,
        track: GPSTrack,
        video_location: Optional[VideoLocation] = None,
        style: Optional[OverlayStyle] = None
    ) -> QImage:
        """Génère l'image overlay selon le style fourni."""
        if not style:
            style = OverlayStyle()
            
        image = QImage(self.width, self.height, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        
        if track.is_empty():
            painter.end()
            return image
        
        valid_points = [p for p in track.points if p.is_valid()]
        if not valid_points:
            painter.end()
            return image
        
        # 1. Normalisation et projection 3D
        projected_points = self._project_points_3d(valid_points, style)
        
        if not projected_points:
            painter.end()
            return image
            
        # 2. Trouver l'index du point vidéo
        video_idx = None
        if video_location and video_location.position:
            video_idx = self._find_closest_point_index(valid_points, video_location.position)
            
        # 3. Dessiner la trace
        self._draw_trace(painter, projected_points, video_idx, style)
        
        # 4. Dessiner le marqueur et le texte
        if video_location and video_idx is not None:
             # Récupérer la position projetée du point vidéo
            if 0 <= video_idx < len(projected_points):
                marker_pos = projected_points[video_idx]
                distance_km = self._calculate_distance_km(track, video_location)
                self._draw_marker(painter, marker_pos, distance_km, style)
        
        painter.end()
        return image
    
    def _project_points_3d(self, points: List[GPSPoint], style: OverlayStyle) -> List[QPointF]:
        """Convertit les points GPS en pixels avec rotation 3D."""
        if not points:
            return []
            
        lats = [p.latitude for p in points]
        lons = [p.longitude for p in points]
        
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        
        lat_range = max(0.0001, max_lat - min_lat)
        lon_range = max(0.0001, max_lon - min_lon)
        
        center_lat = (min_lat + max_lat) / 2
        center_lon = (min_lon + max_lon) / 2
        
        # Facteur d'échelle global (adaptation à la taille écran)
        scale_gps = min(
            (self.width - 2 * self.padding) / lon_range,
            (self.height - 2 * self.padding) / lat_range
        ) * style.scale
        
        res_points = []
        
        # Matrices de rotation
        rad_x = math.radians(style.rotation_x)
        rad_z = math.radians(style.rotation_z)
        
        cos_x, sin_x = math.cos(rad_x), math.sin(rad_x)
        cos_z, sin_z = math.cos(rad_z), math.sin(rad_z)
        
        center_x = self.width / 2
        center_y = self.height / 2
        
        for p in points:
            # 1. Centrer et normaliser autour de 0,0
            # Note: Y inversé pour le GPS
            x0 = (p.longitude - center_lon) * scale_gps
            y0 = -(p.latitude - center_lat) * scale_gps
            z0 = 0.0
            
            # 2. Rotation Z (Yaw)
            x1 = x0 * cos_z - y0 * sin_z
            y1 = x0 * sin_z + y0 * cos_z
            z1 = z0
            
            # 3. Rotation X (Pitch) - simule la perspective
            # On bascule le plan XY pour créer de la profondeur
            y2 = y1 * cos_x
            z2 = y1 * sin_x
            x2 = x1
            
            # 4. Projection perspective simple
            # Plus z2 est grand (loin), plus on réduit l'échelle, mais ici on projette orthogonalement
            # avec un léger facteur de perspective si voulu.
            # Pour simplifier et éviter les déformations extrêmes, on fait une projection iso avec foreshortening
            
            # Mapping final écran
            screen_x = center_x + x2
            screen_y = center_y + y2
            
            res_points.append(QPointF(screen_x, screen_y))
            
        return res_points
        
    def _draw_trace(
        self, 
        painter: QPainter, 
        points: List[QPointF], 
        video_idx: Optional[int], 
        style: OverlayStyle
    ):
        """Dessine les segments 'fait' et 'restant'."""
        if not points:
            return
            
        # Chemin complet si pas de vidéo, sinon split
        if video_idx is None:
             self._draw_path(painter, points, style.trace_color_done, style.trace_width, Qt.PenStyle.SolidLine)
             return
             
        # Done Path (0 -> video_idx)
        done_points = points[:video_idx + 1]
        if len(done_points) > 1:
            self._draw_path(painter, done_points, style.trace_color_done, style.trace_width, Qt.PenStyle.SolidLine)
            
        # Remaining Path (video_idx -> end)
        rem_points = points[video_idx:]
        if len(rem_points) > 1:
             # Appliquer opacité pour le remaining
             color = QColor(style.trace_color_remaining)
             color.setAlphaF(style.trace_opacity_remaining)
             self._draw_path(painter, rem_points, color, style.trace_width, style.trace_style_remaining)

    def _draw_path(self, painter: QPainter, points: List[QPointF], color: QColor, width: int, pen_style: Qt.PenStyle):
        if len(points) < 2:
            return
            
        path = QPainterPath()
        path.moveTo(points[0])
        for p in points[1:]:
            path.lineTo(p)
            
        pen = QPen(color)
        pen.setWidth(width)
        pen.setStyle(pen_style)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        
        painter.setPen(pen)
        painter.drawPath(path)

    def _draw_marker(self, painter: QPainter, pos: QPointF, distance: float, style: OverlayStyle):
        """Dessine le marqueur complet."""
        # 1. Glow
        if style.glow_enabled:
            radius = style.glow_radius
            if radius > 0:
                gradient = QRadialGradient(pos, radius)
                c = QColor(style.glow_color)
                
                c.setAlphaF(style.glow_intensity)
                gradient.setColorAt(0, c)
                
                c.setAlphaF(0.0)
                gradient.setColorAt(1, c)
                
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(gradient))
                painter.drawEllipse(pos, radius, radius)
        
        # 2. Cercle principal
        size = style.marker_size
        rect = QPointF(pos.x() - size/2, pos.y() - size/2)
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(style.marker_color))
        painter.drawEllipse(pos, size/2, size/2)
        
        # 3. Bordure
        pen = QPen(style.marker_border_color)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(pos, size/2, size/2)
        
        # 4. Texte
        self._draw_text(painter, pos, distance, style)
        
    def _draw_text(self, painter: QPainter, pos: QPointF, distance: float, style: OverlayStyle):
        text = f"{distance:.1f} km"
        if style.extra_text:
            text += f" - {style.extra_text}"
            
        font = QFont(style.text_font_family, style.text_font_size)
        font.setBold(style.text_bold)
        painter.setFont(font)
        
        # Position décalée
        offset_x = style.marker_size + 10
        offset_y = style.text_font_size / 3
        text_pos = pos + QPointF(offset_x, offset_y)
        
        # Ombre portée
        painter.setPen(QColor(0, 0, 0, 180))
        for d in [1, 2]:
            painter.drawText(text_pos + QPointF(d, d), text)
            
        # Texte principal
        painter.setPen(style.text_color)
        painter.drawText(text_pos, text)

    def _find_closest_point_index(self, points: List[GPSPoint], target: GPSPoint) -> int:
        best_idx = 0
        min_dist = float('inf')
        for i, p in enumerate(points):
            d = (p.latitude - target.latitude)**2 + (p.longitude - target.longitude)**2
            if d < min_dist:
                min_dist = d
                best_idx = i
        return best_idx

    def _calculate_distance_km(self, track: GPSTrack, video_location: VideoLocation) -> float:
        # Same as before... simplified for brevity, assume linear calculation
        # Reuse existing haversine logic if possible or reimplement since we overwrote the class
        
        if not video_location.position or track.is_empty():
            return 0.0
            
        valid_points = [p for p in track.points if p.is_valid()]
        target = video_location.position
        
        # Find index
        idx = self._find_closest_point_index(valid_points, target)
        
        dist = 0.0
        for i in range(1, idx + 1):
             dist += self._haversine_km(valid_points[i-1], valid_points[i])
             
        return dist

    def _haversine_km(self, a: GPSPoint, b: GPSPoint) -> float:
        R = 6371.0 
        lat1 = math.radians(a.latitude)
        lat2 = math.radians(b.latitude)
        dlat = math.radians(b.latitude - a.latitude)
        dlon = math.radians(b.longitude - a.longitude)
        
        h = (math.sin(dlat / 2) ** 2 +
             math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
        
        return 2 * R * math.asin(math.sqrt(h))
