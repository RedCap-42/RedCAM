#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Widget de configuration de l'overlay style DaVinci.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, 
    QPushButton, QColorDialog, QComboBox, QLineEdit, QFrame,
    QScrollArea, QGroupBox, QInputDialog, QMessageBox, QCompleter
)
from PyQt6.QtCore import Qt, pyqtSignal, QStringListModel
from PyQt6.QtGui import QColor, QFontDatabase

from .overlay_style import OverlayStyle


class ColorButton(QPushButton):
    """Bouton de sélection de couleur (carré coloré)."""
    colorChanged = pyqtSignal(QColor)
    
    def __init__(self, color: QColor, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 24)
        self._color = color
        self._update_style()
        self.clicked.connect(self._pick_color)
        
    def _update_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color.name()};
                border: 1px solid #505050;
                border-radius: 2px;
            }}
            QPushButton:hover {{
                border: 1px solid #ffffff;
            }}
        """)
        
    def _pick_color(self):
        color = QColorDialog.getColor(self._color, self, "Choisir une couleur")
        if color.isValid():
            self.set_color(color)
            self.colorChanged.emit(color)
            
    def set_color(self, color: QColor):
        self._color = color
        self._update_style()


class MinimalSlider(QWidget):
    """Slider avec label et valeur style DaVinci."""
    valueChanged = pyqtSignal(float)
    
    def __init__(self, label: str, min_val: float, max_val: float, value: float, step: float = 1.0, suffix="", parent=None):
        super().__init__(parent)
        self.scale_factor = 100 if isinstance(step, float) else 1
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Label
        lbl = QLabel(label)
        lbl.setFixedWidth(80)
        lbl.setStyleSheet("color: #b0b0b0; font-size: 11px;")
        layout.addWidget(lbl)
        
        # Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(int(min_val * self.scale_factor))
        self.slider.setMaximum(int(max_val * self.scale_factor))
        self.slider.setValue(int(value * self.scale_factor))
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #3a3a3a;
                height: 4px;
                background: #1a1a1a;
                margin: 0px 0;
            }
            QSlider::handle:horizontal {
                background: #808080;
                border: 1px solid #808080;
                width: 10px;
                height: 10px;
                margin: -4px 0;
                border-radius: 5px;
            }
            QSlider::handle:horizontal:hover {
                background: #e0e0e0;
            }
            QSlider::sub-page:horizontal {
                background: #e04f16;
            }
        """)
        layout.addWidget(self.slider)
        
        # Value display
        self.val_label = QLabel(f"{value}{suffix}")
        self.val_label.setFixedWidth(40)
        self.val_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.val_label.setStyleSheet("color: #b0b0b0; font-size: 11px;")
        layout.addWidget(self.val_label)
        
        self.slider.valueChanged.connect(self._on_slider_changed)
        self.suffix = suffix
        self.step = step
        
    def _on_slider_changed(self, val):
        real_val = val / self.scale_factor if self.scale_factor > 1 else val
        
        # Format display
        if self.scale_factor > 1:
            self.val_label.setText(f"{real_val:.1f}{self.suffix}")
        else:
            self.val_label.setText(f"{int(real_val)}{self.suffix}")
            
        self.valueChanged.emit(real_val)
        
    def setValue(self, val):
        self.slider.setValue(int(val * self.scale_factor))


class OverlaySettingsWidget(QWidget):
    """
    Panneau de configuration complet pour l'overlay.
    """
    settingsChanged = pyqtSignal(OverlayStyle)
    presetSaveRequested = pyqtSignal(str, OverlayStyle)
    presetDeleteRequested = pyqtSignal(str)
    
    def __init__(self, style: OverlayStyle = None, presets: dict = None, parent=None):
        super().__init__(parent)
        self.style = style.copy() if style else OverlayStyle()
        self.presets = presets or {}
        
        self._init_ui()
        
    def _init_ui(self):
        self.setStyleSheet("background-color: #1a1a1a;")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # --- PRESETS SECTION ---
        presets_frame = QWidget()
        presets_layout = QHBoxLayout(presets_frame)
        presets_layout.setContentsMargins(12, 12, 12, 4)
        
        self.combo_presets = QComboBox()
        self.combo_presets.setPlaceholderText("Presets...")
        self.combo_presets.addItem("Par défaut")
        self.combo_presets.addItems(sorted(self.presets.keys()))
        self.combo_presets.currentTextChanged.connect(self._on_preset_selected)
        self.combo_presets.setStyleSheet("""
            QComboBox {
                background-color: #252525; color: #e0e0e0;
                border: 1px solid #3a3a3a; padding: 4px;
            }
        """)
        presets_layout.addWidget(self.combo_presets, 1)
        
        btn_save_preset = QPushButton("💾")
        btn_save_preset.setFixedSize(28, 28)
        btn_save_preset.setToolTip("Sauvegarder le preset")
        btn_save_preset.clicked.connect(self._save_preset)
        btn_save_preset.setStyleSheet("background-color: #252525; border: 1px solid #3a3a3a; color: #e0e0e0;")
        presets_layout.addWidget(btn_save_preset)
        
        btn_del_preset = QPushButton("🗑️")
        btn_del_preset.setFixedSize(28, 28)
        btn_del_preset.setToolTip("Supprimer le preset")
        btn_del_preset.clicked.connect(self._delete_preset)
        btn_del_preset.setStyleSheet("background-color: #252525; border: 1px solid #3a3a3a; color: #e0e0e0;")
        presets_layout.addWidget(btn_del_preset)
        
        main_layout.addWidget(presets_frame)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #1a1a1a; }")
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(16)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # 1. TRACE
        layout.addWidget(self._create_header("TRACE"))
        
        # Done Color
        row_done = QHBoxLayout()
        row_done.addWidget(QLabel("Parcouru", styleSheet="color: #b0b0b0;"))
        self.btn_trace_done = ColorButton(self.style.trace_color_done)
        self.btn_trace_done.colorChanged.connect(lambda c: self._update_param('trace_color_done', c))
        row_done.addWidget(self.btn_trace_done)
        layout.addLayout(row_done)
        
        # Remaining Color
        row_rem = QHBoxLayout()
        row_rem.addWidget(QLabel("Restant", styleSheet="color: #b0b0b0;"))
        self.btn_trace_rem = ColorButton(self.style.trace_color_remaining)
        self.btn_trace_rem.colorChanged.connect(lambda c: self._update_param('trace_color_remaining', c))
        row_rem.addWidget(self.btn_trace_rem)
        layout.addLayout(row_rem)
        
        # Width
        self.sl_width = MinimalSlider("Épaisseur", 1, 20, self.style.trace_width, step=1, suffix="px")
        self.sl_width.valueChanged.connect(lambda v: self._update_param('trace_width', int(v)))
        layout.addWidget(self.sl_width)
        
        # Style Box for remaining (Solid / Dash / Dot)
        row_style = QHBoxLayout()
        row_style.addWidget(QLabel("Style Restant", styleSheet="color: #b0b0b0;"))
        self.combo_style = QComboBox()
        self.combo_style.addItems(["Solid", "Dash", "Dot"])
        self.combo_style.setCurrentIndex(1) # Dash default
        self.combo_style.currentIndexChanged.connect(self._on_style_changed)
        self.combo_style.setStyleSheet("""
            QComboBox {
                background-color: #252525; color: #e0e0e0;
                border: 1px solid #3a3a3a; padding: 4px;
            }
        """)
        row_style.addWidget(self.combo_style)
        layout.addLayout(row_style)
        
        # 2. MARKER & GLOW
        layout.addWidget(self._create_header("MARQUEUR & GLOW"))
        
        # Marker Color
        row_mark = QHBoxLayout()
        row_mark.addWidget(QLabel("Couleur Point", styleSheet="color: #b0b0b0;"))
        self.btn_marker = ColorButton(self.style.marker_color)
        self.btn_marker.colorChanged.connect(lambda c: self._update_param('marker_color', c))
        row_mark.addWidget(self.btn_marker)
        layout.addLayout(row_mark)
        
        # Glow Color
        row_glow = QHBoxLayout()
        row_glow.addWidget(QLabel("Couleur Glow", styleSheet="color: #b0b0b0;"))
        self.btn_glow = ColorButton(self.style.glow_color)
        self.btn_glow.colorChanged.connect(lambda c: self._update_param('glow_color', c))
        row_glow.addWidget(self.btn_glow)
        layout.addLayout(row_glow)
        
        # Size & Radius
        self.sl_size = MinimalSlider("Taille Point", 4, 30, self.style.marker_size, step=1)
        self.sl_size.valueChanged.connect(lambda v: self._update_param('marker_size', int(v)))
        layout.addWidget(self.sl_size)
        
        self.sl_glow = MinimalSlider("Rayon Glow", 0, 100, self.style.glow_radius, step=1)
        self.sl_glow.valueChanged.connect(lambda v: self._update_param('glow_radius', int(v)))
        layout.addWidget(self.sl_glow)
        
        # 3. TEXTE
        layout.addWidget(self._create_header("TEXTE"))
        
        # Font
        self.combo_font = QComboBox()
        self.combo_font.setEditable(True)  # Enable search
        
        # Load all system fonts (static method in PyQt6)
        all_fonts = QFontDatabase.families()
        self.combo_font.addItems(all_fonts)
        
        # Setup completer for search
        completer = QCompleter(all_fonts)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.combo_font.setCompleter(completer)
        
        self.combo_font.setCurrentText(self.style.text_font_family)
        self.combo_font.currentTextChanged.connect(lambda f: self._update_param('text_font_family', f))
        self.combo_font.setStyleSheet(self.combo_style.styleSheet())
        layout.addWidget(self.combo_font)
        
        # Size
        self.sl_font_size = MinimalSlider("Taille", 8, 72, self.style.text_font_size, step=1)
        self.sl_font_size.valueChanged.connect(lambda v: self._update_param('text_font_size', int(v)))
        layout.addWidget(self.sl_font_size)
        
        # Extra text
        self.txt_extra = QLineEdit()
        self.txt_extra.setPlaceholderText("Texte additionnel (ex: 100KM)")
        self.txt_extra.textChanged.connect(lambda t: self._update_param('extra_text', t))
        self.txt_extra.setStyleSheet("""
            QLineEdit {
                background-color: #252525; color: #e0e0e0;
                border: 1px solid #3a3a3a; padding: 4px; border-radius: 2px;
            }
        """)
        layout.addWidget(self.txt_extra)
        
        # 4. 3D TRANSFORM
        layout.addWidget(self._create_header("PERSPECTIVE 3D"))
        
        self.sl_rot_x = MinimalSlider("Inclinaison X", 0, 85, self.style.rotation_x, step=1.0, suffix="°")
        self.sl_rot_x.valueChanged.connect(lambda v: self._update_param('rotation_x', v))
        layout.addWidget(self.sl_rot_x)
        
        self.sl_rot_z = MinimalSlider("Rotation Z", -180, 180, self.style.rotation_z, step=1.0, suffix="°")
        self.sl_rot_z.valueChanged.connect(lambda v: self._update_param('rotation_z', v))
        layout.addWidget(self.sl_rot_z)
        
        layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)
        
    def _create_header(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("""
            QLabel {
                color: #e04f16;
                font-weight: bold;
                font-size: 10px;
                letter-spacing: 1px;
                border-bottom: 1px solid #3a3a3a;
                padding-bottom: 4px;
                margin-top: 8px;
            }
        """)
        return lbl
        
    def _on_style_changed(self, index):
        styles = [Qt.PenStyle.SolidLine, Qt.PenStyle.DashLine, Qt.PenStyle.DotLine]
        self._update_param('trace_style_remaining', styles[index])
        
    def _update_param(self, attr, value):
        setattr(self.style, attr, value)
        self.settingsChanged.emit(self.style)
        
    def _save_preset(self):
        name, ok = QInputDialog.getText(self, "Sauvegarder Preset", "Nom du preset:")
        if ok and name:
            self.presets[name] = self.style.to_dict()
            self.presetSaveRequested.emit(name, self.style)
            
            # Refresh combo
            current = self.combo_presets.currentText()
            self.combo_presets.blockSignals(True)
            self.combo_presets.clear()
            self.combo_presets.addItem("Par défaut")
            self.combo_presets.addItems(sorted(self.presets.keys()))
            self.combo_presets.setCurrentText(name) # Select new preset
            self.combo_presets.blockSignals(False)
            
    def _delete_preset(self):
        name = self.combo_presets.currentText()
        if name == "Par défaut":
            return
            
        confirm = QMessageBox.question(self, "Confirmer suppression", f"Supprimer le preset '{name}' ?")
        if confirm == QMessageBox.StandardButton.Yes:
            del self.presets[name]
            self.presetDeleteRequested.emit(name)
            
            # Refresh combo
            self.combo_presets.blockSignals(True)
            self.combo_presets.clear()
            self.combo_presets.addItem("Par défaut")
            self.combo_presets.addItems(sorted(self.presets.keys()))
            self.combo_presets.setCurrentIndex(0)
            self.combo_presets.blockSignals(False)
            
    def _on_preset_selected(self, name):
        if not name: return
        
        if name == "Par défaut":
            # Reset would require stored default, for now do nothing or reset to hardcoded defaults
            pass
        elif name in self.presets:
            new_style = OverlayStyle.from_dict(self.presets[name])
            self.set_style(new_style)
            
    def set_style(self, style: OverlayStyle):
        """Met à jour tous les controles avec le nouveau style."""
        self.style = style
        self.blockSignals(True)
        
        # Update UI controls... (simplified for brevity, should update all inputs)
        # Mais comme c'est long, on va juste émettre le signal pour l'instant
        # Une vraie implémentation mettrait à jour tous les setValue/setCurrentText
        
        # Couleurs
        self.btn_trace_done.set_color(style.trace_color_done)
        self.btn_trace_rem.set_color(style.trace_color_remaining)
        self.btn_marker.set_color(style.marker_color)
        self.btn_glow.set_color(style.glow_color)
        
        # Sliders
        self.sl_width.setValue(style.trace_width)
        # ... autres sliders
        self.sl_size.setValue(style.marker_size)
        self.sl_glow.setValue(style.glow_radius)
        self.sl_font_size.setValue(style.text_font_size)
        self.sl_rot_x.setValue(style.rotation_x)
        self.sl_rot_z.setValue(style.rotation_z)
        
        # Combo
        self.combo_font.setCurrentText(style.text_font_family)
        idx = [Qt.PenStyle.SolidLine, Qt.PenStyle.DashLine, Qt.PenStyle.DotLine].index(style.trace_style_remaining)
        self.combo_style.setCurrentIndex(idx)
        self.txt_extra.setText(style.extra_text)
        
        self.blockSignals(False)
        self.settingsChanged.emit(self.style)

    def update_rotation(self, x, z):
        """Met à jour les sliders de rotation (depuis la souris)."""
        self.sl_rot_x.blockSignals(True)
        self.sl_rot_z.blockSignals(True)
        
        self.sl_rot_x.setValue(x)
        self.sl_rot_z.setValue(z)
        
        self.style.rotation_x = x
        self.style.rotation_z = z
        
        self.sl_rot_x.blockSignals(False)
        self.sl_rot_z.blockSignals(False)
