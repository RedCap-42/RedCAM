#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, 
    QDialogButtonBox, QPushButton, QColorDialog, QLabel
)
from PyQt6.QtGui import QColor
from redcam.domain.gps_types import VideoLocation

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
