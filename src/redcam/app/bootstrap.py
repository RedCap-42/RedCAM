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
    from redcam.ui.project_menu import ProjectMenu
    from redcam.services.project_manager import ProjectManager

    # Charger les projets récents
    pm = ProjectManager()
    projects = pm.get_recent_projects()

    project_to_load = None
    
    # Si on a des projets, afficher le menu
    # (Ou toujours afficher le menu si style DaVinci)
    menu = ProjectMenu(projects)
    if menu.exec():
         # L'utilisateur a choisi un projet ou "Nouveau"
         # Note: menu.project_selected est un signal, mais exec() bloque.
         # On peut récupérer la sélection via un attribut ou connecter avant exec.
         # Simplification: ProjectMenu émet signal mais on peut aussi stocker l'état.
         pass
    else:
        # Annulé / Fermé
        return 0
        
    # Hack: récupérer le chemin via un membre public ou connexion
    # On va modifier ProjectMenu vite fait pour stocker result ou on utilise le signal
    # Le plus simple ici est de instancier MainWindow avec le path choisi.
    
    # Attends, ProjectMenu est une QDialog. 
    # Le plus propre :
    
    selected_path = menu.selected_path
    
    window = MainWindow()
    if selected_path:     
        window._load_project(selected_path)
    
    window.show()
    return app.exec()
