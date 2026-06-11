# mathex/modules/matlab.py
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from app_platform.core.plugin_manager import StemTool
from ides.mathex.ui.app import MathexApp

class MatlabTool(StemTool):
    def __init__(self):
        self._app_instance = None
        self._container = None

    def get_name(self) -> str:
        return "Mathex"

    def get_icon_name(self) -> str:
        return "M"

    def get_widget(self) -> QWidget:
        if self._container is None:
            # 1. Initialize the existing app
            self._app_instance = MathexApp()
            
            # 2. [CRITICAL FIX] Force it to behave like a child widget, not a window
            self._app_instance.setWindowFlags(Qt.Widget)
            
            # 3. Use the app itself as the container
            self._container = self._app_instance
            
        return self._container

    def on_activate(self):
        print("Mathex Activated")

    def on_deactivate(self):
        print("Mathex Deactivated")