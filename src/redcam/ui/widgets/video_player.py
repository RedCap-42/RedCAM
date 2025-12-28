#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Lecteur vidéo intégré pour RedCAM.
Widget encapsulant le lecteur vidéo pour intégration dans la fenêtre principale.
"""

import os
import subprocess

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QSlider, QLabel, QStyle, QGroupBox
)
from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

from .fullscreen_video import FullscreenVideoWindow


class VideoPlayerWidget(QGroupBox):
    """Widget de lecture vidéo intégré."""
    
    def __init__(self, parent=None):
        super().__init__("Lecteur Vidéo", parent)
        
        # Média Player
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        
        # Video Widget
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(200) # Hauteur minimale pour la colonne latérale
        self.media_player.setVideoOutput(self.video_widget)
        
        self._init_ui()
        
        # Connexions
        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.durationChanged.connect(self._on_duration_changed)
        self.media_player.playbackStateChanged.connect(self._update_buttons)
        self.media_player.errorOccurred.connect(self._on_error)
        
        # État
        self.current_video_path = None
        self.fullscreen_window = None
        
    def _init_ui(self):
        # Style spécifique pour ce widget
        self.setStyleSheet("""
            QGroupBox {
                border: 1px solid #3a3a3a;
                border-radius: 0px;
                margin-top: 10px;
                font-weight: 700;
                color: #e0e0e0;
                background-color: #252525;
                padding-top: 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
            QPushButton {
                background-color: #2a4d69;
                border: 1px solid #355d7f;
                border-radius: 6px;
                padding: 6px 10px;
                color: #f0f0f0;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #3b6d93; border-color: #4b7aa5; }
            QLabel { color: #c8c8c8; font-family: monospace; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 15, 10, 10)

        # Ligne info (nom fichier + bouton dossier)
        info_layout = QHBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(6)

        self.lbl_video_name = QLabel("—")
        self.lbl_video_name.setToolTip("Vidéo sélectionnée")
        self.lbl_video_name.setStyleSheet("color: #ddd; font-family: 'Segoe UI';")

        self.btn_open_folder = QPushButton("Folder")
        self.btn_open_folder.setFixedHeight(26)
        self.btn_open_folder.setToolTip("Ouvrir le dossier et sélectionner le fichier")
        self.btn_open_folder.clicked.connect(self._open_in_folder)
        self.btn_open_folder.setEnabled(False)

        info_layout.addWidget(self.lbl_video_name)
        info_layout.addStretch()
        info_layout.addWidget(self.btn_open_folder)

        layout.addLayout(info_layout)
        
        # Vidéo
        layout.addWidget(self.video_widget)
        
        # Contrôles
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        
        # Play/Pause
        self.btn_play = QPushButton()
        self.btn_play.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.btn_play.setFixedSize(30, 30)
        self.btn_play.clicked.connect(self.play_pause)
        self.btn_play.setEnabled(False)
        
        # Slider position
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 0)
        self.slider.sliderMoved.connect(self._set_position)
        
        # Labels temps
        self.lbl_current = QLabel("00:00")
        self.lbl_duration = QLabel("00:00")
        
        controls_layout.addWidget(self.btn_play)
        controls_layout.addWidget(self.lbl_current)
        controls_layout.addWidget(self.slider)
        controls_layout.addWidget(self.lbl_duration)
        
        # Bouton plein écran
        self.btn_fullscreen = QPushButton("⛶")
        self.btn_fullscreen.setFixedSize(30, 30)
        self.btn_fullscreen.setToolTip("Plein écran")
        self.btn_fullscreen.clicked.connect(self._open_fullscreen)
        self.btn_fullscreen.setEnabled(False)
        controls_layout.addWidget(self.btn_fullscreen)
        
        layout.addLayout(controls_layout)

    def load_video(self, path: str, autoplay: bool = True):
        """Charge une vidéo. Si autoplay=False, la met en pause."""
        self.current_video_path = path
        self.lbl_video_name.setText(os.path.basename(path))
        self.lbl_video_name.setToolTip(path)
        self.btn_open_folder.setEnabled(True)
        self.media_player.setSource(QUrl.fromLocalFile(path))
        self.btn_play.setEnabled(True)
        self.btn_fullscreen.setEnabled(True)

        if autoplay:
            self.media_player.play()
        else:
            # Astuce QtMultimedia: play puis pause pour afficher une frame sans lancer.
            self.media_player.play()
            QTimer.singleShot(0, self.media_player.pause)

    def _open_in_folder(self):
        """Ouvre l'explorateur Windows sur le fichier sélectionné."""
        if not self.current_video_path or not os.path.exists(self.current_video_path):
            return
        try:
            # Windows: ouvrir Explorer en sélectionnant le fichier
            subprocess.Popen([
                "explorer.exe",
                "/select,",
                os.path.normpath(self.current_video_path)
            ])
        except Exception:
            # Fallback: ouvrir le dossier
            try:
                os.startfile(os.path.dirname(self.current_video_path))
            except Exception:
                pass
        
    def play_pause(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()
            
    def _update_buttons(self):
        state = self.media_player.playbackState()
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        else:
            self.btn_play.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            
    def _on_position_changed(self, position):
        if not self.slider.isSliderDown():
            self.slider.setValue(position)
        self.lbl_current.setText(self._format_time(position))
        
    def _on_duration_changed(self, duration):
        self.slider.setRange(0, duration)
        self.lbl_duration.setText(self._format_time(duration))
        
    def _set_position(self, position):
        self.media_player.setPosition(position)
        
    def _format_time(self, ms):
        seconds = (ms // 1000) % 60
        minutes = (ms // 60000)
        return f"{minutes:02}:{seconds:02}"
    
    def _on_error(self):
        err = self.media_player.error()
        err_msg = self.media_player.errorString()
        print(f"Erreur Lecture Vidéo: {err} - {err_msg}")
        
    def close_player(self):
        """Arrête la lecture."""
        self.media_player.stop()
        self.media_player.setSource(QUrl())
        self.current_video_path = None
        if self.fullscreen_window:
            self.fullscreen_window.close()
            self.fullscreen_window = None

    def _open_fullscreen(self):
        """Ouvre la vidéo en plein écran."""
        if not self.current_video_path:
            return
            
        # Pause le lecteur intégré
        current_pos = self.media_player.position()
        self.media_player.pause()
        
        # Créer et afficher la fenêtre plein écran
        self.fullscreen_window = FullscreenVideoWindow()
        self.fullscreen_window.closed.connect(self._on_fullscreen_closed)
        self.fullscreen_window.show_fullscreen_animated(self.current_video_path, current_pos)
        
    def _on_fullscreen_closed(self):
        """Appelé quand le plein écran se ferme."""
        if self.fullscreen_window:
            try:
                # Récupérer la position AVANT de perdre la référence
                new_pos = self.fullscreen_window.get_current_position()
                self.media_player.setPosition(new_pos)
                self.media_player.play()
            except Exception as e:
                print(f"Erreur retour plein écran: {e}")
            finally:
                try:
                    self.fullscreen_window.cleanup()
                except Exception:
                    pass
                self.fullscreen_window = None

