#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fenêtre vidéo plein écran pour RedCAM.

Implémentation orientée fluidité:
- Utilise QVideoWidget (backend vidéo natif) plutôt que QGraphicsVideoItem.
- Overlay (contrôles + retour) au-dessus via layout, avec auto-hide.
"""

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QSlider,
    QLabel,
    QVBoxLayout,
    QFrame,
    QToolButton,
    QSizePolicy,
    QStyle,
    QGridLayout,
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QTimer, QEvent
from PyQt6.QtGui import QKeyEvent

from ..theme.styles import COLOR_ACCENT


def _tool_btn(parent: QWidget, icon: QStyle.StandardPixmap, tooltip: str) -> QToolButton:
    btn = QToolButton(parent)
    btn.setToolTip(tooltip)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setIcon(parent.style().standardIcon(icon))
    btn.setIconSize(btn.iconSize().expandedTo(btn.sizeHint()))
    btn.setFixedSize(56, 56)
    btn.setStyleSheet(
        "QToolButton {"
        "  background-color: rgba(20, 20, 20, 180);"
        "  border: 1px solid rgba(255, 255, 255, 30);"
        "  border-radius: 12px;"
        "}"
        "QToolButton:hover {"
        "  background-color: rgba(255, 255, 255, 18);"
        "}"
        "QToolButton:pressed {"
        "  background-color: rgba(255, 255, 255, 10);"
        "}"
    )
    return btn


class FullscreenVideoWindow(QWidget):
    """Fenêtre plein écran haute performance (QGraphicsView + OpenGL)."""
    
    closed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._closed_emitted = False
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("background-color: black;")
        self.setMouseTracking(True)

        # --- Vidéo (widget natif, généralement plus fluide) ---
        self.video_widget = QVideoWidget(self)
        self.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.video_widget.setMouseTracking(True)
        # QVideoWidget peut être une surface native qui "mange" les events souris.
        # On laisse l'overlay gérer l'interaction (contrôles + auto-hide).
        self.video_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        
        # Media Player
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)
        
        # --- Overlay ---
        self.overlay = QWidget(self)
        self.overlay.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.overlay.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.overlay.setStyleSheet("background: transparent;")
        self.overlay.setMouseTracking(True)

        overlay_layout = QVBoxLayout(self.overlay)
        overlay_layout.setContentsMargins(24, 24, 24, 24)
        overlay_layout.setSpacing(0)

        # Top row: back button
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        self.btn_back = _tool_btn(self.overlay, QStyle.StandardPixmap.SP_ArrowBack, "Retour")
        self.btn_back.clicked.connect(self._close_fullscreen)
        top_row.addWidget(self.btn_back, alignment=Qt.AlignmentFlag.AlignLeft)
        top_row.addStretch(1)
        overlay_layout.addLayout(top_row)

        overlay_layout.addStretch(1)

        # Bottom controls
        self.controls_widget = QFrame(self.overlay)
        self.controls_widget.setObjectName("ControlBar")
        self.controls_widget.setStyleSheet(
            "QFrame#ControlBar {"
            "  background-color: rgba(20, 20, 20, 220);"
            "  border: 1px solid rgba(255, 255, 255, 30);"
            "  border-radius: 12px;"
            "}"
            "QSlider::groove:horizontal {"
            "  height: 4px;"
            "  background: rgba(255, 255, 255, 50);"
            "  border-radius: 2px;"
            "}"
            "QSlider::handle:horizontal {"
            f"  background: {COLOR_ACCENT};"
            "  width: 18px;"
            "  height: 18px;"
            "  margin: -7px 0;"
            "  border-radius: 9px;"
            "  border: 2px solid white;"
            "}"
            "QSlider::sub-page:horizontal {"
            f"  background: {COLOR_ACCENT};"
            "  border-radius: 2px;"
            "}"
            "QLabel {"
            "  color: #EEEEEE;"
            "  font-size: 14px;"
            "  font-weight: 600;"
            "  background: transparent;"
            "  margin: 0 10px;"
            "}"
        )

        controls_layout = QHBoxLayout(self.controls_widget)
        controls_layout.setContentsMargins(24, 12, 24, 12)

        self.btn_play = _tool_btn(self.controls_widget, QStyle.StandardPixmap.SP_MediaPause, "Lecture / Pause")
        self.btn_play.clicked.connect(self._toggle_play)

        self.slider = QSlider(Qt.Orientation.Horizontal, self.controls_widget)
        self.slider.setRange(0, 5000)
        self.slider.sliderMoved.connect(self._seek)

        self.lbl_time = QLabel("00:00 / 00:00", self.controls_widget)

        controls_layout.addWidget(self.btn_play)
        controls_layout.addWidget(self.slider, stretch=1)
        controls_layout.addWidget(self.lbl_time)

        overlay_layout.addWidget(self.controls_widget)

        # --- Root layout: stack video + overlay ---
        root = QGridLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.video_widget, 0, 0)
        root.addWidget(self.overlay, 0, 0)
        self.overlay.raise_()
        
        # Timer auto-hide
        self.hide_timer = QTimer(self)
        self.hide_timer.setInterval(3000)
        self.hide_timer.timeout.connect(self._hide_controls)
        
        # Connexions
        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.durationChanged.connect(self._on_duration_changed)
        self.media_player.playbackStateChanged.connect(self._on_state_changed)
        self.media_player.mediaStatusChanged.connect(self._on_media_status_changed)
        
        self._duration = 0
        self._pending_pos = -1

        # Mouse move events: centralize via eventFilter.
        self.installEventFilter(self)
        self.overlay.installEventFilter(self)

    def resizeEvent(self, event):
        self.overlay.raise_()
        super().resizeEvent(event)

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.MouseMove, QEvent.Type.HoverMove):
            self._show_controls()
        return super().eventFilter(watched, event)

    def _show_controls(self):
        self.controls_widget.show()
        self.btn_back.show()  # toujours visible
        self.setCursor(Qt.CursorShape.ArrowCursor)
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.hide_timer.start()

    def _hide_controls(self):
        if self.controls_widget.underMouse() or self.btn_back.underMouse():
            return
        self.controls_widget.hide()
        self.hide_timer.stop()

    def show_fullscreen_animated(self, video_path: str, start_position: int = 0):
        self.showFullScreen()
        self._pending_pos = start_position
        self.media_player.setSource(QUrl.fromLocalFile(video_path))
        self._show_controls()

    def _on_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.LoadedMedia and self._pending_pos >= 0:
            self.media_player.setPosition(self._pending_pos)
            self.media_player.play()
            self._pending_pos = -1

    def _close_fullscreen(self):
        self.hide_timer.stop()
        try:
            # Stop sans raise si déjà relâché/détruit
            if self.media_player:
                self.media_player.stop()
                self.media_player.setSource(QUrl())
            if self.audio_output:
                self.media_player.setAudioOutput(None)
                self.audio_output = None
        except Exception:
            pass
        finally:
            if not self._closed_emitted:
                self.closed.emit()
                self._closed_emitted = True
            self.close()

    def closeEvent(self, event):
        # Sécurité pour éviter les crashs lors d'une fermeture externe
        if self.media_player:
            try:
                self.media_player.stop()
                self.media_player.setSource(QUrl())
            except Exception:
                pass
        # Déréférencer l'audio pour éviter double libération
        try:
            if self.audio_output:
                self.media_player.setAudioOutput(None)
                self.audio_output = None
        except Exception:
            pass
        if not self._closed_emitted:
            self.closed.emit()
            self._closed_emitted = True
        event.accept()

    def _toggle_play(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def _seek(self, position):
        if self._duration > 0:
            self.media_player.setPosition(int(position * self._duration / 5000))

    def _on_position_changed(self, position):
        if self._duration > 0:
            if not self.slider.isSliderDown():
                self.slider.setValue(int(position * 5000 / self._duration))
            self._update_time_label(position, self._duration)

    def _on_duration_changed(self, duration):
        self._duration = duration

    def _on_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        else:
            self.btn_play.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))

    def _update_time_label(self, pos, dur):
        def fmt(ms):
            s = int(ms // 1000)
            m = s // 60
            s = s % 60
            return f"{m:02d}:{s:02d}"
        self.lbl_time.setText(f"{fmt(pos)} / {fmt(dur)}")

    def keyPressEvent(self, event: QKeyEvent):
        self._show_controls()
        if event.key() == Qt.Key.Key_Escape:
            self._close_fullscreen()
        elif event.key() == Qt.Key.Key_Space:
            self._toggle_play()
        super().keyPressEvent(event)

    def get_current_position(self) -> int:
        return self.media_player.position()

    def cleanup(self):
        """Libère proprement les ressources multimédia (appelée côté parent si nécessaire)."""
        try:
            if self.media_player:
                self.media_player.stop()
                self.media_player.setSource(QUrl())
        except Exception:
            pass
        try:
            if self.audio_output:
                self.media_player.setAudioOutput(None)
                self.audio_output = None
        except Exception:
            pass
