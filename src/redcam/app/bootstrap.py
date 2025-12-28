from __future__ import annotations

from typing import Sequence

from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtWidgets import QApplication

from redcam.app.config import APP_NAME, APP_VERSION


def run(argv: Sequence[str]) -> int:
    # QtWebEngine nécessite cette option AVANT la création de QCoreApplication.
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

    app = QApplication(list(argv))
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("RedCAM")
    app.setStyle("Fusion")

    from redcam.ui.main_window import MainWindow

    window = MainWindow()
    window.show()
    return app.exec()
