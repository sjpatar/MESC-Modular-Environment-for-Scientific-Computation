# tests/test_debug_plotly.py
import os
import pytest
import plotly.graph_objects as go
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtCore import QEventLoop, QTimer

# Import your widget
from shared.plotting_engine.plotly_backend import PlotlyWidget

class DebugWebPage(QWebEnginePage):
    """
    A custom QWebEnginePage that intercepts JavaScript errors and prints 
    them to the Python console so we can see why the plot is failing.
    """
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        print(f"\n[JS CONSOLE] Line {lineNumber}: {message}\n")


@pytest.fixture(scope="session")
def qapp():
    """Ensures a QApplication exists for the UI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


# Removed qtbot from the arguments
def test_plotly_3d_render_no_crash(qapp):
    """
    Tests if the PlotlyWidget can successfully load the local JS file
    and render a 3D figure without throwing JavaScript reference errors.
    """
    widget = PlotlyWidget()
    widget.show() # Used standard .show() instead of qtbot

    # Attach the custom page to catch JS errors
    debug_page = DebugWebPage()
    widget.browser.setPage(debug_page)

    # 1. Create a minimal 3D plot
    fig = go.Figure(data=[go.Scatter3d(
        x=[1, 2, 3], y=[1, 2, 3], z=[1, 2, 3],
        mode='markers',
        marker=dict(size=5, color='red')
    )])

    # 2. Setup an event loop to wait for the HTML to finish loading
    load_loop = QEventLoop()
    widget.browser.loadFinished.connect(load_loop.quit)

    # 3. Trigger the render
    print("\nRendering figure...")
    widget.render_figure(fig)

    # Wait for the page to finish loading (timeout after 5 seconds)
    QTimer.singleShot(5000, load_loop.quit)
    load_loop.exec()

    # 4. Inject JavaScript to explicitly check if 'Plotly' exists
    js_check_code = "typeof Plotly !== 'undefined';"
    plotly_is_defined = False
    
    js_loop = QEventLoop()

    def js_callback(result):
        nonlocal plotly_is_defined
        plotly_is_defined = result
        js_loop.quit()

    widget.browser.page().runJavaScript(js_check_code, 0, js_callback)
    
    # Wait for JS execution (timeout after 2 seconds)
    QTimer.singleShot(2000, js_loop.quit)
    js_loop.exec()

    # 5. Assertions
    assert plotly_is_defined, "Plotly library failed to load in the WebEngineView! Check your path to plotly.min.js."