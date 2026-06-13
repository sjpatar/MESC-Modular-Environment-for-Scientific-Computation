# mathex/ui/plotdock.py
"""
PlotDock - container for the Mathex plotting surface.

Improvements in this version:
  * Automatically registers the internal PlotWidget with plot_manager so
    the kernel/session finds the widget even if the UI order varies.
  * Re-registers the widget on showEvent (prevents lost registration when docks
    are hidden/restored).
  * Ensures the canvas container and widget use expanding size policies so the
    Matplotlib canvas receives a non-zero geometry.
  * Small defensive guards to avoid importing plot_manager at module import time
    (avoids circular import during app/module initialization).
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QSizePolicy, QStackedWidget
)
from PySide6.QtCore import Qt, QEvent, QTimer, Signal

# Import the backend widget (Matplotlib canvas)
from shared.plotting_engine.mpl_backend import PlotWidget


class PlotDock(QWidget):
    """
    Professional container for Matplotlib figures.

    Structure:
      [ optional top bar ]
      [ canvas container -> PlotWidget ]
    """
    plot_selection_changed = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)

        # 1. Main Layout (zero margins for edge-to-edge look)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # 2. Top Bar (placeholder for toolbar/controls)
        self.top_bar = QFrame()
        self.top_bar.setFixedHeight(0)  # hidden by default
        self.top_bar.setStyleSheet("background: #252526; border-bottom: 1px solid #333;")
        self.layout.addWidget(self.top_bar)

        # 3. Canvas container (ensures canvas gets expanding geometry)
        self.canvas_container = QFrame()
        self.canvas_container.setStyleSheet("background-color: #1e1e1e;")
        self.canvas_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Layout for the canvas container
        self.canvas_layout = QVBoxLayout(self.canvas_container)
        self.canvas_layout.setContentsMargins(0, 0, 0, 0)
        self.canvas_layout.setSpacing(0)

        self.backend_stack = QStackedWidget(self.canvas_container)
        self.canvas_layout.addWidget(self.backend_stack)

        # 4. The actual Matplotlib widget
        self.canvas_widget = PlotWidget(parent=self.canvas_container)
        self.plotly_widget = None
        self._active_backend = "mpl"
        # ensure the widget will expand to fill the container
        self.canvas_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.backend_stack.addWidget(self.canvas_widget)

        # Add container to main layout
        self.layout.addWidget(self.canvas_container)

        # Attempt to register the widget with plot_manager now (defensive / non-fatal)
        try:
            # import here to avoid module-level circular imports
            from shared.plotting_engine.state import plot_manager
            plot_manager.set_widget(self)
        except Exception:
            # non-fatal: app will register later when ready
            pass

    def showEvent(self, event):
        """
        Re-register the canvas widget with the plot manager when the dock becomes visible.
        This handles cases where docks are hidden/restored and the plot_manager lost the binding.
        """
        super().showEvent(event)
        self.refresh_plot()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.refresh_plot()

    def refresh_plot(self):
        try:
            from shared.plotting_engine.state import plot_manager
            if getattr(plot_manager, "widget", None) is not self:
                plot_manager.set_widget(self)
            QTimer.singleShot(0, self._draw_visible_canvas)
        except Exception:
            pass

    def _draw_visible_canvas(self):
        if not self.isVisible():
            return
        if self._active_backend != "mpl":
            return
        try:
            if hasattr(self.canvas_widget, "refresh_canvas"):
                self.canvas_widget.refresh_canvas()
            elif hasattr(self.canvas_widget, "canvas"):
                self.canvas_widget.canvas.draw_idle()
        except Exception:
            pass

    def get_canvas(self):
        """Returns the internal PlotWidget for external use."""
        return self.canvas_widget

    @property
    def figure(self):
        return self.canvas_widget.figure

    @property
    def canvas(self):
        return self.canvas_widget.canvas

    def configure_layout(self, is_3d: bool):
        return self.canvas_widget.configure_layout(is_3d=is_3d)

    def new_axes(self, projection=None):
        self.switch_backend("mpl")
        return self.canvas_widget.new_axes(projection=projection)

    def clear(self):
        self.switch_backend("mpl")
        return self.canvas_widget.clear()

    def render(self, *, immediate: bool = False):
        if self._active_backend == "mpl":
            return self.canvas_widget.render(immediate=immediate)

    def ginput(self, n=1, **kwargs):
        self.switch_backend("mpl")
        return self.canvas_widget.ginput(n=n, **kwargs)

    def _apply_axes_defaults(self, ax):
        return self.canvas_widget._apply_axes_defaults(ax)

    def get_plotly_widget(self):
        if self.plotly_widget is None:
            from shared.plotting_engine.plotly_backend import PlotlyWidget
            self.plotly_widget = PlotlyWidget(parent=self.canvas_container)
            self.plotly_widget.selection_changed.connect(self.plot_selection_changed.emit)
            self.backend_stack.addWidget(self.plotly_widget)
        return self.plotly_widget

    def switch_backend(self, target: str):
        target = str(target or "mpl").lower()
        if target in ("matplotlib", "mpl"):
            self._active_backend = "mpl"
            self.backend_stack.setCurrentWidget(self.canvas_widget)
            self.refresh_plot()
            return self.canvas_widget

        if target == "plotly":
            widget = self.get_plotly_widget()
            self._active_backend = "plotly"
            self.backend_stack.setCurrentWidget(widget)
            return widget

        raise ValueError("Backend must be 'matplotlib', 'mpl', or 'plotly'")

    def render_figure(self, fig):
        widget = self.switch_backend("plotly")
        widget.render_figure(fig)
        return widget

    def set_brush_mode(self, mode: str = "select"):
        widget = self.get_plotly_widget()
        widget.set_brush_mode(mode)

    def set_toolbar_visible(self, visible: bool):
        """Toggle the top toolbar area (keeps the top_bar placeholder in sync)."""
        h = 32 if visible else 0
        self.top_bar.setFixedHeight(h)
        # If the backend exposes a toolbar element, toggle it as well (defensive)
        try:
            tb = getattr(self.canvas_widget, "toolbar", None)
            if tb is not None:
                tb.setVisible(visible)
        except Exception:
            pass
