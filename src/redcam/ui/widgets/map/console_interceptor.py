#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWebEngineCore import QWebEnginePage

class ConsoleInterceptor(QWebEnginePage):
    """Intercepte les messages console JS pour la communication."""
    
    def __init__(self, parent_widget):
        super().__init__(parent_widget)
        self.parent_widget = parent_widget
        
    def javaScriptConsoleMessage(self, level, message, line, source_id):
        # Interception du clic vidéo
        if message.startswith("VIDEO:"):
            video_path = message[6:]
            self.parent_widget.video_clicked.emit(video_path)
            return
        
        # Interception de l'édition
        if message.startswith("EDIT:"):
            video_path = message[5:]
            # Suppose parent_widget has this method
            if hasattr(self.parent_widget, 'open_edit_dialog'):
                self.parent_widget.open_edit_dialog(video_path)
            return
            
        super().javaScriptConsoleMessage(level, message, line, source_id)
