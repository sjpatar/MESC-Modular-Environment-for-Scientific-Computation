# shared/plotting_engine/plotly_backend.py
import plotly.graph_objects as go
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView

class PlotlyWidget(QWidget):
    """
    Qt-based Plotly render widget for Mathex UI.
    Engineered for interactive HTML rendering.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # The web view that will run the Plotly Javascript
        self.browser = QWebEngineView(self)
        self.layout.addWidget(self.browser)
        
        # Set a dark background by default to match Mathex
        self.setStyleSheet("background-color: #1e1e1e;")

    def render_figure(self, fig: go.Figure):
        """
        Converts a Plotly figure to HTML and renders it in the browser.
        """
        # Apply dark theme to match your existing UI
        fig.update_layout(template="plotly_dark", paper_bgcolor="#1e1e1e", plot_bgcolor="#1e1e1e")
        
        raw_html = fig.to_html(include_plotlyjs=True, full_html='cdn')
        self.browser.setHtml(raw_html)
        
    def clear(self):
        """Clears the current plot."""
        self.browser.setHtml("<html><body style='background-color: #1e1e1e;'></body></html>")
