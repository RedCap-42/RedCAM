#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Définition du style de l'overlay.
"""

from dataclasses import dataclass, field
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt

@dataclass
class OverlayStyle:
    """
    Paramètres de style pour l'overlay.
    """
    # Trace parcourue (Done)
    trace_color_done: QColor = field(default_factory=lambda: QColor("#E09F3E"))  # Orange/Jaune
    trace_width: int = 4
    
    # Trace restante (Remaining)
    trace_color_remaining: QColor = field(default_factory=lambda: QColor("#505050"))  # Gris foncé
    trace_style_remaining: Qt.PenStyle = Qt.PenStyle.DashLine
    trace_opacity_remaining: float = 0.6
    
    # Marqueur
    marker_color: QColor = field(default_factory=lambda: QColor("#FFFFFF"))
    marker_size: int = 12
    marker_border_color: QColor = field(default_factory=lambda: QColor("#E09F3E"))
    
    # Glow (Lueur)
    glow_enabled: bool = True
    glow_color: QColor = field(default_factory=lambda: QColor("#FFD700"))
    glow_radius: int = 20
    glow_intensity: float = 0.6
    
    # Texte
    text_color: QColor = field(default_factory=lambda: QColor("#FFFFFF"))
    text_font_family: str = "Segoe UI"
    text_font_size: int = 16
    text_bold: bool = True
    extra_text: str = ""
    
    # 3D Transform
    rotation_x: float = 45.0  # Inclinaison
    rotation_z: float = 0.0   # Rotation
    scale: float = 0.8        # Zoom global
    
    def copy(self):
        """Crée une copie profonde (pour les couleurs mutables)."""
        import copy
        return copy.deepcopy(self)
    
    def to_dict(self) -> dict:
        """Sérialise le style en dictionnaire."""
        return {
            'trace_color_done': self.trace_color_done.name(),
            'trace_width': self.trace_width,
            'trace_color_remaining': self.trace_color_remaining.name(),
            'trace_style_remaining': int(self.trace_style_remaining),
            'trace_opacity_remaining': self.trace_opacity_remaining,
            'marker_color': self.marker_color.name(),
            'marker_size': self.marker_size,
            'marker_border_color': self.marker_border_color.name(),
            'glow_enabled': self.glow_enabled,
            'glow_color': self.glow_color.name(),
            'glow_radius': self.glow_radius,
            'glow_intensity': self.glow_intensity,
            'text_color': self.text_color.name(),
            'text_font_family': self.text_font_family,
            'text_font_size': self.text_font_size,
            'text_bold': self.text_bold,
            'extra_text': self.extra_text,
            'rotation_x': self.rotation_x,
            'rotation_z': self.rotation_z,
            'scale': self.scale
        }

    @staticmethod
    def from_dict(data: dict) -> 'OverlayStyle':
        """Crée un style depuis un dictionnaire."""
        style = OverlayStyle()
        if 'trace_color_done' in data:
            style.trace_color_done = QColor(data['trace_color_done'])
        if 'trace_width' in data:
            style.trace_width = data['trace_width']
        if 'trace_color_remaining' in data:
            style.trace_color_remaining = QColor(data['trace_color_remaining'])
        if 'trace_style_remaining' in data:
            style.trace_style_remaining = Qt.PenStyle(data['trace_style_remaining'])
        if 'trace_opacity_remaining' in data:
            style.trace_opacity_remaining = data['trace_opacity_remaining']
        if 'marker_color' in data:
            style.marker_color = QColor(data['marker_color'])
        if 'marker_size' in data:
            style.marker_size = data['marker_size']
        if 'marker_border_color' in data:
            style.marker_border_color = QColor(data['marker_border_color'])
        if 'glow_enabled' in data:
            style.glow_enabled = data['glow_enabled']
        if 'glow_color' in data:
            style.glow_color = QColor(data['glow_color'])
        if 'glow_radius' in data:
            style.glow_radius = data['glow_radius']
        if 'glow_intensity' in data:
            style.glow_intensity = data['glow_intensity']
        if 'text_color' in data:
            style.text_color = QColor(data['text_color'])
        if 'text_font_family' in data:
            style.text_font_family = data['text_font_family']
        if 'text_font_size' in data:
            style.text_font_size = data['text_font_size']
        if 'text_bold' in data:
            style.text_bold = data['text_bold']
        if 'extra_text' in data:
            style.extra_text = data['extra_text']
        if 'rotation_x' in data:
            style.rotation_x = data['rotation_x']
        if 'rotation_z' in data:
            style.rotation_z = data['rotation_z']
        if 'scale' in data:
            style.scale = data['scale']
        return style
