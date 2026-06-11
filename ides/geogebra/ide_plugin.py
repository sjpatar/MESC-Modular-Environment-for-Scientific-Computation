from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from app_platform.core.plugin_manager import StemTool
from ides.geogebra.ui.app import GeoGebraApp

class GeogebraTool(StemTool):
    def __init__(self):
        self._app_instance = None
        self._container = None

    def get_name(self) -> str:
        return "GeoGebra"

    def get_icon_name(self) -> str:
        return "G"

    def get_widget(self) -> QWidget:
        if self._container is None:
            self._app_instance = GeoGebraApp()
            self._app_instance.setWindowFlags(Qt.Widget)
            self._container = self._app_instance
        return self._container

    def on_activate(self):
        pass

    def on_deactivate(self):
        pass