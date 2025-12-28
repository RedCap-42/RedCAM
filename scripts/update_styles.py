# Styles QSS pour RedCAM
# Thème sombre professionnel "Darkroom" inspiré de DaVinci Resolve

from PyQt6.QtGui import QColor, QPalette
from pathlib import Path

# Palette de couleurs
COLOR_BACKGROUND = "#121212"
COLOR_PANEL = "#2A2A2A"
COLOR_ACCENT = "#E04F16"  # Orange RedCAM
COLOR_TEXT_PRIMARY = "#E0E0E0"
COLOR_TEXT_SECONDARY = "#AAAAAA"
COLOR_BORDER = "#3E3E3E"
COLOR_HOVER = "#3E3E3E"
COLOR_PRESSED = "#1A1A1A"

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
    padding-left: 5px;
    padding-top: 4px;
    padding-bottom: 4px;
    font-weight: bold;
    border-bottom: 1px solid {COLOR_BORDER};
}}
QDockWidget::close-button, QDockWidget::float-button {{
    border: 1px solid transparent;
    background: transparent;
    padding: 0px;
}}
QDockWidget::close-button:hover, QDockWidget::float-button:hover {{
    background: {COLOR_HOVER};
}}
QSplitter::handle {{
    background-color: {COLOR_BACKGROUND};
    border: 1px solid {COLOR_BORDER};
}}
QScrollBar:vertical {{
    border: none;
    background: {COLOR_BACKGROUND};
    width: 10px;
    margin: 0px 0px 0px 0px;
}}
QScrollBar::handle:vertical {{
    background: #444444;
    min-height: 20px;
    border-radius: 5px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
"""

BUTTON_STYLE = f"""
QPushButton {{
    background-color: {COLOR_ACCENT};
    color: white;
    border: none;
    border-radius: 3px;
    padding: 6px 12px;
    font-weight: bold;
    text-transform: uppercase;
    font-size: 12px;
}}
QPushButton:hover {{
    background-color: #F4511E;
}}
QPushButton:pressed {{
    background-color: #BF360C;
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
    border-radius: 3px;
    padding: 6px 12px;
}}
QPushButton:hover {{
    background-color: {COLOR_HOVER};
    border-color: #666666;
}}
QPushButton:pressed {{
    background-color: {COLOR_PRESSED};
}}
"""

GROUPBOX_STYLE = f"""
QGroupBox {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    margin-top: 20px;
    padding-top: 10px;
    font-weight: bold;
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
}}
"""

LABEL_TITLE_STYLE = f"""
QLabel {{
    font-size: 14px;
    font-weight: bold;
    color: {COLOR_TEXT_PRIMARY};
    padding-bottom: 5px;
    text-transform: uppercase;
}}
"""

PROGRESS_BAR_STYLE = f"""
QProgressBar {{
    border: none;
    border-radius: 2px;
    text-align: center;
    background-color: {COLOR_PANEL};
    color: white;
}}
QProgressBar::chunk {{
    background-color: {COLOR_ACCENT};
    border-radius: 2px;
}}
"""

TITLE_BAR_STYLE = f"""
QWidget {{
    background-color: {COLOR_BACKGROUND};
}}
QLabel {{
    color: {COLOR_TEXT_SECONDARY};
    font-weight: bold;
}}
QPushButton {{
    background-color: transparent;
    border: none;
    color: {COLOR_TEXT_SECONDARY};
    font-weight: bold;
    font-size: 14px;
}}
QPushButton:hover {{
    background-color: {COLOR_HOVER};
    color: white;
}}
QPushButton#close_btn:hover {{
    background-color: #D32F2F;
}}
"""

repo_root = Path(__file__).resolve().parents[1]
out_path = repo_root / "src" / "redcam" / "ui" / "theme" / "styles.py"

with out_path.open('w', encoding='utf-8') as f:
    f.write(Path(__file__).read_text(encoding='utf-8').split('TITLE_BAR_STYLE = f"""')[0])
    f.write(f'TITLE_BAR_STYLE = f"""{TITLE_BAR_STYLE}"""')

