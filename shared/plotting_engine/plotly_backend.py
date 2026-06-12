import os
import shutil
import tempfile
import plotly.graph_objects as go
from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl

class PlotlyWidget(QWidget):
    """
    Qt-based Plotly render widget for Mathex UI.
    Engineered to bypass Chromium cross-origin policies by using physical temp files
    and mirroring the JavaScript library into the same origin directory.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # The web view that will run the Plotly Javascript
        self.browser = QWebEngineView(self)
        self.layout.addWidget(self.browser)
        
        # Create a dedicated temp directory for Mathex plots to ensure Same-Origin Policy
        self._temp_dir = os.path.join(tempfile.gettempdir(), "mathex_plotly_env")
        os.makedirs(self._temp_dir, exist_ok=True)
        
        # Create a unique temporary file path for this specific widget instance
        self._temp_file_path = os.path.join(self._temp_dir, f"plot_{id(self)}.html")
        
        # Set a dark background by default to match Mathex
        self.setStyleSheet("background-color: #1e1e1e;")

        # Catch the application shutdown signal to destroy the WebEngine safely
        app = QApplication.instance()
        if app:
            app.aboutToQuit.connect(self._cleanup_browser)

    def _cleanup_browser(self):
        """
        Safely destroys the web engine profile and deletes the temporary HTML file.
        """
        if hasattr(self, 'browser') and self.browser is not None:
            self.browser.page().deleteLater()
            self.browser.deleteLater()
            self.browser = None
            
        if hasattr(self, '_temp_file_path') and os.path.exists(self._temp_file_path):
            try:
                os.remove(self._temp_file_path)
            except Exception:
                pass

    def render_figure(self, fig: go.Figure):
        """
        Converts a Plotly figure to HTML, saves it natively to disk, and loads it.
        """
        # Apply dark theme to match your existing UI
        fig.update_layout(template="plotly_dark", paper_bgcolor="#1e1e1e", plot_bgcolor="#1e1e1e")
        
        # 1. Ensure the local plotly.min.js exists in the temp directory alongside our HTML
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
        source_plotly = os.path.join(project_root, "resources", "plotly", "plotly.min.js")
        
        temp_plotly = os.path.join(self._temp_dir, "plotly.min.js")
        
        # Copy the JS file to the temp directory so it shares the EXACT SAME ORIGIN as the HTML
        if not os.path.exists(temp_plotly) and os.path.exists(source_plotly):
            try:
                shutil.copy2(source_plotly, temp_plotly)
            except Exception as e:
                print(f"Error mirroring Plotly JS: {e}")
        
        # 2. Tell Plotly to link using a pure relative filename
        raw_html = fig.to_html(include_plotlyjs="plotly.min.js", full_html=True)
        
        # 3. Inject Canvas2D patch to suppress Chromium performance warnings
        canvas_patch = """<script>
        const _originalGetContext = HTMLCanvasElement.prototype.getContext;
        HTMLCanvasElement.prototype.getContext = function(type, attributes) {
            if (type === '2d') {
                attributes = attributes || {};
                attributes.willReadFrequently = true;
            }
            return _originalGetContext.call(this, type, attributes);
        };
        </script>"""
        raw_html = raw_html.replace("<head>", f"<head>\n{canvas_patch}")
        
        # 4. Write to the physical temporary file in the same directory as the JS
        with open(self._temp_file_path, "w", encoding="utf-8") as f:
            f.write(raw_html)
            
        # 5. Load the file natively. This bypasses the sandbox completely.
        self.browser.load(QUrl.fromLocalFile(self._temp_file_path))
        
    def clear(self):
        """Clears the current plot."""
        if hasattr(self, 'browser') and self.browser is not None:
            self.browser.setHtml("<html><body style='background-color: #1e1e1e;'></body></html>")