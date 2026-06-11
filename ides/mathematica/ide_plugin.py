from PySide6.QtWidgets import QWidget
from app_platform.core.plugin_manager import StemTool
from .ui.app import MathematicaApp

class MathematicaTool(StemTool):
    def __init__(self):
        self._app = None

    def get_name(self) -> str:
        return "Mathematica"

    def get_icon_name(self) -> str:
        return "MA"

    def get_widget(self) -> QWidget:
        if self._app is None:
            self._app = MathematicaApp()
        return self._app

    def on_activate(self):
        if self._app:
            self._app.setFocus()  # Fixed: set_focus() -> setFocus()