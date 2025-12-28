#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Widget Timeline avancé pour RedCAM (Style DaVinci Resolve).
Visualisation multi-pistes (GPS, Vidéo) avec scrubbing fluide.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from bisect import bisect_right
from math import radians, sin, cos, sqrt, atan2

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene,
    QGraphicsRectItem, QGraphicsLineItem, QGraphicsTextItem,
    QGraphicsItem, QToolButton, QLabel, QStyle
)
from PyQt6.QtGui import QPen, QBrush, QColor, QPainter, QFont, QPolygonF, QPixmap, QImage, QCursor
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF, QTimer, QThread, QObject

import subprocess
import threading
import os
import multiprocessing
from concurrent.futures import ThreadPoolExecutor

from redcam.domain.gps_types import VideoLocation, GPSTrack, GPSPoint

# Constantes de style
COLOR_TIMELINE_BG = QColor("#121212")  # Très sombre, presque noir
COLOR_TRACK_BG = QColor("#1e1e1e")     # Fond de piste sombre
COLOR_GPS_TRACK = QColor("#4caf50")
COLOR_VIDEO_CLIP = QColor("#4682b4")   # SteelBlue, plus proche de Resolve
COLOR_VIDEO_HOVER = QColor("#5a9bc4")
COLOR_VIDEO_SELECTED = QColor("#cd5c5c") # IndianRed pour la sélection (style Resolve)
COLOR_MARKER_SYNC = QColor("#59c27a")
COLOR_PLAYHEAD = QColor("#e53935")     # Rouge vif Resolve
COLOR_RULER_BG = QColor("#1a1a1a")
COLOR_RULER_TEXT = QColor("#808080")
DEFAULT_PIXELS_PER_SECOND = 10.0
MIN_PIXELS_PER_SECOND = 0.5
MAX_PIXELS_PER_SECOND = 80.0

class ThumbnailWorker(QObject):
    """Gère la génération de miniatures vidéo en arrière-plan via ffmpeg (Parallélisé)."""
    thumbnail_ready = pyqtSignal(str, QImage)

    def __init__(self):
        super().__init__()
        # Utiliser un pool de threads pour traiter plusieurs vidéos simultanément
        # On laisse un cœur libre pour l'UI
        max_workers = max(1, multiprocessing.cpu_count() - 1)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.processed = set()
        self.lock = threading.Lock()

    def request_thumbnail(self, video_path, duration):
        with self.lock:
            if video_path in self.processed:
                return
            self.processed.add(video_path)
        
        self.executor.submit(self._generate_task, video_path, duration)

    def stop(self):
        self.executor.shutdown(wait=False)

    def _generate_task(self, path, duration):
        try:
            image = self._generate_thumbnail(path, duration)
            if image:
                self.thumbnail_ready.emit(path, image)
        except Exception as e:
            print(f"Thumbnail error for {path}: {e}")

    def _generate_thumbnail(self, path, duration):
        if not os.path.exists(path):
            return None
            
        # Generate a strip of 5 frames
        num_frames = 5
        dur = max(1.0, duration)
        fps = num_frames / dur
        
        # Optimisation: -skip_frame nokey pour ne décoder que les keyframes (beaucoup plus rapide)
        # scale=-1:64 -> hauteur 64px
        cmd = [
            "ffmpeg",
            "-skip_frame", "nokey",
            "-i", path,
            "-vf", f"fps={fps},scale=-1:64,tile={num_frames}x1",
            "-frames:v", "1",
            "-f", "image2",
            "-c:v", "mjpeg",
            "pipe:1"
        ]
        
        # On Windows, prevent console window popping up
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.DEVNULL,
            startupinfo=startupinfo
        )
        out, _ = process.communicate()
        
        if out:
            image = QImage.fromData(out)
            if not image.isNull():
                return image
        return None

class TimelineScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundBrush(QBrush(COLOR_TIMELINE_BG))

class VideoClipItem(QGraphicsRectItem):
    """Représente un clip vidéo sur la timeline."""
    
    def __init__(self, x, y, w, h, video: VideoLocation, parent_widget):
        super().__init__(x, y, w, h)
        self.video = video
        self.parent_widget = parent_widget
        self.setAcceptHoverEvents(True)
        self.thumbnail_image = None
        
        # Style par défaut
        self.default_brush = QBrush(COLOR_VIDEO_CLIP)
        self.hover_brush = QBrush(COLOR_VIDEO_HOVER)
        self.selected_brush = QBrush(COLOR_VIDEO_SELECTED)
        
        self.default_pen = QPen(QColor("#1a1a1a"), 1)
        
        self.setBrush(self.default_brush)
        self.setPen(self.default_pen)
        
    def set_thumbnail(self, image: QImage):
        self.thumbnail_image = image
        self.update()

    def paint(self, painter, option, widget):
        rect = self.rect()
        
        # 1. Draw content (Thumbnail or Solid Color)
        if self.thumbnail_image:
            # Draw filmstrip stretched
            painter.drawImage(rect, self.thumbnail_image)
            # Add tint
            painter.fillRect(rect, QColor(0, 0, 0, 40))
        else:
            painter.setBrush(self.brush())
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(rect)
            
        # 2. Draw Selection/Hover Overlay
        if self.parent_widget.selected_item == self:
            # Selection border (Red)
            painter.setPen(QPen(QColor("#e53935"), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)
        elif self.brush() == self.hover_brush:
            # Hover highlight
            painter.fillRect(rect, QColor(255, 255, 255, 30))
            
        # 3. Draw standard border if not selected
        if self.parent_widget.selected_item != self:
            painter.setPen(self.pen())
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)

    def hoverEnterEvent(self, event):
        if self != self.parent_widget.selected_item:
            self.setBrush(self.hover_brush)
        super().hoverEnterEvent(event)
        
    def hoverLeaveEvent(self, event):
        if self != self.parent_widget.selected_item:
            self.setBrush(self.default_brush)
        super().hoverLeaveEvent(event)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent_widget.select_clip_item(self)
            # Ne pas propager pour éviter de déplacer la playhead au clic (optionnel)
            event.accept()
        else:
            super().mousePressEvent(event)

class TimelineWidget(QWidget):
    """
    Widget affichant une timeline multi-pistes.
    """
    
    # Signal émis quand le temps change (timestamp)
    time_changed = pyqtSignal(datetime)
    # Signal émis quand une vidéo est sélectionnée
    video_selected = pyqtSignal(str) # Chemin de la vidéo
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.duration: timedelta = timedelta(0)
        self.current_time: Optional[datetime] = None
        self.pixels_per_second: float = DEFAULT_PIXELS_PER_SECOND
        self.videos: List[VideoLocation] = []

        self.track: Optional[GPSTrack] = None
        self._distance_series: List[tuple[datetime, float]] = []  # (timestamp, cumulative_km)
        self.total_distance_km: Optional[float] = None

        # Si True, la timeline suit automatiquement la largeur visible.
        self.fit_mode: bool = True
        
        self.scene = TimelineScene()
        self.view = QGraphicsView(self.scene)
        self.view.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.view.setFrameShape(QGraphicsView.Shape.NoFrame) # Remove border
        
        self.clip_items = {} # Map video_path -> VideoClipItem
        self.selected_item = None
        
        # Thumbnails
        self.thumbnail_cache = {}
        self.thumbnail_worker = ThumbnailWorker()
        self.thumbnail_worker.thumbnail_ready.connect(self._on_thumbnail_ready)
        
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._tick_playback)
        self.playing = False
        
        self.last_mouse_pos = None
        
        # Playhead
        self.playhead = QGraphicsLineItem()
        self.playhead.setPen(QPen(COLOR_PLAYHEAD, 3))
        self.playhead.setZValue(100)
        self.scene.addItem(self.playhead)
        
        controls = QHBoxLayout()
        controls.setContentsMargins(6, 4, 6, 4)
        controls.setSpacing(6)

        self.btn_play_pause = QToolButton()
        self.btn_play_pause.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.btn_play_pause.setAutoRaise(True)
        self.btn_play_pause.clicked.connect(self._toggle_play)
        
        self.btn_zoom_out = QToolButton()
        self.btn_zoom_out.setText("–")
        self.btn_zoom_out.setAutoRaise(True)
        self.btn_zoom_out.clicked.connect(lambda: self._zoom(0.8))
        
        self.btn_zoom_fit = QToolButton()
        self.btn_zoom_fit.setText("Ajuster")
        self.btn_zoom_fit.setAutoRaise(True)
        self.btn_zoom_fit.clicked.connect(self._fit_to_view)
        
        self.btn_zoom_in = QToolButton()
        self.btn_zoom_in.setText("+")
        self.btn_zoom_in.setAutoRaise(True)
        self.btn_zoom_in.clicked.connect(lambda: self._zoom(1.25))
        
        control_style = """
        QToolButton {
            background: #2a2a2a;
            color: #e0e0e0;
            border: none;
            border-radius: 0px;
            padding: 6px 10px;
            min-width: 28px;
            font-weight: 700;
        }
        QToolButton:hover { background: #333333; }
        QToolButton:pressed { background: #1f1f1f; }
        """
        for btn in (self.btn_play_pause, self.btn_zoom_out, self.btn_zoom_fit, self.btn_zoom_in):
            btn.setStyleSheet(control_style)

        controls.addWidget(self.btn_play_pause)
        controls.addWidget(self.btn_zoom_out)
        controls.addWidget(self.btn_zoom_fit)
        controls.addWidget(self.btn_zoom_in)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #d5d5d5; font-weight: 600; padding-left: 8px;")
        controls.addWidget(self.lbl_status)
        controls.addStretch()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(controls)
        layout.addWidget(self.view)
        
        # Event handling
        self.view.mousePressEvent = self._on_mouse_press
        self.view.mouseMoveEvent = self._on_mouse_move
        self.view.mouseReleaseEvent = self._on_mouse_release

    def _on_thumbnail_ready(self, path: str, image: QImage):
        self.thumbnail_cache[path] = image
        if path in self.clip_items:
            self.clip_items[path].set_thumbnail(image)

    def _toggle_play(self):
        if not self.start_time or not self.end_time:
            return
        if not self.current_time:
            self.current_time = self.start_time
        self.playing = not self.playing
        if self.playing:
            self.btn_play_pause.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
            self.timer.start()
        else:
            self.btn_play_pause.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            self.timer.stop()

    def _tick_playback(self):
        if not self.playing or not self.start_time or not self.end_time:
            return
        if not self.current_time:
            self.current_time = self.start_time

        delta_s = self.timer.interval() / 1000.0
        next_time = self.current_time + timedelta(seconds=delta_s)
        if next_time >= self.end_time:
            next_time = self.end_time
            self.playing = False
            self.timer.stop()
            self.btn_play_pause.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))

        self._set_position_from_time(next_time, emit_signal=True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Re-fit automatiquement uniquement si on est en mode Ajuster.
        if self.fit_mode and self.duration:
            self._fit_to_view()
            self._rebuild_scene()

    def set_track(self, track: Optional[GPSTrack]) -> None:
        """Injecte la trace GPS pour permettre l'affichage des distances sur la règle."""
        self.track = track
        self._distance_series = []
        self.total_distance_km = None

        if not track or not track.points:
            self._rebuild_scene()
            return

        points = [p for p in track.points if p and p.is_valid() and p.timestamp is not None]
        if len(points) < 2:
            self._rebuild_scene()
            return

        # Assurer l'ordre temporel
        points.sort(key=lambda p: p.timestamp)

        cumulative_km = 0.0
        self._distance_series = [(points[0].timestamp, 0.0)]

        prev = points[0]
        for p in points[1:]:
            cumulative_km += self._haversine_km(prev, p)
            self._distance_series.append((p.timestamp, cumulative_km))
            prev = p

        self.total_distance_km = cumulative_km
        self._rebuild_scene()

    def _haversine_km(self, a: GPSPoint, b: GPSPoint) -> float:
        """Distance haversine en km entre deux points GPS."""
        # Rayon moyen Terre (km)
        r = 6371.0
        lat1 = radians(a.latitude)
        lon1 = radians(a.longitude)
        lat2 = radians(b.latitude)
        lon2 = radians(b.longitude)

        dlat = lat2 - lat1
        dlon = lon2 - lon1
        h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(h), sqrt(1 - h))
        return r * c

    def _distance_at_time(self, t: datetime) -> Optional[float]:
        if not self._distance_series:
            return None
        timestamps = [ts for ts, _ in self._distance_series]
        if t <= timestamps[0]:
            return 0.0
        if t >= timestamps[-1]:
            return float(self._distance_series[-1][1])

        idx = bisect_right(timestamps, t)
        if idx <= 0:
            return 0.0
        if idx >= len(self._distance_series):
            return float(self._distance_series[-1][1])

        t0, d0 = self._distance_series[idx - 1]
        t1, d1 = self._distance_series[idx]
        dt = (t1 - t0).total_seconds()
        if dt <= 0:
            return float(d0)
        alpha = (t - t0).total_seconds() / dt
        return float(d0 + (d1 - d0) * alpha)
        
    def set_range(self, start: datetime, end: datetime) -> None:
        """Définit la plage temporelle et redessine la timeline."""
        self.start_time = start
        self.end_time = end
        self.duration = end - start
        self.current_time = start
        self.fit_mode = True
        self.playing = False
        self.timer.stop()
        self.btn_play_pause.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self._fit_to_view()
        self._rebuild_scene()
        
    def set_videos(self, videos: List[VideoLocation]) -> None:
        """Ajoute les segments vidéo sur la timeline."""
        self.videos = [v for v in videos if v.creation_time]

        if not self.videos:
            self._rebuild_scene()
            return

        # Si la range n'est pas encore définie, caler sur les vidéos
        default_duration = timedelta(seconds=60)
        earliest = min(v.creation_time for v in self.videos)
        latest = max(v.creation_time + default_duration for v in self.videos)

        if self.start_time is None:
            self.start_time = earliest
        if self.end_time is None:
            self.end_time = latest

        # Si la range est déjà définie, on l'étend si nécessaire pour inclure toutes les vidéos
        if self.start_time and self.end_time:
            self.start_time = min(self.start_time, earliest)
            self.end_time = max(self.end_time, latest)
            self.duration = self.end_time - self.start_time
            self.playing = False
            self.timer.stop()
            self.btn_play_pause.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            self._fit_to_view()
            self._rebuild_scene()

    def _rebuild_scene(self):
        """Reconstruit la scène graphique."""
        self.scene.clear()
        self.clip_items.clear()
        self.selected_item = None
        self.playing = False
        self.timer.stop()
        self.btn_play_pause.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        
        if not self.duration:
            return

        total_seconds = max(1, self.duration.total_seconds())

        # Ajuster le zoom pour occuper toute la largeur visible
        if self.fit_mode:
            self._fit_to_view()

        width = total_seconds * self.pixels_per_second
        viewport_width = self.view.viewport().width() or 0
        if viewport_width > 0:
            width = max(width, viewport_width)

        height = 140
        
        self.scene.setSceneRect(0, 0, width, height)
        
        ruler_height = 46
        video_band_top = ruler_height + 12
        video_band_height = 44

        # Bande vidéo principale
        track_rect = QGraphicsRectItem(0, video_band_top - 4, width, video_band_height + 8)
        track_rect.setBrush(QBrush(COLOR_TRACK_BG))
        track_rect.setPen(QPen(Qt.PenStyle.NoPen))
        self.scene.addItem(track_rect)

        # Clips vidéo + marqueurs
        self._draw_clips(width, video_band_top, video_band_height)

        # Règle temporelle
        self._draw_ruler(width, total_seconds, ruler_height)
        
        # 5. Playhead (ligne + poignée triangle rouge)
        self.playhead = QGraphicsLineItem(0, 0, 0, height)
        self.playhead.setPen(QPen(COLOR_PLAYHEAD, 1.5)) # Ligne plus fine
        self.playhead.setZValue(100)
        self.scene.addItem(self.playhead)

        # Triangle inversé pour la tête de lecture
        handle_size = 6
        handle = QPolygonF([
            QPointF(-handle_size, 0),
            QPointF(handle_size, 0),
            QPointF(0, handle_size + 4),
            QPointF(-handle_size, 0)
        ])
        self.playhead_handle = self.scene.addPolygon(handle, QPen(Qt.PenStyle.NoPen), QBrush(COLOR_PLAYHEAD))
        self.playhead_handle.setZValue(101)

        self._apply_playhead_position()
        self._update_status_label()
        
    def _draw_ruler(self, width: float, total_seconds: float, ruler_height: float) -> None:
        """Dessine la règle temporelle."""
        bg = QGraphicsRectItem(0, 0, width, ruler_height)
        bg.setBrush(QBrush(COLOR_RULER_BG))
        bg.setPen(QPen(Qt.PenStyle.NoPen))
        self.scene.addItem(bg)
        
        # Ligne de séparation bas de règle
        bottom_line = QGraphicsLineItem(0, ruler_height, width, ruler_height)
        bottom_line.setPen(QPen(QColor("#333333"), 1))
        self.scene.addItem(bottom_line)

        step_seconds = 60
        if self.pixels_per_second > 20:
            step_seconds = 10
        if self.pixels_per_second < 2:
            step_seconds = 300
        
        # Petits ticks intermédiaires
        sub_step = step_seconds / 5 if step_seconds >= 10 else step_seconds / 2
        
        for sec in range(0, int(total_seconds) + 1, int(sub_step)):
            x = sec * self.pixels_per_second
            if x > width: break
            
            is_major = (sec % step_seconds) == 0
            tick_h = 10 if is_major else 5
            y_start = ruler_height - tick_h
            
            line = QGraphicsLineItem(x, y_start, x, ruler_height)
            line.setPen(QPen(COLOR_RULER_TEXT if is_major else QColor("#555555")))
            self.scene.addItem(line)
            
            if is_major:
                if self.start_time:
                    tick_time = self.start_time + timedelta(seconds=sec)
                    tick_local = tick_time.astimezone()
                    time_str = tick_local.strftime("%H:%M") if step_seconds >= 60 else tick_local.strftime("%H:%M:%S")
                else:
                    time_str = str(timedelta(seconds=sec))

                text = QGraphicsTextItem(time_str)
                text.setDefaultTextColor(COLOR_RULER_TEXT)
                text.setPos(x + 2, ruler_height - 20)
                text.setFont(QFont("Segoe UI", 8))
                self.scene.addItem(text)

    def _format_elapsed(self, td: timedelta) -> str:
        total_seconds = int(max(0, td.total_seconds()))
        minutes = total_seconds // 60
        hours = minutes // 60
        minutes = minutes % 60
        if hours > 0:
            return f"{hours}h{minutes:02d}"
        return f"{minutes}min"

    def _update_status_label(self) -> None:
        if not self.start_time or not self.current_time:
            self.lbl_status.setText("")
            return

        local_time = self.current_time.astimezone()
        hour_str = local_time.strftime("%H:%M:%S")
        elapsed = self.current_time - self.start_time
        elapsed_str = self._format_elapsed(elapsed)
        km = self._distance_at_time(self.current_time)
        km_str = f"km {km:.1f}" if km is not None else "km -"

        self.lbl_status.setText(f"{hour_str}  |  {km_str}  |  temps {elapsed_str}")

    def _draw_clips(self, width: float, video_top: float, video_height: float) -> None:
        """Dessine tous les clips vidéo en blocs colorés."""
        if not self.videos or not self.start_time:
            return
        
        clip_height = max(24.0, video_height - 4.0) # Plus haut pour remplir la piste
        y_pos = video_top + (video_height - clip_height) / 2
        
        # Couleurs alternées subtiles pour distinguer les clips adjacents
        color_variants = [
            COLOR_VIDEO_CLIP,
            COLOR_VIDEO_CLIP.lighter(110),
        ]
        sorted_videos = sorted(self.videos, key=lambda v: v.creation_time)

        for idx, video in enumerate(sorted_videos):
            start_offset = (video.creation_time - self.start_time).total_seconds()
            x = start_offset * self.pixels_per_second

            duration_seconds = float(video.duration_seconds) if video.duration_seconds else 1.0
            if idx + 1 < len(sorted_videos):
                next_video = sorted_videos[idx + 1]
                next_start_offset = (next_video.creation_time - self.start_time).total_seconds()
                available = max(0.5, next_start_offset - start_offset)
                duration_seconds = min(duration_seconds, available)

            w = max(10.0, duration_seconds * self.pixels_per_second)
            if x + w < 0 or x > width:
                continue
            
            color = color_variants[idx % len(color_variants)]
            item = VideoClipItem(x, y_pos, w, clip_height, video, self)
            item.default_brush = QBrush(color)
            item.hover_brush = QBrush(COLOR_VIDEO_HOVER)
            item.selected_brush = QBrush(COLOR_VIDEO_SELECTED)
            item.setBrush(item.default_brush)
            
            item.setOpacity(1.0) # Opaque pour look "solide"
            item.setZValue(20)
            self.scene.addItem(item)
            self.clip_items[video.video_path] = item
            
            # Request thumbnail
            if video.video_path in self.thumbnail_cache:
                item.set_thumbnail(self.thumbnail_cache[video.video_path])
            else:
                self.thumbnail_worker.request_thumbnail(video.video_path, video.duration_seconds)

            # Nom du fichier sur le clip si assez de place
            if w > 40:
                name = video.video_path.split("\\")[-1].split("/")[-1]
                text = QGraphicsTextItem(name, item)
                text.setDefaultTextColor(QColor("white"))
                text.setFont(QFont("Segoe UI", 8))
                # Clip text to width
                # (Simple implementation: just position it)
                text.setPos(x + 2, y_pos + 2)
                # Ensure text doesn't spill out visually (QGraphicsTextItem doesn't clip automatically easily without more code, 
                # but ZValue helps or just let it be for now as it's on top of the clip)

            # Marqueur de synchro (petit triangle au début du clip)
            marker_poly = QPolygonF([
                QPointF(x, video_top - 4),
                QPointF(x + 8, video_top - 4),
                QPointF(x + 4, video_top - 12)
            ])
            marker = self.scene.addPolygon(marker_poly, QPen(Qt.PenStyle.NoPen), QBrush(COLOR_MARKER_SYNC))
            marker.setZValue(25)

    def select_clip_item(self, item: VideoClipItem):
        """Gère la sélection d'un clip (interne)."""
        # Évite une boucle: timeline -> main_window -> timeline
        if self.selected_item is item:
            return

        # Reset précédent
        if self.selected_item:
            self.selected_item.setBrush(self.selected_item.default_brush)
            self.selected_item.setPen(self.selected_item.default_pen)
            
        self.selected_item = item
        
        # Highlight nouveau (Glow effect simulé par bordure blanche épaisse + couleur vive)
        item.setBrush(item.selected_brush)
        item.setPen(QPen(QColor("white"), 3))
        
        # Émettre signal
        self.video_selected.emit(item.video.video_path)

    def select_video(self, video_path: str):
        """Sélectionne une vidéo depuis l'extérieur (ex: map)."""
        if video_path in self.clip_items:
            item = self.clip_items[video_path]
            self.select_clip_item(item)
            # Scroll to item if needed
            self.view.ensureVisible(item)

    def _fit_to_view(self) -> None:
        """Ajuste automatiquement le zoom pour occuper la largeur disponible."""
        if not self.duration:
            return
        total_seconds = max(1, self.duration.total_seconds())
        viewport_width = self.view.viewport().width() or self.width() or 800
        target_pps = viewport_width / total_seconds
        self.pixels_per_second = self._clamp_pps(target_pps)

    def _zoom(self, factor: float) -> None:
        if not self.duration:
            return
        self.fit_mode = False
        self.pixels_per_second = self._clamp_pps(self.pixels_per_second * factor)
        self._rebuild_scene()
        
        # Centrer sur la tête de lecture après le zoom
        if self.playhead:
            self.view.centerOn(self.playhead)

    def _clamp_pps(self, value: float) -> float:
        return max(MIN_PIXELS_PER_SECOND, min(MAX_PIXELS_PER_SECOND, value))

    def _apply_playhead_position(self) -> None:
        """Replace la tête de lecture après un rebuild."""
        if not self.start_time or not self.current_time:
            return
        delta = (self.current_time - self.start_time).total_seconds()
        x = max(0, delta * self.pixels_per_second)
        rect = self.scene.sceneRect()
        x = min(x, rect.width()) if rect else x
        scene_h = rect.height() if rect else 0
        self.playhead.setLine(x, 0, x, scene_h)
        if hasattr(self, 'playhead_handle') and self.playhead_handle:
            self.playhead_handle.setPos(x, 0)
        self._update_status_label()

    def _on_mouse_press(self, event):
        """Gère le clic pour déplacer la tête de lecture ou le panning."""
        if event.button() == Qt.MouseButton.MiddleButton:
            self.last_mouse_pos = event.pos()
            self.view.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        pos = self.view.mapToScene(event.pos())
        # IMPORTANT: on override QGraphicsView.mousePressEvent, donc on doit gérer
        # nous-mêmes la détection de clic sur items (sinon il faut double-cliquer).
        if self._try_select_item_at(pos):
            return
        self._update_playhead_from_x(pos.x())
        
    def _on_mouse_move(self, event):
        """Gère le glisser pour le scrubbing ou le panning."""
        if self.last_mouse_pos is not None:
            delta = event.pos() - self.last_mouse_pos
            self.last_mouse_pos = event.pos()
            h_bar = self.view.horizontalScrollBar()
            h_bar.setValue(h_bar.value() - delta.x())
            event.accept()
            return

        if event.buttons() & Qt.MouseButton.LeftButton:
            pos = self.view.mapToScene(event.pos())
            self._update_playhead_from_x(pos.x())

    def _on_mouse_release(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self.last_mouse_pos = None
            self.view.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        QGraphicsView.mouseReleaseEvent(self.view, event)

    def _set_position_from_time(self, timestamp: datetime, emit_signal: bool = True) -> None:
        """Met à jour la position du playhead à partir d'un timestamp."""
        if not self.start_time:
            return
        delta = (timestamp - self.start_time).total_seconds()
        x = max(0.0, delta * self.pixels_per_second)
        rect = self.scene.sceneRect()
        if rect:
            x = min(x, rect.width())
        self.playhead.setLine(x, 0, x, rect.height() if rect else 0)
        if hasattr(self, 'playhead_handle') and self.playhead_handle:
            self.playhead_handle.setPos(x, 0)
        self.current_time = timestamp
        self._update_status_label()
        if emit_signal:
            self.time_changed.emit(timestamp)

    def _try_select_item_at(self, pos: QPointF) -> bool:
        """Sélectionne un clip si la position correspond à un cube vidéo."""
        # items() renvoie les items du dessus vers le dessous (via Z)
        for scene_item in self.scene.items(pos):
            if isinstance(scene_item, VideoClipItem):
                self.select_clip_item(scene_item)
                return True
        return False

    def _update_playhead_from_x(self, x):
        """Met à jour la position et émet le signal."""
        if not self.start_time or not self.duration:
            return
        rect = self.scene.sceneRect()
        x = max(0, min(x, rect.width())) if rect else max(0, x)
        scene_h = rect.height() if rect else 0
        self.playhead.setLine(x, 0, x, scene_h)
        if hasattr(self, 'playhead_handle') and self.playhead_handle:
            self.playhead_handle.setPos(x, 0)

        seconds = x / self.pixels_per_second
        new_time = self.start_time + timedelta(seconds=seconds)
        self.current_time = new_time
        self._update_status_label()
        self.time_changed.emit(new_time)
        
    def set_position(self, timestamp: datetime):
        """Met à jour la position visuelle depuis l'extérieur."""
        self._set_position_from_time(timestamp, emit_signal=False)
