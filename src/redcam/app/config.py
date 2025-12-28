from __future__ import annotations

import os
import sys
from typing import List


def is_frozen() -> bool:
    """True si l'application tourne en mode PyInstaller."""
    return getattr(sys, "frozen", False)


def get_base_path() -> str:
    """Chemin de base (PyInstaller: _MEIPASS, sinon dossier projet)."""
    if is_frozen():
        return sys._MEIPASS  # type: ignore[attr-defined]
    # En dev: racine du repo (..
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def resource_path(relative_path: str) -> str:
    """Chemin absolu vers une ressource (dev/frozen)."""
    return os.path.join(get_base_path(), relative_path)


VIDEO_EXTENSIONS: List[str] = [".mp4", ".MP4"]
FIT_EXTENSION: str = ".fit"

DEFAULT_TIMEZONE: str = "Europe/Paris"
DOP_LIMIT: int = 2000

APP_NAME: str = "RedCAM"
APP_VERSION: str = "1.0.0"
