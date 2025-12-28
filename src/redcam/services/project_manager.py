#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Gestionaire de projet pour RedCAM.
Gère la sauvegarde/chargement de la configuration (.json) et la liste des fichiers récents.
"""

import json
import os
from typing import Dict, List, Optional
from PyQt6.QtCore import QSettings

class ProjectManager:
    """Gère la persistance des projets et l'historique."""
    
    def __init__(self):
        self.settings = QSettings("RedCAM", "RedCAM_App")
        
    def save_project(self, filepath: str, data: Dict) -> bool:
        """
        Sauvegarde l'état actuel dans un fichier JSON.
        data: {
            'fit_path': str,
            'video_folder': str,
            'force_timestamp_sync': bool
        }
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            self._add_to_recent(filepath)
            return True
        except Exception as e:
            print(f"Erreur sauvegarde projet: {e}")
            return False

    def load_project(self, filepath: str) -> Optional[Dict]:
        """Charge un projet depuis un fichier JSON."""
        if not os.path.exists(filepath):
            return None
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._add_to_recent(filepath)
            return data
        except Exception as e:
            print(f"Erreur chargement projet: {e}")
            return None

    def get_recent_projects(self) -> List[str]:
        """Retourne la liste des projets récents (chemins absolus)."""
        # QSettings retourne parfois une string simple si 1 seul élément, ou list si plusieurs
        recents = self.settings.value("recent_projects", [], type=list)
        # Filtrer ceux qui n'existent plus
        return [p for p in recents if os.path.exists(p)]

    def _add_to_recent(self, filepath: str):
        """Ajoute un fichier à la liste des récents."""
        recents = self.get_recent_projects()
        
        # Suppr si existe déjà pour le remettre en haut
        if filepath in recents:
            recents.remove(filepath)
            
        recents.insert(0, filepath)
        
        # Max 10 projets
        recents = recents[:10]
        
        self.settings.setValue("recent_projects", recents)
