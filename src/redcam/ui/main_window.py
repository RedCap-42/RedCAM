#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fenêtre principale de l'application RedCAM.
Orchestre les widgets (carte, chargement, timeline) et le contrôleur.
"""

import os
import sys
from typing import Optional, List

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QSplitter, QMessageBox, QFrame, QFileDialog, QMenu,
    QDockWidget, QLabel, QPushButton, QApplication, QMenuBar, QSizePolicy
)
from PyQt6.QtGui import QDesktopServices, QAction, QIcon, QMouseEvent
from PyQt6.QtCore import Qt, QUrl, QPoint, QSize

from .widgets.map_widget import MapWidget
from .widgets.file_loader_widget import FileLoaderWidget
from .widgets.timeline_widget import TimelineWidget
from .widgets.progress_indicator import ProgressIndicator
from .widgets.video_player import VideoPlayerWidget
from .theme.styles import WINDOW_STYLE, TITLE_BAR_STYLE

from redcam.services.sync_controller import SyncController
from redcam.workers.worker_threads import ProcessingWorker
from redcam.services.project_manager import ProjectManager
from redcam.domain.gps_types import VideoLocation


class CustomTitleBar(QWidget):
    """Barre de titre personnalisée style DaVinci."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self.setStyleSheet(TITLE_BAR_STYLE)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 0, 8, 0)
        self.layout.setSpacing(6)
        
        # Menu placeholder (inséré au début)
        
        self.layout.addStretch()
        
        # Boutons de fenêtre (style minimal)
        btn_size = QSize(36, 26)
        
        self.btn_min = QPushButton("–")
        self.btn_min.setFixedSize(btn_size)
        self.btn_min.clicked.connect(self.window().showMinimized)
        
        self.btn_max = QPushButton("▢")
        self.btn_max.setFixedSize(btn_size)
        self.btn_max.clicked.connect(self._toggle_max)
        
        self.btn_close = QPushButton("×")
        self.btn_close.setFixedSize(btn_size)
        self.btn_close.setObjectName("close_btn")
        self.btn_close.clicked.connect(self.window().close)
        
        self.layout.addWidget(self.btn_min)
        self.layout.addWidget(self.btn_max)
        self.layout.addWidget(self.btn_close)
        
        self.start_pos = None

    def add_menu(self, menu_bar: QMenuBar):
        """Ajoute la barre de menu au titre."""
        self.layout.insertWidget(0, menu_bar)

    def _toggle_max(self):
        if self.window().isMaximized():
            self.window().showNormal()
        else:
            self.window().showMaximized()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.start_pos:
            delta = event.globalPosition().toPoint() - self.start_pos
            self.window().move(self.window().pos() + delta)
            self.start_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.start_pos = None


class MainWindow(QMainWindow):
    """Fenêtre principale de l'application."""
    
    def __init__(self) -> None:
        """Initialise la fenêtre."""
        super().__init__()
        
        self.current_project_path = None
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle("RedCAM v1.1.0 - Synchronisation GoPro & Garmin")
        self.resize(1400, 900)
        self.setStyleSheet(WINDOW_STYLE)
        
        # Custom Title Bar
        self.title_bar = CustomTitleBar(self)
        self.setMenuWidget(self.title_bar)
        
        # Contrôleur
        self.controller = SyncController()
        
        # Worker thread
        self.worker: Optional[ProcessingWorker] = None
        
        # Lecteur vidéo intégré
        self.video_player = None 
        
        # Gestionnaire de projet
        self.project_manager = ProjectManager()
        
        # État
        self.force_timestamp_sync = False
        
        self.setAcceptDrops(True)
        
        self._init_ui()
        self._create_menu_bar()
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path) and path.lower().endswith('.fit'):
                self.loader_widget.set_fit_file(path)
            elif os.path.isdir(path):
                self.loader_widget.set_video_folder(path)
        
    def _init_ui(self) -> None:
        """Initialise l'interface utilisateur avec Docking."""
        self.setDockOptions(QMainWindow.DockOption.AnimatedDocks | QMainWindow.DockOption.AllowNestedDocks)

        # 1. Central Widget (Map)
        self.map_widget = MapWidget()
        self.map_widget.video_clicked.connect(self._play_video)
        self.setCentralWidget(self.map_widget)

        # 2. Left Dock (Files & Import)
        self.dock_files = QDockWidget("Fichier", self)
        self.dock_files.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.dock_files.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        self.dock_files.setMinimumWidth(320)
        
        self.loader_widget = FileLoaderWidget()
        self.loader_widget.fit_file_selected.connect(self._on_fit_selected)
        self.loader_widget.video_folder_selected.connect(self._on_folder_selected)
        self.loader_widget.sync_requested.connect(self._start_sync)
        self.loader_widget.weak_gps_toggled.connect(self._on_weak_gps_toggled)
        self.loader_widget.camera_model_changed.connect(lambda _: self._on_weak_gps_toggled(self.force_timestamp_sync))
        
        # Container for left dock to include progress bar
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0,0,0,0)
        left_layout.addWidget(self.loader_widget)
        
        self.progress_bar = ProgressIndicator()
        left_layout.addWidget(self.progress_bar)
        left_layout.addStretch()
        
        self.dock_files.setWidget(left_container)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_files)

        # 3. Video Dock (Right of Map by default)
        self.dock_video = QDockWidget("Prévisualisation Vidéo", self)
        self.dock_video.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetFloatable | QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.dock_video.setMinimumWidth(400)
        self.video_player = VideoPlayerWidget()
        self.dock_video.setWidget(self.video_player)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_video)
        
        # 4. Timeline Dock (Bottom)
        self.dock_timeline = QDockWidget("Timeline de Synchronisation", self)
        self.dock_timeline.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        self.dock_timeline.setMinimumHeight(180)
        self.timeline_widget = TimelineWidget()
        self.timeline_widget.time_changed.connect(self._on_timeline_changed)
        self.dock_timeline.setWidget(self.timeline_widget)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dock_timeline)

        # Connexions croisées
        self.timeline_widget.video_selected.connect(self._on_video_selected)
        self.map_widget.video_clicked.connect(self._on_video_selected)

        
    def _on_fit_selected(self, path: str) -> None:
        """Gère la sélection d'un fichier FIT."""
        self.controller.fit_path = path
        
        # Charger et afficher la trace immédiatement
        success = self.controller.load_fit_file(path)
        if success and self.controller.track:
            self.map_widget.display_track(self.controller.track)
            
            # Mettre à jour la timeline
            track = self.controller.track
            if track.points and track.points[0].timestamp and track.points[-1].timestamp:
                self.timeline_widget.set_track(track)
                self.timeline_widget.set_range(
                    track.points[0].timestamp,
                    track.points[-1].timestamp
                )
        
    def _on_folder_selected(self, path: str) -> None:
        """Gère la sélection d'un dossier vidéo."""
        self.controller.video_folder = path
        
    def _start_sync(self) -> None:
        """Démarre le processus de synchronisation."""
        if not self.controller.fit_path:
            QMessageBox.warning(
                self,
                "Attention",
                "Veuillez sélectionner un fichier FIT (Garmin)."
            )
            return
        
        if not self.controller.video_folder:
            QMessageBox.warning(
                self,
                "Attention",
                "Veuillez sélectionner un dossier contenant des vidéos GoPro."
            )
            return
        
        # Désactiver les contrôles
        self.loader_widget.set_processing(True)
        self.progress_bar.start_progress()
        self.progress_bar.set_status("Traitement des vidéos...")
        
        # Créer et lancer le worker
        self.worker = ProcessingWorker(
            self.controller,
            fit_path=self.controller.fit_path,
            video_folder=self.controller.video_folder
        )
        
        # Passer l'option weak gps et filtre caméra
        self.worker.force_timestamp_sync = self.force_timestamp_sync
        self.worker.camera_filter = self.loader_widget.get_camera_filter()
        
        # Connecter les signaux du worker
        self.worker.progress.connect(self._on_progress)
        self.worker.videos_processed.connect(self._on_videos_processed)
        self.worker.error.connect(self._on_error)
        self.worker.status_update.connect(self._on_status_update)
        self.worker.finished_processing.connect(self._on_processing_finished)
        
        # Démarrer le traitement
        self.worker.start()
    
    def _on_progress(self, current: int, total: int) -> None:
        """Met à jour la progression."""
        self.progress_bar.set_progress(current, total)
    
    def _on_status_update(self, message: str) -> None:
        """Met à jour le message de statut."""
        self.progress_bar.set_status(message)
    
    def _on_videos_processed(self, locations: List[VideoLocation]) -> None:
        """Gère la fin du traitement des vidéos."""
        track = self.controller.get_track()
        
        if track and not track.is_empty():
            self.map_widget.display_track(track, locations)
            
            if track.points and track.points[0].timestamp and track.points[-1].timestamp:
                self.timeline_widget.set_track(track)
                self.timeline_widget.set_range(
                    track.points[0].timestamp,
                    track.points[-1].timestamp
                )
                # Afficher les vidéos sur la timeline
                self.timeline_widget.set_videos(locations)
        elif locations:
            self.map_widget.display_videos_only(locations)
        
        # Afficher le résumé
        summary = self.controller.get_summary()
        self.progress_bar.set_status(
            f"Terminé: {summary['located_videos']}/{summary['total_videos']} vidéos localisées"
        )
    
    def _on_error(self, message: str) -> None:
        """Gère les erreurs de traitement."""
        self.progress_bar.set_status(f"Erreur: {message}")
        QMessageBox.critical(self, "Erreur", message)
    
    def _on_weak_gps_toggled(self, enabled: bool) -> None:
        """Active/désactive le mode GPS faible."""
        self.force_timestamp_sync = enabled
        
        # Si on a déjà des données, relancer la synchronisation pour mettre à jour
        # C'est rapide grâce au cache du VideoLocator
        if (self.controller.video_locations and 
            self.worker is None and 
            self.controller.fit_path and 
            self.controller.video_folder):
            self._start_sync()

    def _on_video_selected(self, video_path: str) -> None:
        """Gère la sélection d'une vidéo (depuis timeline ou carte)."""
        if not os.path.exists(video_path):
            return

        # 1. Charger la vidéo dans le lecteur
        if self.video_player:
            if not self.video_player.isVisible():
                self.video_player.setVisible(True)
            self.video_player.load_video(video_path, autoplay=False)
            
        # 2. Sélectionner sur la carte (Glow/Highlight)
        if self.map_widget:
            self.map_widget.select_video(video_path)
            
        # 3. Sélectionner sur la timeline (Glow)
        if self.timeline_widget:
            self.timeline_widget.select_video(video_path)
    
    def _play_video(self, video_path: str) -> None:
        """Ouvre une vidéo dans le lecteur intégré."""
        # Obsolète: redirigé vers _on_video_selected via signal map_widget.video_clicked
        self._on_video_selected(video_path)
            
    def _on_timeline_changed(self, timestamp) -> None:
        """Gère le changement de position sur la timeline."""
        self.map_widget.update_current_position(timestamp)
    
    def _on_processing_finished(self) -> None:
        """Gère la fin du traitement."""
        self.loader_widget.set_processing(False)
        self.progress_bar.stop_progress()
        self.worker = None
        
        # Appliquer les métadonnées chargées si disponibles
        if hasattr(self, 'pending_metadata') and self.pending_metadata:
            for v in self.controller.video_locations:
                if v.video_path in self.pending_metadata:
                    meta = self.pending_metadata[v.video_path]
                    v.custom_name = meta.get('custom_name')
                    v.custom_note = meta.get('custom_note')
                    v.marker_color = meta.get('marker_color', "#3388ff")
                    v.marker_icon = meta.get('marker_icon', "circle")
            
            # Rafraîchir la carte avec les nouvelles données
            if self.map_widget:
                self.map_widget.display_track(self.controller.track, self.controller.video_locations)
            
            self.pending_metadata = {}
    
    def closeEvent(self, event) -> None:
        """Gère la fermeture de la fenêtre."""
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        
        self.map_widget.cleanup()
        if self.video_player:
            self.video_player.close_player()
            
        event.accept()

    def _create_menu_bar(self) -> None:
        """Crée la barre de menu."""
        # Création manuelle de la barre de menu pour l'intégrer au titre
        menu_bar = QMenuBar(self)
        menu_bar.setStyleSheet("""
            QMenuBar {
                background-color: transparent;
                color: #E0E0E0;
                border: none;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 4px 10px;
            }
            QMenuBar::item:selected {
                background-color: #3E3E3E;
            }
            QMenu {
                background-color: #2A2A2A;
                color: #E0E0E0;
                border: 1px solid #3E3E3E;
            }
            QMenu::item {
                padding: 4px 20px;
            }
            QMenu::item:selected {
                background-color: #E04F16;
                color: white;
            }
        """)
        
        # Menu Fichier
        file_menu = menu_bar.addMenu("&Fichier")
        
        # Ouvrir
        open_action = QAction("&Ouvrir Projet...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._load_project_dialog)
        file_menu.addAction(open_action)
        
        # Enregistrer
        save_action = QAction("&Enregistrer Projet...", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_project)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        # Récents
        self.recent_menu = file_menu.addMenu("Projets Récents")
        self._update_recent_menu()
        
        file_menu.addSeparator()
        
        # Quitter
        quit_action = QAction("&Quitter", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        # Ajouter au titre
        self.title_bar.add_menu(menu_bar)

    def _update_recent_menu(self) -> None:
        """Met à jour le menu des projets récents."""
        self.recent_menu.clear()
        projects = self.project_manager.get_recent_projects()
        
        if not projects:
            action = QAction("Aucun projet récent", self)
            action.setEnabled(False)
            self.recent_menu.addAction(action)
            return

        for path in projects:
            action = QAction(os.path.basename(path), self)
            action.setData(path)
            action.triggered.connect(lambda checked, p=path: self._load_project(p))
            self.recent_menu.addAction(action)

    def _save_project(self) -> None:
        """Sauvegarde le projet actuel."""
        path = self.current_project_path
        
        if not path:
            path, _ = QFileDialog.getSaveFileName(
                self, "Enregistrer le projet", "", "Fichiers JSON (*.json)"
            )
        
        if path:
            self.current_project_path = path
            
            # Collecter les métadonnées personnalisées
            video_metadata = {}
            if self.controller.video_locations:
                for v in self.controller.video_locations:
                    # Sauvegarder seulement si modifié
                    if (hasattr(v, 'custom_name') and v.custom_name) or \
                       (hasattr(v, 'custom_note') and v.custom_note) or \
                       (hasattr(v, 'marker_color') and v.marker_color != "#3388ff") or \
                       (hasattr(v, 'marker_icon') and v.marker_icon != "circle"):
                        video_metadata[v.video_path] = {
                            'custom_name': getattr(v, 'custom_name', None),
                            'custom_note': getattr(v, 'custom_note', None),
                            'marker_color': getattr(v, 'marker_color', "#3388ff"),
                            'marker_icon': getattr(v, 'marker_icon', "circle")
                        }

            data = {
                'fit_path': self.controller.fit_path,
                'video_folder': self.controller.video_folder,
                'force_timestamp_sync': self.force_timestamp_sync,
                'video_metadata': video_metadata
            }
            if self.project_manager.save_project(path, data):
                self.statusBar().showMessage(f"Projet enregistré: {os.path.basename(path)}", 3000)
                self._update_recent_menu()

    def _load_project_dialog(self) -> None:
        """Ouvre le dialogue de chargement."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Ouvrir un projet", "", "Fichiers JSON (*.json)"
        )
        if path:
            self._load_project(path)

    def _load_project(self, path: str) -> None:
        """Charge un projet spécifique."""
        data = self.project_manager.load_project(path)
        if not data:
            QMessageBox.warning(self, "Erreur", "Impossible de charger le projet.")
            return
            
        self.current_project_path = path
        
        # Appliquer les données
        fit_path = data.get('fit_path')
        video_folder = data.get('video_folder')
        force_weak = data.get('force_timestamp_sync', False)
        
        # Stocker les métadonnées pour application après traitement
        self.pending_metadata = data.get('video_metadata', {})
        
        if fit_path:
            self.loader_widget.set_fit_file(fit_path)
            
        if video_folder:
            self.loader_widget.set_video_folder(video_folder)
            
        self.loader_widget.set_weak_gps(force_weak)
        self.force_timestamp_sync = force_weak
        
        # Mettre à jour le menu récent
        self._update_recent_menu()
        self.statusBar().showMessage(f"Projet chargé: {os.path.basename(path)}", 3000)
        
        # Lancer la synchronisation automatiquement si possible
        if fit_path and video_folder and os.path.exists(fit_path) and os.path.exists(video_folder):
            self._start_sync()

