#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Menu de sélection de projet style DaVinci Resolve.
Affiche une grille de projets récents.
"""

import os
import json
from datetime import datetime
from typing import List, Optional

from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPointF
from PyQt6.QtGui import QIcon, QPixmap, QColor, QPainter, QBrush, QPen, QPolygonF
from redcam.infra.garmin.fit_parser import FitParser

# Constants de style
COLOR_BG = "#161616"       # DaVinci Dark Background
COLOR_CARD_BG = "#222222"  # Card Background
COLOR_CARD_HOVER = "#2a2a2a"
COLOR_SELECTED = "#e53935" # Resolve Red
COLOR_TEXT = "#e0e0e0"
COLOR_SUBTEXT = "#909090"
COLOR_BTN_NORMAL = "#333333"
COLOR_BTN_HOVER = "#444444"


class ProjectCard(QFrame):
    """Carte représentant un projet."""
    
    clicked = pyqtSignal(str) # Path
    double_clicked = pyqtSignal(str) # Path

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.path = path
        self.filename = os.path.basename(path) # .json filename
        # Remove extension for display if desired, but filename is explicit
        
        self.selected = False
        
        self.setFixedSize(220, 160) # Slightly more compact
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Info date and Fit Path extraction
        self.date_str = ""
        self.track_poly: Optional[QPolygonF] = None
        
        try:
            mtime = os.path.getmtime(path)
            dt = datetime.fromtimestamp(mtime)
            self.date_str = dt.strftime("%Y-%m-%d %H:%M")
            
            # Load JSON to find fit_path
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                fit_path = data.get('fit_path')
                
                # If we have a fit path, parse it to get the track
                if fit_path and os.path.exists(fit_path):
                     self._load_track_preview(fit_path)
                     
        except Exception as e:
            print(f"Error loading project card data for {path}: {e}")

    def _load_track_preview(self, fit_path: str):
        """Parse fit file and normalize points for preview."""
        try:
            parser = FitParser(fit_path)
            track = parser.parse()
            if track and track.points:
                # Downsample points for performance (every 10th point)
                points = track.points[::10] if len(track.points) > 100 else track.points
                
                lats = [p.latitude for p in points if p.latitude]
                lons = [p.longitude for p in points if p.longitude]
                
                if not lats or not lons:
                    return

                min_lat, max_lat = min(lats), max(lats)
                min_lon, max_lon = min(lons), max(lons)
                
                lat_range = max_lat - min_lat
                lon_range = max_lon - min_lon
                
                if lat_range == 0 or lon_range == 0:
                    return
                    
                poly = QPolygonF()
                for p in points:
                    if p.latitude and p.longitude:
                        # Normalize 0..1
                        # Invert Y for screen coords (max_lat is top/0 in geo, but 0 is top in screen. Wait. 
                        # High lat = North = Up. Screen 0 = Top. So High Lat maps to 0 if we map directly? 
                        # Actually: x = (lon - min_lon)/range
                        # y = (max_lat - lat)/range  (so max_lat becomes 0)
                        x = (p.longitude - min_lon) / lon_range
                        y = (max_lat - p.latitude) / lat_range
                        poly.append(QPointF(x, y))
                
                self.track_poly = poly
        except Exception as e:
            print(f"Error parsing fit for preview: {e}")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        
        # Background
        bg_color = QColor(COLOR_CARD_HOVER if self.underMouse() else COLOR_CARD_BG)
        if self.selected:
             bg_color = QColor("#2d2d2d")
             
        painter.setBrush(QBrush(bg_color))
        
        # Border
        if self.selected:
            painter.setPen(QPen(QColor(COLOR_SELECTED), 2))
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            
        # Sharper corners (3px instead of 6px)
        painter.drawRoundedRect(rect, 3, 3)
        
        # Thumbnail area (Top part)
        thumb_height = 100
        thumb_rect = rect.adjusted(4, 4, -4, 0)
        thumb_rect.setHeight(thumb_height)
        
        painter.setBrush(QBrush(QColor("#111111"))) # Blackish thumbnail bg
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(thumb_rect) # Sharp thumbnail
        
        # Draw Track Preview if available
        if self.track_poly:
            painter.setPen(QPen(QColor("#00E5FF"), 2)) # Cyan track like map
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            # Map normalized poly to thumb_rect
            # Padding
            pad = 10
            draw_rect = thumb_rect.adjusted(pad, pad, -pad, -pad)
            w = draw_rect.width()
            h = draw_rect.height()
            
            scaled_poly = QPolygonF()
            for pt in self.track_poly:
                sx = draw_rect.left() + pt.x() * w
                sy = draw_rect.top() + pt.y() * h
                scaled_poly.append(QPointF(sx, sy))
            
            painter.drawPolyline(scaled_poly)
            
        else:
            # Fallback Icon
            painter.setPen(QPen(QColor("#333"), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            center = thumb_rect.center()
            icon_size = 24
            icon_rect = rect.adjusted(0,0,0,0)
            icon_rect.setSize(QSize(icon_size, icon_size))
            icon_rect.moveCenter(center)
            painter.drawRect(icon_rect)
        
        # Text Area (Bottom)
        painter.setPen(QColor(COLOR_TEXT))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(9)
        painter.setFont(font)
        
        # Title
        text_rect = rect.adjusted(8, thumb_height + 10, -8, -20)
        # Elide text if too long
        metrics = painter.fontMetrics()
        elided_text = metrics.elidedText(self.filename, Qt.TextElideMode.ElideRight, text_rect.width())
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, elided_text)
        
        # Subtext (Date)
        painter.setPen(QColor(COLOR_SUBTEXT))
        font.setBold(False)
        font.setPointSize(8)
        painter.setFont(font)
        text_rect_sub = rect.adjusted(8, thumb_height + 28, -8, -4)
        painter.drawText(text_rect_sub, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, self.date_str)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.path)
            
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.path)
            
    def enterEvent(self, event):
        self.update()
        
    def leaveEvent(self, event):
        self.update()


class ProjectMenu(QDialog):
    """Fenêtre de sélection de projet (Startup)."""
    
    project_selected = pyqtSignal(str) # Path
    
    def __init__(self, projects: List[str], parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.resize(1080, 720) # Standard size
        self.setStyleSheet(f"background-color: {COLOR_BG}; color: {COLOR_TEXT}; font-family: 'Segoe UI';")
        
        self.projects = projects
        self.selected_path = None
        self.project_cards = []
        
        self._init_ui()
        
    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- Header ---
        header = QFrame()
        header.setFixedHeight(50)
        header.setStyleSheet("background-color: #1f1f1f; border-bottom: 1px solid #000;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 0, 16, 0)
        
        # Title
        title = QLabel("Project Manager")
        title.setStyleSheet("font-size: 14px; font-weight: 600; color: #ccc;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Close Button
        btn_close = QPushButton("×")
        btn_close.setFixedSize(24, 24)
        btn_close.clicked.connect(self.reject)
        btn_close.setStyleSheet("""
            QPushButton { background: transparent; color: #888; border: none; font-size: 18px; }
            QPushButton:hover { color: white; }
        """)
        header_layout.addWidget(btn_close)
        
        main_layout.addWidget(header)
        
        # --- Content (Grid) ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #161616; } QWidget { background: #161616; }")
        
        content_widget = QWidget()
        self.grid_layout = QGridLayout(content_widget)
        self.grid_layout.setContentsMargins(40, 40, 40, 40)
        self.grid_layout.setSpacing(24)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        # Populate Grid
        row, col = 0, 0
        cols_max = 4
        
        for path in self.projects:
            if not os.path.exists(path):
                continue
                
            card = ProjectCard(path)
            card.clicked.connect(self._select_card)
            card.double_clicked.connect(self._open_project)
            self.grid_layout.addWidget(card, row, col)
            self.project_cards.append(card)
            
            col += 1
            if col >= cols_max:
                col = 0
                row += 1
                
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        
        # --- Footer ---
        footer = QFrame()
        footer.setFixedHeight(50)
        footer.setStyleSheet("background-color: #1f1f1f; border-top: 1px solid #000;")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 0, 20, 0)
        
        self.btn_new = QPushButton("New Project")
        self.btn_new.setStyleSheet("""
            QPushButton { 
                background: #333; 
                color: #ddd; 
                border: 1px solid #111; 
                padding: 6px 18px; 
                border-radius: 2px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover { background: #444; color: white; }
            QPushButton:pressed { background: #222; }
        """)
        self.btn_new.clicked.connect(self._new_project)
        
        self.btn_open = QPushButton("Open")
        self.btn_open.setEnabled(False)
        self.btn_open.setStyleSheet("""
            QPushButton { 
                background: #e53935; 
                color: white; 
                border: none; 
                padding: 6px 24px; 
                border-radius: 2px; 
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover { background: #ff5252; }
            QPushButton:disabled { background: #442222; color: #777; }
        """)
        self.btn_open.clicked.connect(lambda: self._open_project(self.selected_path))
        
        footer_layout.addWidget(self.btn_new)
        footer_layout.addStretch()
        footer_layout.addWidget(self.btn_open)
        
        main_layout.addWidget(footer)
        
    def _select_card(self, path: str):
        self.selected_path = path
        for card in self.project_cards:
            card.selected = (card.path == path)
            card.update()
        self.btn_open.setEnabled(True)
        
    def _open_project(self, path: str):
        if path:
            self.project_selected.emit(path)
            self.accept()

    def _new_project(self):
        # Pour l'instant, signal vide pour indiquer "Nouveau projet" (MainWindow lancée vide)
        self.project_selected.emit("") 
        self.accept()
