from __future__ import annotations

import os
from typing import Sequence

from redcam.core.ports.video_catalog import VideoCatalogPort


class OSVideoCatalog(VideoCatalogPort):
    def list_videos(self, folder_path: str, extensions: Sequence[str]) -> list[str]:
        video_files: list[str] = []
        try:
            for filename in os.listdir(folder_path):
                _, ext = os.path.splitext(filename)
                if ext in extensions:
                    video_files.append(os.path.join(folder_path, filename))
        except FileNotFoundError:
            return []

        return sorted(video_files)
