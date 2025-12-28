#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Barre d'onglets de workspace style DaVinci Resolve.
Affichée en bas de l'écran pour basculer entre les différentes vues.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QButtonGroup, QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class WorkspaceTabBar(QWidget):
    """
    Barre d'onglets horizontale en bas de l'écran.
    Style DaVinci Resolve - minimaliste et professionnel.
    """
    workspace_changed = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self.buttons: list[QPushButton] = []
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialise l'interface."""
        self.setStyleSheet("""
            WorkspaceTabBar {
                background-color: #1a1a1a;
                border-top: 1px solid #0a0a0a;
            }
        """)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Espace à gauche
        self.layout.addStretch()
        
        # Les onglets seront ajoutés ici
        
        # Espace à droite
        self.layout.addStretch()
    
    def add_workspace(self, name: str, icon: str = None) -> int:
        """
        Ajoute un onglet de workspace.
        """
        btn = QPushButton(name)
        btn.setCheckable(True)
        btn.setFixedHeight(28)
        btn.setMinimumWidth(80)
        btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        
        # Style minimaliste
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #606060;
                border: none;
                border-left: 1px solid #0a0a0a;
                padding: 4px 24px;
                font-size: 11px;
                font-weight: 500;
                letter-spacing: 0.3px;
            }
            QPushButton:first-child {
                border-left: none;
            }
            QPushButton:hover {
                color: #909090;
                background-color: #1f1f1f;
            }
            QPushButton:checked {
                color: #e0e0e0;
                background-color: #252525;
            }
        """)
        
        index = len(self.buttons)
        self.buttons.append(btn)
        self.button_group.addButton(btn, index)
        
        insert_pos = self.layout.count() - 1
        self.layout.insertWidget(insert_pos, btn)
        
        btn.clicked.connect(lambda: self._on_button_clicked(index))
        
        if index == 0:
            btn.setChecked(True)
        
        return index
    
    def _on_button_clicked(self, index: int):
        self.workspace_changed.emit(index)
    
    def set_current_index(self, index: int):
        if 0 <= index < len(self.buttons):
            self.buttons[index].setChecked(True)
    
    def current_index(self) -> int:
        return self.button_group.checkedId()
