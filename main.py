#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RedCAM - GPS Video Synchronization Tool
Point d'entrée principal de l'application.

Application PyQt6 pour synchroniser les traces GPS Garmin (.fit) 
avec les vidéos GoPro et les afficher sur une carte interactive.
"""

import sys
import os


def _ensure_src_on_path() -> None:
    """Permet d'exécuter `python main.py` sans installer le package."""
    if getattr(sys, "frozen", False):
        return

    repo_root = os.path.dirname(os.path.abspath(__file__))
    src_path = os.path.join(repo_root, "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


def main() -> int:
    """
    Point d'entrée principal de l'application.
    
    Returns:
        Code de retour de l'application
    """
    _ensure_src_on_path()
    from redcam.app.bootstrap import run

    return run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
