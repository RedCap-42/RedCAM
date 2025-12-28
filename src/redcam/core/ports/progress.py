from __future__ import annotations

from typing import Protocol

from redcam.core.models.sync_models import ProgressEvent


class ProgressReporter(Protocol):
    def report(self, event: ProgressEvent) -> None: ...
