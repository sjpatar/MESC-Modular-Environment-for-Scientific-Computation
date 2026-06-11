from abc import ABC, abstractmethod
from PySide6.QtWidgets import QWidget

class StemTool(ABC):
    """
    The base contract that all Mathex tools must follow.
    """
    
    @abstractmethod
    def get_name(self) -> str:
        """Return the display name of the tool (e.g., 'GeoGebra')."""
        pass

    @abstractmethod
    def get_widget(self) -> QWidget:
        """Return the main UI widget for this tool."""
        pass

    def get_icon_name(self) -> str:
        """
        Return the short text for the sidebar button (e.g. 'MA', 'M').
        Used by StemShell to create the menu button.
        """
        return "🔧"

    def on_activate(self):
        """Optional hook called when the user switches to this tool."""
        pass

    def on_deactivate(self):
        """Optional hook called when the user switches away from this tool."""
        pass