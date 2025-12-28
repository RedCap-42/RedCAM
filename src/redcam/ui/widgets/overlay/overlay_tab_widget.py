#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Widget principal de l'onglet Overlay - Version production.
Intègre la grille, la prévisualisation et les réglages style DaVinci.
"""

from typing import Optional, List

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter, QLabel,
    QSplitterHandle
)
from PyQt6.QtCore import Qt, pyqtSignal

from redcam.domain.gps_types import GPSTrack, VideoLocation
from .video_grid_widget import VideoGridWidget
from .overlay_preview_widget import OverlayPreviewWidget
from .overlay_renderer import OverlayRenderer
from .overlay_settings_widget import OverlaySettingsWidget
from .overlay_style import OverlayStyle


class OverlayTabWidget(QWidget):
    """
    Widget principal de l'onglet Overlay.
    
    Layout:
    [ GRID (Left) ] | [ PREVIEW (Center) ] | [ SETTINGS (Right) ]
    """
    overlay_exported = pyqtSignal(str)
    presets_updated = pyqtSignal(dict)
    
    def __init__(self, presets: dict = None, parent=None):
        super().__init__(parent)
        
        self.track: Optional[GPSTrack] = None
        self.videos: List[VideoLocation] = []
        self.selected_video: Optional[VideoLocation] = None
        self.presets = presets or {}
        
        self.renderer = OverlayRenderer()
        self.style = OverlayStyle()
        
        self._init_ui()
    
    def _init_ui(self):
        self.setStyleSheet("background-color: #141414;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Splitter principal
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #0a0a0a;
                width: 1px;
            }
        """)
        splitter.setHandleWidth(1)
        
        # --- LEFT PANEL: Video Grid ---
        left_panel = QWidget()
        left_panel.setStyleSheet("background-color: #141414;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        left_layout.addWidget(self._create_header("  VIDÉOS"))
        
        self.video_grid = VideoGridWidget()
        self.video_grid.video_selected.connect(self._on_video_selected)
        left_layout.addWidget(self.video_grid)
        
        left_panel.setMinimumWidth(250)
        splitter.addWidget(left_panel)
        
        # --- CENTER PANEL: Preview ---
        center_panel = QWidget()
        center_panel.setStyleSheet("background-color: #141414;")
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        
        center_layout.addWidget(self._create_header("  OVERLAY"))
        
        self.preview = OverlayPreviewWidget()
        self.preview.export_requested.connect(self._on_export_completed)
        self.preview.rotation_changed.connect(self._on_preview_rotation_changed)
        center_layout.addWidget(self.preview)
        
        center_panel.setMinimumWidth(400)
        splitter.addWidget(center_panel)
        
        # --- RIGHT PANEL: Settings ---
        right_panel = QWidget()
        right_panel.setStyleSheet("background-color: #1a1a1a;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        right_layout.addWidget(self._create_header("  RÉGLAGES", bg="#1a1a1a"))
        
        self.settings = OverlaySettingsWidget(self.style, self.presets)
        self.settings.settingsChanged.connect(self._on_settings_changed)
        self.settings.presetSaveRequested.connect(self._on_preset_saved)
        self.settings.presetDeleteRequested.connect(self._on_preset_deleted)
        right_layout.addWidget(self.settings)
        
        right_panel.setMinimumWidth(280)
        right_panel.setMaximumWidth(350)
        splitter.addWidget(right_panel)
        
        # Initial sizes
        splitter.setSizes([300, 700, 300])
        
        layout.addWidget(splitter)
        
        # Placeholder screen (shown when no data)
        self.placeholder = QLabel("Chargez un fichier .fit et synchronisez les vidéos")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setStyleSheet("""
            QLabel {
                color: #404040;
                font-size: 13px;
                background-color: #141414;
            }
        """)
        layout.addWidget(self.placeholder)
        
        self._update_visibility()
    
    def _create_header(self, text, bg="#1a1a1a"):
        header = QLabel(text)
        header.setFixedHeight(28)
        header.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: #505050;
                font-weight: 600;
                font-size: 10px;
                letter-spacing: 0.5px;
                border-bottom: 1px solid #0a0a0a;
            }}
        """)
        return header
    
    def set_data(self, track: Optional[GPSTrack], videos: List[VideoLocation]):
        self.track = track
        self.videos = videos
        
        self.video_grid.set_videos(videos)
        self.preview.clear()
        
        self._update_visibility()
    
    def _update_visibility(self):
        has_data = self.track is not None and len(self.videos) > 0
        
        # Toggle placeholder vs splitter
        layout_item0 = self.layout().itemAt(0) # Splitter
        layout_item1 = self.layout().itemAt(1) # Placeholder
        
        if layout_item0 and layout_item0.widget():
            layout_item0.widget().setVisible(has_data)
        
        if layout_item1 and layout_item1.widget():
            layout_item1.widget().setVisible(not has_data)
    
    def _on_video_selected(self, video: VideoLocation):
        self.selected_video = video
        self._redraw_overlay()
    
    def _on_settings_changed(self, new_style: OverlayStyle):
        self.style = new_style
        
        # Mettre à jour la rotation dans la preview pour qu'elle reste sync
        self.preview.set_current_rotation(self.style.rotation_x, self.style.rotation_z)
        
        self._redraw_overlay()
    
    def _on_preview_rotation_changed(self, rot_x, rot_z):
        """Mise à jour depuis la souris dans la preview."""
        # Mise à jour des sliders (sans émettre de signal pour éviter boucle)
        self.settings.update_rotation(rot_x, rot_z)
        
        # Mettre à jour le style directement
        self.style.rotation_x = rot_x
        self.style.rotation_z = rot_z
        
        # Redessiner immédiatement
        self._redraw_overlay()
    
    def _redraw_overlay(self):
        if not self.track or not self.selected_video or not self.selected_video.position:
            return
        
        # Rendu avec le style actuel
        image = self.renderer.render(self.track, self.selected_video, self.style)
        
        # Calcul distance
        distance_km = self.renderer._calculate_distance_km(self.track, self.selected_video)
        
        self.preview.set_overlay(image, distance_km)
    
    
    def _on_export_completed(self, path: str):
        self.overlay_exported.emit(path)

    def _on_preset_saved(self, name: str, style: OverlayStyle):
        """Met à jour les presets locaux et notifie le parent."""
        self.presets[name] = style.to_dict()
        self.presets_updated.emit(self.presets)
        
    def _on_preset_deleted(self, name: str):
        """Supprime un preset et notifie."""
        if name in self.presets:
            del self.presets[name]
            self.presets_updated.emit(self.presets)
    
    def cleanup(self):
        self.video_grid.cleanup()
