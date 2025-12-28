"""Styles QSS pour RedCAM.
Palette sombre inspirée de DaVinci Resolve avec accents bleus/verts.
"""

from PyQt6.QtGui import QColor, QPalette

# Palette de couleurs
COLOR_BACKGROUND = "#1e1e1e"
COLOR_PANEL = "#252525"
COLOR_SURFACE = "#2d2d2d"
COLOR_ACCENT = "#2a4d69"  # Bleu Resolve-like
COLOR_ACCENT_SUCCESS = "#4caf50"  # Vert actions positives
COLOR_TEXT_PRIMARY = "#e0e0e0"
COLOR_TEXT_SECONDARY = "#b0b0b0"
COLOR_BORDER = "#3a3a3a"
COLOR_HOVER = "#333333"
COLOR_PRESSED = "#1a1a1a"
COLOR_INPUT_BG = "#181818"
COLOR_SHADOW = "#000000"

WINDOW_STYLE = f"""
QMainWindow {{
    background-color: {COLOR_BACKGROUND};
    color: {COLOR_TEXT_PRIMARY};
}}
QWidget {{
    background-color: {COLOR_BACKGROUND};
    color: {COLOR_TEXT_PRIMARY};
    font-family: 'Segoe UI', 'Roboto', 'Inter', sans-serif;
    font-size: 13px;
}}
QDockWidget {{
    titlebar-close-icon: url(close.png);
    titlebar-normal-icon: url(undock.png);
}}
QDockWidget::title {{
    text-align: left;
    background: {COLOR_PANEL};
    padding-left: 12px;
    padding-top: 8px;
    padding-bottom: 8px;
    font-weight: bold;
    letter-spacing: 0.2px;
    border-bottom: 1px solid {COLOR_BORDER};
}}
QDockWidget::close-button, QDockWidget::float-button {{
    border: none;
    background: transparent;
    padding: 0px;
    icon-size: 14px;
}}
QDockWidget::close-button:hover, QDockWidget::float-button:hover {{
    background: {COLOR_HOVER};
    border-radius: 0px;
}}
QSplitter::handle {{
    background-color: {COLOR_BACKGROUND};
    border: 1px solid {COLOR_BORDER};
}}
QScrollBar:vertical {{
    border: none;
    background: {COLOR_BACKGROUND};
    width: 12px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: #4a4a4a;
    min-height: 20px;
    border-radius: 0px;
    margin: 2px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
"""

BUTTON_STYLE = f"""
QPushButton {{
    background-color: {COLOR_ACCENT};
    color: white;
    border: 1px solid {COLOR_BORDER};
    border-radius: 0px;
    padding: 10px 18px;
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 0.2px;
}}
QPushButton:hover {{
    background-color: #3b6d93;
    border-color: #4b7aa5;
}}
QPushButton:pressed {{
    background-color: #203548;
}}
QPushButton:disabled {{
    background-color: {COLOR_PANEL};
    color: {COLOR_TEXT_SECONDARY};
    border: 1px solid {COLOR_BORDER};
}}
"""

BUTTON_SECONDARY_STYLE = f"""
QPushButton {{
    background-color: {COLOR_PANEL};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 0px;
    padding: 8px 14px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: {COLOR_HOVER};
    border-color: #5a5a5a;
}}
QPushButton:pressed {{
    background-color: {COLOR_PRESSED};
}}
"""

GROUPBOX_STYLE = f"""
QGroupBox {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 0px;
    margin-top: 16px;
    padding-top: 18px;
    padding-bottom: 14px;
    padding-left: 14px;
    padding-right: 14px;
    font-weight: 700;
    letter-spacing: 0.2px;
    color: {COLOR_TEXT_SECONDARY};
    background-color: {COLOR_PANEL};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
    left: 10px;
    color: {COLOR_ACCENT};
    background-color: {COLOR_PANEL};
}}
"""

LABEL_STYLE = f"""
QLabel {{
    color: {COLOR_TEXT_PRIMARY};
    background-color: transparent;
    font-weight: 500;
}}
"""

LABEL_TITLE_STYLE = f"""
QLabel {{
    font-size: 14px;
    font-weight: 800;
    color: {COLOR_TEXT_PRIMARY};
    padding-bottom: 8px;
    text-transform: uppercase;
    background-color: transparent;
}}
"""

PROGRESS_BAR_STYLE = f"""
QProgressBar {{
    border: none;
    border-radius: 4px;
    text-align: center;
    background-color: {COLOR_INPUT_BG};
    color: white;
    height: 8px;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLOR_ACCENT}, stop:1 {COLOR_ACCENT_SUCCESS});
    border-radius: 4px;
}}
"""

TITLE_BAR_STYLE = f"""
QWidget {{
    background-color: #161616;
    border-bottom: 1px solid {COLOR_BORDER};
}}
QPushButton {{
    background-color: #1f1f1f;
    border: 1px solid #2d2d2d;
    color: {COLOR_TEXT_SECONDARY};
    font-weight: 600;
    font-size: 12px;
    padding: 6px 10px;
    border-radius: 6px;
}}
QPushButton:hover {{
    background-color: #2a2a2a;
    color: white;
    border-color: #3a3a3a;
}}
QPushButton#close_btn:hover {{
    background-color: #b3261e;
    border-color: #b3261e;
}}
QToolButton {{
    background-color: transparent;
    border: 1px solid {COLOR_BORDER};
    color: {COLOR_TEXT_PRIMARY};
    padding: 4px 8px;
    border-radius: 6px;
}}
QToolButton:hover {{
    background-color: #242424;
}}
"""

CHECKBOX_STYLE = f"""
QCheckBox {{
    color: {COLOR_TEXT_PRIMARY};
    spacing: 8px;
    background-color: transparent;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1px solid {COLOR_BORDER};
    border-radius: 3px;
    background: {COLOR_INPUT_BG};
}}
QCheckBox::indicator:checked {{
    background: {COLOR_ACCENT};
    border-color: {COLOR_ACCENT};
}}
"""

COMBO_STYLE = f"""
QComboBox {{
    background-color: {COLOR_INPUT_BG};
    color: white;
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 8px 12px;
    min-height: 24px;
}}
QComboBox:hover {{
    border-color: #666666;
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #AAAAAA;
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLOR_PANEL};
    color: white;
    selection-background-color: {COLOR_ACCENT};
    border: 1px solid {COLOR_BORDER};
    outline: 0px;
}}
"""

