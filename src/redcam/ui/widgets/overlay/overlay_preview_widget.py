#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Widget de prévisualisation d'overlay - Version production.
Supporte la rotation 3D à la souris (clic molette).
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QSizePolicy, QFrame, QApplication
)
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QMouseEvent, QCursor
from PyQt6.QtCore import Qt, pyqtSignal, QPoint


class OverlayPreviewWidget(QWidget):
    """
    Widget affichant l'overlay généré.
    Gère les interactions souris pour la rotation 3D.
    """
    export_requested = pyqtSignal(str)
    rotation_changed = pyqtSignal(float, float)  # rot_x, rot_z
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_image: Optional[QImage] = None
        self.distance_km: float = 0.0
        
        # État rotation
        self._last_mouse_pos = None
        self._rot_x = 45.0
        self._rot_z = 0.0
        
        self._init_ui()
    
    def _init_ui(self):
        self.setStyleSheet("background-color: #141414;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(12)
        
        # Preview frame
        self.preview_container = QFrame()
        self.preview_container.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border: 1px solid #252525;
                border-radius: 4px;
            }
        """)
        preview_layout = QVBoxLayout(self.preview_container)
        preview_layout.setContentsMargins(1, 1, 1, 1)
        
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(400, 280)
        self.preview_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        self.preview_label.setStyleSheet("background: transparent; border: none;")
        self.preview_label.setMouseTracking(True)
        preview_layout.addWidget(self.preview_label)
        
        layout.addWidget(self.preview_container, 1)
        
        # Bottom bar
        bottom_bar = QWidget()
        bottom_bar.setFixedHeight(36)
        bottom_bar.setStyleSheet("background-color: transparent;")
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(12)
        
        # Hint info
        self.hint_label = QLabel("💡 Clic molette + glisser pour orienter la carte")
        self.hint_label.setStyleSheet("color: #606060; font-size: 10px; font-style: italic;")
        bottom_layout.addWidget(self.hint_label)
        
        # Distance label
        self.distance_label = QLabel("Distance: --")
        self.distance_label.setStyleSheet("""
            QLabel {
                color: #e08040;
                font-size: 12px;
                font-weight: 600;
                background: transparent;
            }
        """)
        bottom_layout.addWidget(self.distance_label)
        
        bottom_layout.addStretch()
        
        # Export button
        self.export_btn = QPushButton("Exporter Overlay (.png)")
        self.export_btn.setFixedHeight(28)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #e04f16;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 16px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #f05f26;
            }
            QPushButton:pressed {
                background-color: #c04010;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #505050;
            }
        """)
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._on_export_clicked)
        bottom_layout.addWidget(self.export_btn)
        
        layout.addWidget(bottom_bar)
        
        # Install event filter for mouse events on label
        self.preview_label.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        if obj == self.preview_label:
            if event.type() == event.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.MiddleButton:
                    self._last_mouse_pos = event.globalPosition()
                    QApplication.setOverrideCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
                    return True
            elif event.type() == event.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.MiddleButton:
                    self._last_mouse_pos = None
                    QApplication.restoreOverrideCursor()
                    return True
            elif event.type() == event.Type.MouseMove:
                if self._last_mouse_pos and event.buttons() & Qt.MouseButton.MiddleButton:
                    delta = event.globalPosition() - self._last_mouse_pos
                    self._last_mouse_pos = event.globalPosition()
                    
                    # Logique de rotation intuitive type "Orbit"
                    # Delta X -> Rotation Z (tourner autour de l'axe vertical)
                    # Delta Y -> Rotation X (incliner)
                    
                    self._rot_z += delta.x() * 0.5
                    self._rot_x += delta.y() * 0.5
                    
                    # Clamp rot_x (0 à 85 degrés)
                    self._rot_x = max(0.0, min(85.0, self._rot_x))
                    
                    self.rotation_changed.emit(self._rot_x, self._rot_z)
                    return True
                    
        return super().eventFilter(obj, event)
    
    def set_overlay(self, image: QImage, distance_km: float = 0.0):
        self.current_image = image
        self.distance_km = distance_km
        
        self.distance_label.setText(f"Distance: {distance_km:.1f} km")
        
        display_image = self._create_display_image(image)
        pixmap = QPixmap.fromImage(display_image)
        
        scaled = pixmap.scaled(
            self.preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.preview_label.setPixmap(scaled)
        self.export_btn.setEnabled(True)
    
    def _create_display_image(self, overlay: QImage) -> QImage:
        display = QImage(overlay.size(), QImage.Format.Format_ARGB32)
        display.fill(QColor("#1a1a1a"))
        
        painter = QPainter(display)
        painter.drawImage(0, 0, overlay)
        painter.end()
        
        return display
    
    def _on_export_clicked(self):
        if self.current_image is None:
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter l'Overlay",
            "overlay.png",
            "Images PNG (*.png)"
        )
        
        if path:
            if not path.lower().endswith('.png'):
                path += '.png'
            
            if self.current_image.save(path, "PNG"):
                self.export_requested.emit(path)
    
    def clear(self):
        self.current_image = None
        self.distance_km = 0.0
        self.preview_label.clear()
        self.distance_label.setText("Distance: --")
        self.export_btn.setEnabled(False)
    
    def set_current_rotation(self, rot_x, rot_z):
        self._rot_x = rot_x
        self._rot_z = rot_z
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.current_image:
            # Re-render preview on resize
            display_image = self._create_display_image(self.current_image)
            pixmap = QPixmap.fromImage(display_image)
            scaled = pixmap.scaled(
                self.preview_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled)
