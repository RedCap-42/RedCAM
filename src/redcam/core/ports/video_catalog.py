from __future__ import annotations

from typing import Protocol, Sequence


class VideoCatalogPort(Protocol):
    def list_videos(self, folder_path: str, extensions: Sequence[str]) -> list[str]: ...
