#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Widget grille de vidéos - Version production.
Cartes carrées avec miniature extraite du milieu de la vidéo.
"""

from typing import Optional, List, Dict
import os
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtWidgets import (
    QWidget, QGridLayout, QScrollArea, QVBoxLayout,
    QLabel, QFrame, QSizePolicy
)
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QBrush
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QObject

from redcam.domain.gps_types import VideoLocation


class ThumbnailExtractor(QObject):
    """
    Extracteur de miniatures vidéo - frame du milieu.
    """
    thumbnail_ready = pyqtSignal(str, QImage)
    
    def __init__(self):
        super().__init__()
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.processed = set()
        self._stopped = False
    
    def request_thumbnail(self, video_path: str, duration: float):
        """Demande une miniature pour une vidéo."""
        if video_path in self.processed or self._stopped:
            return
        self.processed.add(video_path)
        self.executor.submit(self._extract, video_path, duration)
    
    def _extract(self, path: str, duration: float):
        """Extrait la frame du milieu de la vidéo."""
        if self._stopped:
            return
        
        try:
            # Position au milieu de la vidéo
            mid_time = max(0, duration / 2)
            
            # Commande ffmpeg pour extraire une frame
            cmd = [
                'ffmpeg',
                '-ss', str(mid_time),
                '-i', path,
                '-vframes', '1',
                '-f', 'image2pipe',
                '-vcodec', 'png',
                '-vf', 'scale=160:120:force_original_aspect_ratio=increase,crop=160:120',
                '-'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            if result.returncode == 0 and result.stdout:
                image = QImage()
                if image.loadFromData(result.stdout):
                    if not self._stopped:
                        self.thumbnail_ready.emit(path, image)
        except Exception:
            pass
    
    def stop(self):
        self._stopped = True
        self.executor.shutdown(wait=False)


class VideoCard(QFrame):
    """
    Carte vidéo carrée avec miniature centrée.
    """
    clicked = pyqtSignal(object)
    
    CARD_SIZE = 120
    THUMB_SIZE = 108  # Avec padding
    
    def __init__(self, video: VideoLocation, parent=None):
        super().__init__(parent)
        self.video = video
        self.selected = False
        self.thumbnail: Optional[QPixmap] = None
        
        self.setFixedSize(self.CARD_SIZE, self.CARD_SIZE + 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 4)
        layout.setSpacing(4)
        
        # Container pour la miniature (carré)
        self.thumb_container = QFrame()
        self.thumb_container.setFixedSize(self.THUMB_SIZE, self.THUMB_SIZE)
        self.thumb_container.setStyleSheet("""
            QFrame {
                background-color: #0f0f0f;
                border: 1px solid #252525;
                border-radius: 2px;
            }
        """)
        
        thumb_layout = QVBoxLayout(self.thumb_container)
        thumb_layout.setContentsMargins(0, 0, 0, 0)
        
        self.thumb_label = QLabel()
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setFixedSize(self.THUMB_SIZE - 2, self.THUMB_SIZE - 2)
        thumb_layout.addWidget(self.thumb_label)
        
        layout.addWidget(self.thumb_container, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Nom de la vidéo
        name = video.custom_name or video.video_name
        # Troncature intelligente
        base, ext = os.path.splitext(name)
        if len(base) > 12:
            name = base[:10] + ".." + ext
        
        self.name_label = QLabel(name)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setStyleSheet("""
            QLabel {
                color: #707070;
                font-size: 9px;
                font-weight: 400;
                background: transparent;
            }
        """)
        layout.addWidget(self.name_label)
    
    def _update_style(self):
        if self.selected:
            self.setStyleSheet("""
                VideoCard {
                    background-color: #1a2530;
                    border: 1px solid #3a7fc4;
                    border-radius: 3px;
                }
            """)
            self.name_label.setStyleSheet("""
                QLabel {
                    color: #a0c0e0;
                    font-size: 9px;
                    font-weight: 500;
                    background: transparent;
                }
            """) if hasattr(self, 'name_label') else None
        else:
            self.setStyleSheet("""
                VideoCard {
                    background-color: #1a1a1a;
                    border: 1px solid #252525;
                    border-radius: 3px;
                }
                VideoCard:hover {
                    background-color: #1f1f1f;
                    border-color: #303030;
                }
            """)
            if hasattr(self, 'name_label'):
                self.name_label.setStyleSheet("""
                    QLabel {
                        color: #707070;
                        font-size: 9px;
                        font-weight: 400;
                        background: transparent;
                    }
                """)
    
    def set_selected(self, selected: bool):
        self.selected = selected
        self._update_style()
    
    def set_thumbnail(self, image: QImage):
        pixmap = QPixmap.fromImage(image)
        # Crop carré au centre
        size = min(pixmap.width(), pixmap.height())
        x = (pixmap.width() - size) // 2
        y = (pixmap.height() - size) // 2
        cropped = pixmap.copy(x, y, size, size)
        
        scaled = cropped.scaled(
            self.THUMB_SIZE - 2,
            self.THUMB_SIZE - 2,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.thumbnail = scaled
        self.thumb_label.setPixmap(scaled)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.video)
        super().mousePressEvent(event)


class VideoGridWidget(QScrollArea):
    """
    Grille scrollable de cartes vidéo - style production.
    """
    video_selected = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.videos: List[VideoLocation] = []
        self.cards: Dict[str, VideoCard] = {}
        self.selected_video: Optional[VideoLocation] = None
        
        # Extracteur de miniatures
        self.thumb_extractor = ThumbnailExtractor()
        self.thumb_extractor.thumbnail_ready.connect(self._on_thumbnail_ready)
        
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setStyleSheet("""
            QScrollArea {
                background-color: #141414;
                border: none;
                border-right: 1px solid #0a0a0a;
            }
            QScrollBar:vertical {
                background: #141414;
                width: 8px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #2a2a2a;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)
        
        self.container = QWidget()
        self.container.setStyleSheet("background-color: #141414;")
        self.grid_layout = QGridLayout(self.container)
        self.grid_layout.setContentsMargins(8, 8, 8, 8)
        self.grid_layout.setSpacing(6)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        self.setWidget(self.container)
    
    def set_videos(self, videos: List[VideoLocation]):
        for card in self.cards.values():
            card.deleteLater()
        self.cards.clear()
        
        self.videos = [v for v in videos if v.is_located()]
        
        cols = max(1, (self.width() - 20) // (VideoCard.CARD_SIZE + 6))
        
        for i, video in enumerate(self.videos):
            row = i // cols
            col = i % cols
            
            card = VideoCard(video)
            card.clicked.connect(self._on_card_clicked)
            
            self.grid_layout.addWidget(card, row, col)
            self.cards[video.video_path] = card
            
            duration = video.duration_seconds or 10.0
            self.thumb_extractor.request_thumbnail(video.video_path, duration)
    
    def _on_card_clicked(self, video: VideoLocation):
        if self.selected_video and self.selected_video.video_path in self.cards:
            self.cards[self.selected_video.video_path].set_selected(False)
        
        self.selected_video = video
        if video.video_path in self.cards:
            self.cards[video.video_path].set_selected(True)
        
        self.video_selected.emit(video)
    
    def _on_thumbnail_ready(self, path: str, image: QImage):
        if path in self.cards:
            self.cards[path].set_thumbnail(image)
    
    def select_video(self, video_path: str):
        for video in self.videos:
            if video.video_path == video_path:
                self._on_card_clicked(video)
                break
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.videos:
            cols = max(1, (self.width() - 20) // (VideoCard.CARD_SIZE + 6))
            for i, (path, card) in enumerate(self.cards.items()):
                row = i // cols
                col = i % cols
                self.grid_layout.addWidget(card, row, col)
    
    def cleanup(self):
        if self.thumb_extractor:
            self.thumb_extractor.stop()
