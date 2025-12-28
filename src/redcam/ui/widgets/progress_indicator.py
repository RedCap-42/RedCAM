#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Indicateur de progression pour RedCAM.
Affiche une barre de progression et un message de statut.
"""

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, 
    QProgressBar, QLabel
)
from PyQt6.QtCore import Qt


class ProgressIndicator(QWidget):
    """
    Widget affichant une barre de progression et un message de statut.
    """
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialise le widget."""
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Configure l'interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        
        # Label de statut
        self.lbl_status = QLabel("Prêt")
        self.lbl_status.setMinimumWidth(200)
        layout.addWidget(self.lbl_status)
        
        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setMaximumWidth(200)
        layout.addWidget(self.progress_bar)
        
        # Masquer par défaut
        self.progress_bar.hide()
    
    def set_status(self, message: str) -> None:
        """
        Met à jour le message de statut.
        
        Args:
            message: Message à afficher
        """
        self.lbl_status.setText(message)
    
    def set_progress(self, current: int, total: int) -> None:
        """
        Met à jour la progression.
        
        Args:
            current: Valeur actuelle
            total: Valeur totale
        """
        if total > 0:
            percent = int((current / total) * 100)
            self.progress_bar.setValue(percent)
            self.progress_bar.show()
        else:
            self.progress_bar.hide()
    
    def start_progress(self) -> None:
        """Démarre l'affichage de la progression."""
        self.progress_bar.setValue(0)
        self.progress_bar.show()
    
    def stop_progress(self) -> None:
        """Arrête l'affichage de la progression."""
        self.progress_bar.setValue(100)
        # Cacher après un court délai
        self.progress_bar.hide()
    
    def set_indeterminate(self, indeterminate: bool) -> None:
        """
        Active/désactive le mode indéterminé.
        
        Args:
            indeterminate: True pour mode indéterminé
        """
        if indeterminate:
            self.progress_bar.setMinimum(0)
            self.progress_bar.setMaximum(0)  # Mode indéterminé
            self.progress_bar.show()
        else:
            self.progress_bar.setMinimum(0)
            self.progress_bar.setMaximum(100)
    
    def reset(self) -> None:
        """Réinitialise le widget."""
        self.lbl_status.setText("Prêt")
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
