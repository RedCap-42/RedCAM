from PyQt6.QtWidgets import QDoubleSpinBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor

class ScrubberInput(QDoubleSpinBox):
    """
    Champ numérique style 'Scrubber' (DaVinci/Blender).
    Permet de glisser la souris pour changer la valeur.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        self.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #2A2A2A;
                color: #E0E0E0;
                border: 1px solid #3E3E3E;
                border-radius: 3px;
                padding: 4px;
                selection-background-color: #E04F16;
                font-weight: bold;
            }
            QDoubleSpinBox:hover {
                border-color: #E04F16;
                background-color: #333333;
            }
        """)
        self.last_x = 0
        self.dragging = False
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.last_x = event.globalPosition().x()
            # On cache le curseur pour l'immersion, ou on le laisse en SizeHor
            # self.setCursor(Qt.CursorShape.BlankCursor) 
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging:
            delta = event.globalPosition().x() - self.last_x
            self.last_x = event.globalPosition().x()
            
            # Ajuster la sensibilité (shift pour précision)
            step = self.singleStep()
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                step /= 10
                
            self.setValue(self.value() + delta * step)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.dragging:
            self.dragging = False
            # self.setCursor(Qt.CursorShape.SizeHorCursor)
        super().mouseReleaseEvent(event)
