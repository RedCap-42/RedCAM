#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Widget de chargement de fichiers pour RedCAM.
Permet de sélectionner les fichiers .fit et les dossiers vidéo.
"""

from typing import Optional, List
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel,
    QFileDialog, QGroupBox, QCheckBox, QComboBox, QHBoxLayout,
    QStyle
)
from PyQt6.QtCore import pyqtSignal

from ..theme.styles import (
    BUTTON_STYLE, BUTTON_SECONDARY_STYLE, GROUPBOX_STYLE, 
    LABEL_STYLE, PROGRESS_BAR_STYLE, CHECKBOX_STYLE, COMBO_STYLE
)
from .scrubber import ScrubberInput


class FileLoaderWidget(QWidget):
    """
    Widget permettant à l'utilisateur de charger les fichiers nécessaires.
    """
    
    # Signaux
    fit_file_selected = pyqtSignal(str)     # Chemin du fichier .fit
    video_folder_selected = pyqtSignal(str) # Chemin du dossier vidéo
    sync_requested = pyqtSignal()           # Demande de synchronisation
    weak_gps_toggled = pyqtSignal(bool)     # Toggle pour le mode GPS faible
    watch_brand_changed = pyqtSignal(str)   # Marque de montre sélectionnée
    camera_model_changed = pyqtSignal(str)   # Modèle de caméra sélectionné
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        self.fit_path: Optional[str] = None
        self.video_folder: Optional[str] = None
        
        self._init_ui()
        
    def _init_ui(self) -> None:
        """Initialise l'interface utilisateur."""
        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        layout.setContentsMargins(16, 16, 16, 16)
        
        # --- Section Fichier GPS ---
        group_fit = QGroupBox("Fichier GPS")
        group_fit.setStyleSheet(GROUPBOX_STYLE)
        fit_layout = QVBoxLayout(group_fit)
        fit_layout.setSpacing(12)
        
        # Sélecteur de marque
        brand_layout = QHBoxLayout()
        brand_label = QLabel("Montre:")
        brand_label.setStyleSheet(LABEL_STYLE)
        self.combo_brand = QComboBox()
        self.combo_brand.addItems(["Garmin", "Coros"])
        self.combo_brand.setStyleSheet(COMBO_STYLE)
        self.combo_brand.currentTextChanged.connect(self.watch_brand_changed.emit)
        brand_layout.addWidget(brand_label)
        brand_layout.addWidget(self.combo_brand)
        fit_layout.addLayout(brand_layout)
        
        self.btn_load_fit = QPushButton("Charger fichier .fit")
        self.btn_load_fit.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.btn_load_fit.setStyleSheet(BUTTON_SECONDARY_STYLE)
        self.btn_load_fit.clicked.connect(self._browse_fit)
        
        self.lbl_fit_status = QLabel("Aucun fichier sélectionné")
        self.lbl_fit_status.setStyleSheet(LABEL_STYLE + "font-style: italic; color: #8a8a8a;")
        self.lbl_fit_status.setWordWrap(True)
        
        fit_layout.addWidget(self.btn_load_fit)
        fit_layout.addWidget(self.lbl_fit_status)
        
        layout.addWidget(group_fit)
        
        # --- Section Vidéos ---
        group_video = QGroupBox("Vidéos")
        group_video.setStyleSheet(GROUPBOX_STYLE)
        video_layout = QVBoxLayout(group_video)
        
        # Filtre Caméra
        cam_layout = QHBoxLayout()
        cam_label = QLabel("Caméra:")
        cam_label.setStyleSheet(LABEL_STYLE)
        self.combo_cam = QComboBox()
        self.combo_cam.addItems([
            "Auto (Détection)", 
            "Hero 10 ou + (GPS)", 
            "Hero 9 ou - (GPS)", 
            "Hero 12 (Pas de GPS)",
            "DJI (Synchro .fit)",
            "Insta360 (Synchro .fit)"
        ])
        self.combo_cam.setStyleSheet(COMBO_STYLE)
        self.combo_cam.currentTextChanged.connect(self.camera_model_changed.emit)
        cam_layout.addWidget(cam_label)
        cam_layout.addWidget(self.combo_cam)
        video_layout.addLayout(cam_layout)
        
        # Scrubber Décalage
        offset_layout = QHBoxLayout()
        offset_label = QLabel("Décalage (s):")
        offset_label.setStyleSheet(LABEL_STYLE)
        self.scrubber_offset = ScrubberInput()
        self.scrubber_offset.setRange(-3600, 3600)
        self.scrubber_offset.setSingleStep(0.1)
        self.scrubber_offset.setValue(0.0)
        self.scrubber_offset.setToolTip("Glissez pour ajuster le décalage temporel")
        offset_layout.addWidget(offset_label)
        offset_layout.addWidget(self.scrubber_offset)
        video_layout.addLayout(offset_layout)
        
        self.btn_load_video = QPushButton("Charger dossier vidéos")
        self.btn_load_video.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.btn_load_video.setStyleSheet(BUTTON_SECONDARY_STYLE)
        self.btn_load_video.clicked.connect(self._browse_video_folder)
        
        self.lbl_video_status = QLabel("Aucun dossier sélectionné")
        self.lbl_video_status.setStyleSheet(LABEL_STYLE + "font-style: italic; color: #8a8a8a;")
        self.lbl_video_status.setWordWrap(True)
        
        video_layout.addWidget(self.btn_load_video)
        video_layout.addWidget(self.lbl_video_status)
        
        layout.addWidget(group_video)
        
        # --- Options ---
        group_options = QGroupBox("Options")
        group_options.setStyleSheet(GROUPBOX_STYLE)
        options_layout = QVBoxLayout(group_options)
        options_layout.setSpacing(10)
        
        self.chk_weak_gps = QCheckBox("Mode Signal GPS Faible")
        self.chk_weak_gps.setToolTip(
            "Activez cette option si le GPS de la GoPro est imprécis.\n"
            "Cela forcera la synchronisation basée sur l'heure."
        )
        self.chk_weak_gps.setStyleSheet(CHECKBOX_STYLE)
        self.chk_weak_gps.toggled.connect(self.weak_gps_toggled.emit)
        
        options_layout.addWidget(self.chk_weak_gps)
        layout.addWidget(group_options)
        
        # Bouton Synchroniser
        layout.addStretch()
        self.btn_sync = QPushButton("Synchroniser")
        self.btn_sync.setStyleSheet(BUTTON_STYLE)
        self.btn_sync.setMinimumHeight(40)
        self.btn_sync.clicked.connect(self.sync_requested.emit)
        self.btn_sync.setEnabled(False)  # Désactivé tant que pas de dossier vidéo
        
        layout.addWidget(self.btn_sync)

    def _browse_fit(self) -> None:
        """Ouvre un dialogue pour sélectionner un fichier .fit."""
        fname, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner un fichier .fit", "", "Fichiers Garmin (*.fit)"
        )
        if fname:
            self.fit_path = fname
            self.lbl_fit_status.setText(os.path.basename(fname))
            self.lbl_fit_status.setStyleSheet(LABEL_STYLE + "color: #6dd19c; font-weight: bold;")
            self.fit_file_selected.emit(fname)
            
    def _browse_video_folder(self) -> None:
        """Ouvre un dialogue pour sélectionner le dossier vidéo."""
        folder = QFileDialog.getExistingDirectory(
            self, "Sélectionner le dossier contenant les vidéos"
        )
        if folder:
            self.video_folder = folder
            self.lbl_video_status.setText(folder)
            self.lbl_video_status.setStyleSheet(LABEL_STYLE + "color: #6dd19c; font-weight: bold;")
            self.video_folder_selected.emit(folder)
            self.btn_sync.setEnabled(True)
            self.btn_sync.setStyleSheet(BUTTON_STYLE) # Reset style to active

    def set_processing(self, processing: bool) -> None:
        """
        Active ou désactive les contrôles pendant le traitement.
        
        Args:
            processing: True si traitement en cours
        """
        enabled = not processing
        self.btn_load_fit.setEnabled(enabled)
        self.btn_load_video.setEnabled(enabled)
        self.btn_sync.setEnabled(enabled and self.video_folder is not None)
        self.chk_weak_gps.setEnabled(enabled)
        
        if processing:
            self.btn_sync.setText("Traitement...")
        else:
            self.btn_sync.setText("Synchroniser")
            
    def set_fit_file(self, path: str) -> None:
        """Définit le fichier FIT programmatiquement."""
        if os.path.exists(path):
            self.fit_path = path
            self.lbl_fit_status.setText(os.path.basename(path))
            self.fit_file_selected.emit(path)
            
    def set_video_folder(self, path: str) -> None:
        """Définit le dossier vidéo programmatiquement."""
        if os.path.isdir(path):
            self.video_folder = path
            self.lbl_video_status.setText(path)
            self.btn_sync.setEnabled(True)
            self.video_folder_selected.emit(path)
            
    def set_weak_gps(self, enabled: bool) -> None:
        """Définit l'état du toggle GPS faible."""
        self.chk_weak_gps.setChecked(enabled)

    
    def get_fit_path(self) -> Optional[str]:
        """Retourne le chemin du fichier .fit sélectionné."""
        return self.fit_path
    
    def get_video_folder(self) -> Optional[str]:
        """Retourne le chemin du dossier vidéos sélectionné."""
        return self.video_folder
    
    def get_camera_filter(self) -> str:
        """Retourne le filtre de caméra sélectionné."""
        return self.combo_cam.currentText()
    
    def get_manual_offset(self) -> float:
        """Retourne le décalage manuel en secondes."""
        return self.scrubber_offset.value()

    def set_manual_offset(self, value: float) -> None:
        """Définit le décalage manuel (en secondes)."""
        try:
            self.scrubber_offset.setValue(float(value))
        except Exception:
            self.scrubber_offset.setValue(0.0)
    
    def reset(self) -> None:
        """Réinitialise le widget."""
        self.fit_path = None
        self.video_folder = None
        self.lbl_fit_path.setText("Aucun fichier sélectionné")
        self.lbl_fit_path.setStyleSheet("color: #666; font-style: italic;")
        self.lbl_video_path.setText("Aucun dossier sélectionné")
        self.lbl_video_path.setStyleSheet("color: #666; font-style: italic;")
        self.btn_sync.setEnabled(False)
