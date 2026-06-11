# mathex/ui/editor/gutter.py
from PySide6.QtWidgets import QWidget


class LineNumberArea(QWidget):
    """
    Side area used only to draw line numbers
    """
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor

    def sizeHint(self):
        return self.codeEditor.line_number_area_width()

    def paintEvent(self, event):
        self.codeEditor.line_number_area_paint_event(event)
