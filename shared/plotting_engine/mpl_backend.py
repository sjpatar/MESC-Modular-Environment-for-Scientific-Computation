"""
Qt-based Matplotlib render widget for Mathex UI.
"MATLAB-Grade" Edition - Public Layout API & Pro UI.

Responsibilities (STRICT):
- Provide Figure + Canvas + Toolbar
- Provide axes creation helpers
- Provide user interaction (zoom / pan / datacursor)
- NEVER decide WHEN to draw
- NEVER throttle
- NEVER schedule draws
"""

from __future__ import annotations

import numpy as np
import warnings
import traceback
import logging
import time
import os
from shared.config import AppConfig

# [FIX] Essential for 3D plotting to work
try:
    import mpl_toolkits.mplot3d 
    from mpl_toolkits.mplot3d.art3d import Line3D
    HAS_MPL_3D = True
except ImportError:
    HAS_MPL_3D = False
    Line3D = object # Mock

# Conditional imports for Headless mode support
try:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QLabel, QSizePolicy, QHBoxLayout, QFrame, QSpacerItem,
        QToolButton, QFileDialog, QMessageBox
    )
    from PySide6.QtCore import Qt, QSize, QTimer
    from PySide6.QtGui import QColor, QPalette, QFont, QIcon, QPixmap, QPainter, QImage, QResizeEvent
    
    import matplotlib
    # Default to QtAgg for live app rendering. On Windows, mplcairo's Qt canvas
    # has been a recurrent source of hard process crashes during label/layout
    # redraws, especially with non-Latin text. Keep mplcairo as an explicit
    # opt-in instead of the default path.
    if os.environ.get("MATHEX_ENABLE_MPLCAIRO", "").strip() == "1":
        try:
            matplotlib.use("module://mplcairo.qt")
            from mplcairo.qt import FigureCanvasQTCairo as FigureCanvasQTAgg
        except Exception:
            matplotlib.use("QtAgg", force=True)
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
    else:
        matplotlib.use("QtAgg", force=True)
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
    
    from matplotlib.backend_bases import MouseButton
    HAS_QT = True
except ImportError:
    HAS_QT = False
    QWidget = object # Mock

from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import matplotlib.pyplot as plt

# Filter out harmless layout warnings to keep the "Professional" feel
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)


# ============================================================
# Helpers
# ============================================================

def _unwrap(v):
    """Extract raw numpy data from wrappers."""
    if hasattr(v, '_data'):
        return np.asarray(v._data)
    if isinstance(v, (list, tuple)) and len(v) > 0 and hasattr(v[0], '_data'):
        return np.array([x._data for x in v])
    return v


# ============================================================
# Custom Canvas (The Ironclad Fix + Optimization)
# ============================================================

if HAS_QT:
    class MathexCanvas(FigureCanvasQTAgg):
        """
        Custom Canvas that intercepts the draw call to:
        1. Sanitize 3D objects (version mismatch fix).
        2. Capture frames for Animation Recording.
        3. Optimize Resize Performance.
        4. [CRITICAL] Enforce Full-Screen Layout on every frame.
        """
        def __init__(self, figure):
            super().__init__(figure)
            self._is_recording = False
            self._frames = []
            
            # [PERFORMANCE] Resize Throttler
            self._resize_timer = QTimer()
            self._resize_timer.setSingleShot(True)
            self._resize_timer.setInterval(50) # 50ms delay
            self._resize_timer.timeout.connect(self._delayed_resize_draw)

        def resizeEvent(self, event):
            """Override resizeEvent to debounce the expensive draw call."""
            super().resizeEvent(event)
            self._resize_timer.start()

        def _delayed_resize_draw(self):
            """Called when resize interaction settles."""
            try:
                self.draw_idle()
            except:
                pass

        def start_recording(self):
            self._frames = []
            self._is_recording = True
            
        def stop_recording(self):
            self._is_recording = False
            return list(self._frames) # Return copy

        def draw(self):
            # [PERFORMANCE] Only sanitize if we actually have 3D content
            has_3d = HAS_MPL_3D and hasattr(self.figure, 'axes') and self.figure.axes
            if has_3d:
                 self._sanitize_3d_artists()
                 
                 # [CRITICAL FIX] Enforce Full Screen Layout for Single 3D Plot
                 # This overrides any internal layout engine resets during resize/draw.
                 if len(self.figure.axes) == 1:
                     ax = self.figure.axes[0]
                     if getattr(ax, 'name', '') == '3d':
                         # 1. HARD DISABLE Layout Engine to prevent 'snap back'
                         if hasattr(self.figure, 'set_layout_engine'):
                             self.figure.set_layout_engine('none')
                         elif hasattr(self.figure, 'set_constrained_layout'):
                             self.figure.set_constrained_layout(False)

                         # 2. Force Axes to occupy 100% of figure
                         ax.set_position([0, 0, 1, 1], which='both')

                         # [NEW] Dynamically stretch 3D box and PREVENT clipping on rotation
                         w, h = self.get_width_height()
                         if h > 0:
                             ratio = w / h
                             try: 
                                 # Stretch the 3D box correctly depending on if window is tall or wide
                                 ax.set_box_aspect((ratio, 1, 1) if ratio > 1 else (1, 1/ratio, 1))
                                 
                             except: pass

            try:
                super().draw()
                
                # [NEW] Animation Capture Hook
                if self._is_recording:
                    self._capture_frame()
                    
            except Exception:
                traceback.print_exc()

        def _capture_frame(self):
            """Grabs the current render as an image."""
            try:
                # OPTIMIZATION FIX: Do not use self.grab() 
                # Bypass Qt's UI readback entirely and get the raw memory buffer from Matplotlib.
                buf = self.buffer_rgba()
                width, height = self.get_width_height()
                
                # Construct a QImage directly from the raw RGBA bytes
                qimg = QImage(buf, width, height, QImage.Format_RGBA8888)
                
                # CRITICAL: You must call .copy() because Matplotlib will overwrite 
                # the 'buf' memory location on the very next draw cycle.
                self._frames.append(qimg.copy())
                
            except Exception:
                pass

        def _sanitize_3d_artists(self):
            """
            Runtime Patcher for 3D attributes.
            [CRITICAL FIX] Aggressively prunes 'Zombie' artists (axes=None) to prevent crash.
            """
            try:
                for ax in self.figure.axes:
                    if hasattr(ax, 'zaxis'):
                        # -----------------------------------------------------------
                        # 1. PRUNE ZOMBIE ARTISTS (Fix for Crash: 'NoneType' object has no attribute 'M')
                        # -----------------------------------------------------------
                        for list_name in ['lines', 'collections', 'patches', 'artists', 'images', 'texts']:
                            if not hasattr(ax, list_name): continue
                            try:
                                lst = getattr(ax, list_name)
                                clean_lst = [a for a in lst if getattr(a, 'axes', None) is not None]
                                if len(clean_lst) < len(lst):
                                    lst[:] = clean_lst
                            except Exception:
                                pass

                        # -----------------------------------------------------------
                        # 2. FIX LINE3D ATTRIBUTES (Optimize Rotation)
                        # -----------------------------------------------------------
                        for line in ax.lines:
                            if isinstance(line, Line3D):
                                verts = getattr(line, "_verts3d", None)
                                if verts is not None:
                                    try:
                                        xs, ys, zs = verts
                                        if len(xs) != len(ys) or len(xs) != len(zs):
                                            try:
                                                line.remove()
                                            except Exception:
                                                pass
                                            continue
                                    except Exception:
                                        try:
                                            line.remove()
                                        except Exception:
                                            pass
                                        continue
                                if hasattr(line, '_axlim_clip') and hasattr(line, '_verts3d'):
                                    continue
                                if not hasattr(line, '_axlim_clip'):
                                    line._axlim_clip = False
                                if not hasattr(line, '_verts3d'):
                                    line._verts3d = ([], [], [])
            except Exception:
                pass


# ============================================================
# Stable Toolbar (Professional Look)
# ============================================================

if HAS_QT:
    class StableToolbar(NavigationToolbar2QT):
        """
        A 'Rock Solid' toolbar.
        - [FIXED] Record button placed BESIDE other buttons.
        - [FIXED] Coordinates pushed to far right.
        - [FIXED] Coordinates visible even on small windows (Policy: Minimum).
        """
        def __init__(self, canvas, parent):
            super().__init__(canvas, parent)
            
            # 1. VISUAL STYLE - Flat, Dark, Transparent Labels
            self.setStyleSheet("""
                QToolBar {
                    background-color: #252526;
                    border-bottom: 1px solid #3e3e42;
                    spacing: 4px;
                    padding: 2px;
                }
                QToolButton {
                    background-color: transparent;
                    border: 1px solid transparent;
                    border-radius: 3px;
                    color: #cccccc;
                    padding: 3px;
                }
                QToolButton:hover {
                    background-color: #3e3e42;
                    border: 1px solid #555555;
                }
                QToolButton:pressed {
                    background-color: #005f9e;
                    color: white;
                }
                QToolButton:checked {
                    background-color: #094771; 
                    border: 1px solid #007acc;
                    color: white;
                }
                QLabel {
                    color: #eeeeee;
                    background-color: transparent;
                    border: none;
                    /* [FIX] Monospace font prevents jitter when numbers change */
                    font-family: "Consolas", "Monospace", "Courier New";
                    font-size: 11px;
                    font-weight: bold;
                    padding-right: 10px;
                }
            """)

            # 2. CREATE RECORD BUTTON
            self.record_action = self.addAction("Record")
            self.record_action.setToolTip("Record Animation (Save as GIF)")
            self.record_action.setCheckable(True)
            self.record_action.triggered.connect(self._toggle_recording)
            self._update_record_icon(False)

            # 3. [LAYOUT FIX] REORDER ACTIONS
            try:
                label_action = None
                if hasattr(self, 'locLabel'):
                    for action in self.actions():
                        if self.widgetForAction(action) == self.locLabel:
                            label_action = action
                            break
                
                if label_action:
                    self.removeAction(self.record_action)
                    self.insertAction(label_action, self.record_action)
                    
                    empty = QWidget()
                    empty.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                    empty.setStyleSheet("background: transparent;")
                    self.insertWidget(label_action, empty)
                else:
                    empty = QWidget()
                    empty.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                    self.addWidget(empty)
            except Exception:
                pass

            # 4. [CRITICAL FIX] STABILIZE & FORCE VISIBILITY OF COORDINATES
            if hasattr(self, 'locLabel'):
                self.locLabel.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.locLabel.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
                self.locLabel.setMinimumWidth(80) 

        def _update_record_icon(self, is_recording):
            """Creates a programmatic icon for the record button."""
            size = 24
            pix = QPixmap(size, size)
            pix.fill(Qt.transparent)
            painter = QPainter(pix)
            painter.setRenderHint(QPainter.Antialiasing)
            
            if is_recording:
                painter.setBrush(QColor("#ff5555"))
                painter.setPen(Qt.NoPen)
                painter.drawRect(6, 6, 12, 12)
            else:
                painter.setBrush(QColor("#cccccc"))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(6, 6, 12, 12)
                
            painter.end()
            self.record_action.setIcon(QIcon(pix))

        def _toggle_recording(self, checked):
            self._update_record_icon(checked)
            if checked:
                self.canvas.start_recording()
            else:
                frames = self.canvas.stop_recording()
                if not frames:
                    QMessageBox.information(self, "No Frames", "No animation frames were captured.")
                    return
                self._save_recording(frames)

        def _save_recording(self, qimages):
            try:
                from PIL import Image
            except ImportError:
                QMessageBox.warning(self, "Missing Dependency", "Pillow (PIL) is required to save GIFs.")
                return

            path, _ = QFileDialog.getSaveFileName(self, "Save Animation", "", "GIF Image (*.gif)")
            if not path:
                return
            
            try:
                pil_frames = []
                for qimg in qimages:
                    qimg = qimg.convertToFormat(QImage.Format_RGBA8888)
                    width = qimg.width()
                    height = qimg.height()
                    ptr = qimg.bits()
                    if hasattr(ptr, "tobytes"):
                        arr = ptr.tobytes()
                    else:
                        arr = ptr.asstring(width * height * 4)
                    img = Image.frombuffer("RGBA", (width, height), arr, "raw", "RGBA", 0, 1)
                    pil_frames.append(img)

                pil_frames[0].save(
                    path, save_all=True, append_images=pil_frames[1:],
                    optimize=False, duration=50, loop=0
                )
                QMessageBox.information(self, "Success", f"Animation saved to:\n{path}")
            except Exception as e:
                traceback.print_exc()
                QMessageBox.critical(self, "Save Failed", f"Could not save GIF:\n{str(e)}")

        def set_message(self, s):
            super().set_message(s)
            if hasattr(self, 'locLabel'):
                self.locLabel.setVisible(True)
                if self.coordinates:
                    txt = self.locLabel.text()
                    self.locLabel.setText(txt.replace(', ', '  '))

        def home(self, *args, **kwargs):
            super().home(*args, **kwargs)
            has_3d = any(getattr(ax, 'name', '') == '3d' for ax in self.canvas.figure.axes)
            if has_3d:
                for ax in self.canvas.figure.axes:
                    if getattr(ax, 'name', '') == '3d':
                        # [FIX] Cubic aspect constraint removed to allow dock window stretch
                        pass
            self.canvas.draw_idle()


else:
    class StableToolbar:
        def __init__(self, *args, **kwargs): pass


# ============================================================
# PlotWidget (Qt) - The Rendering Surface
# ============================================================

class PlotWidget(QWidget):
    """
    Matplotlib Qt render surface.
    Engineered for STABILITY and PERFORMANCE.
    """

    def __init__(self, parent=None):
        if not HAS_QT:
            raise RuntimeError("Qt dependencies missing. Use HeadlessPlotWidget.")
        super().__init__(parent)

        # State tracking
        self._current_layout_mode = None 

        # --- NEW: Dynamic Font Resolution ---
        # Prioritize Windows native 'Nirmala UI' for Assamese, fallback to others
        lang = AppConfig.get_language()
        if lang == "as":
            font_stack = ['Nirmala UI', 'Noto Sans Bengali', 'Vrinda', 'Kalpurush', 'Lohit Assamese', 'DejaVu Sans']
        else:
            font_stack = ['DejaVu Sans', 'Arial', 'Helvetica']

        # -------------------------------------------------------
        # 1. Appearance / Defaults (Global Polish)
        # -------------------------------------------------------
        plt.rcParams.update({
            'figure.autolayout': False,             
            'figure.constrained_layout.use': False, # [FIX] Force OFF by default
            'path.simplify': True,           
            'path.simplify_threshold': 1.0,  
            'lines.antialiased': True,       
            'axes.linewidth': 0.8,           
            'xtick.direction': 'in',         
            'ytick.direction': 'in',         
            
            # [LOCALE FIX] Keep a generic family but provide an Indic-capable
            # fallback stack so Assamese labels pick a shaping-capable font.
            'font.family': 'sans-serif',
            'font.sans-serif': font_stack,
            
            'font.size': 10,
            'figure.facecolor': '#1e1e1e',
            'figure.edgecolor': '#1e1e1e',
            'savefig.facecolor': '#1e1e1e',
            'savefig.edgecolor': '#1e1e1e',
            'axes.facecolor': '#1e1e1e', 
            'axes.edgecolor': '#666666',
            'axes.labelcolor': '#eeeeee',
            'xtick.color': '#cccccc',
            'ytick.color': '#cccccc',
            'text.color': '#eeeeee',
            'grid.color': '#444444',
            'grid.alpha': 0.8
        })

        # -------------------------------------------------------
        # 2. Figure / Canvas
        # -------------------------------------------------------
        self.figure = Figure(figsize=(6, 4), dpi=100)
        self._current_layout_mode = None 
            
        self.figure.patch.set_facecolor("#1e1e1e")
        
        self.canvas = MathexCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.updateGeometry()

        self.toolbar = StableToolbar(self.canvas, self)

        # -------------------------------------------------------
        # 3. Layout (Rock Solid)
        # -------------------------------------------------------
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

        # Interaction State
        self._pan_active = False
        self._pan_start = None
        self._last_click_time = 0
        self._datacursor_enabled = True
        self._line_points = []
        self._annotations = []

        try:
            self.canvas.mpl_connect("scroll_event", self._on_scroll)
            self.canvas.mpl_connect("button_press_event", self._on_button_press)
            self.canvas.mpl_connect("button_release_event", self._on_button_release)
            self.canvas.mpl_connect("motion_notify_event", self._on_motion)
            self.canvas.mpl_connect("button_press_event", self._on_click_for_datacursor)
        except Exception:
            pass
        
        # Apply default 2D layout on startup so it looks good immediately
        self.configure_layout(is_3d=False)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_canvas()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.refresh_canvas()

    def refresh_canvas(self):
        try:
            if not self.isVisible() or self.canvas.width() <= 0 or self.canvas.height() <= 0:
                return
            self.canvas.updateGeometry()
            self.canvas.resize(self.canvas.size())
            QTimer.singleShot(0, self.canvas.draw_idle)
        except Exception:
            traceback.print_exc()

    # -------------------------------------------------------
    # PUBLIC Layout API (Called by state.py)
    # -------------------------------------------------------

    def configure_layout(self, is_3d: bool):
        """
        Atomically switches layout logic.
        """
        target_mode = '3d' if is_3d else '2d'
        
        if self._current_layout_mode == target_mode:
            # Force layout refresh for 3D just in case
            if is_3d and len(self.figure.axes) == 1:
                try: self.figure.axes[0].set_position([0, 0, 1, 1])
                except: pass
            return

        # 1. Disable current engine
        if hasattr(self.figure, 'set_layout_engine'):
            self.figure.set_layout_engine('none')
        elif hasattr(self.figure, 'set_constrained_layout'):
            self.figure.set_constrained_layout(False)

        # 2. Reset margins
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                self.figure.subplots_adjust(left=0.125, right=0.9, bottom=0.11, top=0.88, wspace=0.2, hspace=0.2)
            except Exception:
                pass

        # 3. Apply New Mode
        if target_mode == '3d':
            # 3D: ZERO Margins (Full Viewport Size)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    self.figure.subplots_adjust(left=0, right=1, bottom=0, top=1, wspace=0, hspace=0)
                    if len(self.figure.axes) == 1:
                        self.figure.axes[0].set_position([0, 0, 1, 1])
                except Exception:
                    pass
        else:
            # 2D: Enable Constrained Layout
            if hasattr(self.figure, 'set_layout_engine'):
                self.figure.set_layout_engine('constrained')
            elif hasattr(self.figure, 'set_constrained_layout'):
                self.figure.set_constrained_layout(True)

        self._current_layout_mode = target_mode

    # -------------------------------------------------------
    # Axes helpers
    # -------------------------------------------------------

    def gca(self):
        if self.figure.axes:
            ax = self.figure.axes[-1]
            if not getattr(ax, '_mathex_styled', False):
                self._apply_axes_defaults(ax)
            return ax
        return self.new_axes()

    def new_axes(self, projection=None):
            is_3d = (projection == '3d')
            self.configure_layout(is_3d)

            # [FIX] SILENT FALLBACK BUG: Removed the try...except block.
            # Now Matplotlib correctly raises a ValueError for invalid projections.
            ax = self.figure.add_subplot(111, projection=projection)

            self._apply_axes_defaults(ax)
            return ax  

    def _apply_axes_defaults(self, ax):
        try:
            ax._mathex_styled = True
            ax.set_facecolor("#1e1e1e")
            ax.tick_params(axis="both", colors="#cccccc", which='both', labelsize=9)
            
            for spine in ax.spines.values():
                spine.set_color("#666666")
                spine.set_linewidth(1.0)

            ax.grid(True, linestyle=':', linewidth=0.5, color='#444444', alpha=0.8)

            if getattr(ax, 'name', '') == '3d':
                # Force Absolute Position for 3D
                if len(self.figure.axes) == 1:
                    ax.set_position([0, 0, 1, 1])

                # [FIX] Aspect limits and Camera distance are now calculated dynamically
                # in MathexCanvas.draw() to prevent rotational clipping.
                
                pane_color = (0.118, 0.118, 0.118, 1.0) # #1e1e1e
                if hasattr(ax, 'xaxis'): ax.xaxis.set_pane_color(pane_color)
                if hasattr(ax, 'yaxis'): ax.yaxis.set_pane_color(pane_color)
                if hasattr(ax, 'zaxis'): ax.zaxis.set_pane_color(pane_color)
                
                grid_color = (0.4, 0.4, 0.4, 0.5)
                if hasattr(ax, 'xaxis') and hasattr(ax.xaxis, '_axinfo'): ax.xaxis._axinfo["grid"]['color'] = grid_color
                if hasattr(ax, 'yaxis') and hasattr(ax.yaxis, '_axinfo'): ax.yaxis._axinfo["grid"]['color'] = grid_color
                if hasattr(ax, 'zaxis') and hasattr(ax.zaxis, '_axinfo'): ax.zaxis._axinfo["grid"]['color'] = grid_color

                if hasattr(ax, 'xaxis'): ax.xaxis.label.set_color("#eeeeee")
                if hasattr(ax, 'yaxis'): ax.yaxis.label.set_color("#eeeeee")
                if hasattr(ax, 'zaxis'): ax.zaxis.label.set_color("#eeeeee")

        except Exception as e:
            traceback.print_exc()

    # -------------------------------------------------------
    # Utilities
    # -------------------------------------------------------

    def render(self, *, immediate: bool = False):
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")
                if self.figure.get_figwidth() <= 0: return
                
                if immediate:
                    self.canvas.draw()
                    self.canvas.flush_events()
                else:
                    self.canvas.draw_idle()
        except Exception:
            traceback.print_exc()

    def savefig(self, path, **kwargs):
        try:
            self.figure.savefig(path, **kwargs)
            return True
        except Exception:
            traceback.print_exc()
            return False

    def clear(self):
        try:
            if hasattr(self.figure, 'set_layout_engine'):
                self.figure.set_layout_engine('none')
            elif hasattr(self.figure, 'set_constrained_layout'):
                self.figure.set_constrained_layout(False)
            
            self.figure.clf()
            self.figure.patch.set_facecolor("#1e1e1e")
            
            self._current_layout_mode = None
            
            # [FIX] THE CLF/3D BUG: Do NOT call self.configure_layout(is_3d=False) here.
            # Setting constrained layout on an entirely empty figure crashes the backend.
            # It will be safely re-configured dynamically during the next new_axes() call.
            
            self.canvas.draw()
        except Exception:
            traceback.print_exc()

        self._line_points.clear()
        self.clear_annotations()
        
        if hasattr(self, 'toolbar') and self.toolbar:
            if hasattr(self.toolbar, '_nav_stack'):
                self.toolbar._nav_stack.clear()
            self.toolbar.update()

    # -------------------------------------------------------
    # Events
    # -------------------------------------------------------
    def ginput(self, n=1, timeout=30, show_clicks=True):
        try:
            self.canvas.draw()
            self.canvas.flush_events()
            return self.figure.ginput(n=n, timeout=timeout, show_clicks=show_clicks, mouse_add=1, mouse_pop=3, mouse_stop=2)
        except Exception:
            traceback.print_exc()
            return []

    def enable_datacursor(self, enabled=True):
        self._datacursor_enabled = bool(enabled)

    def clear_annotations(self):
        for ann in list(self._annotations):
            try: ann.remove()
            except: pass
        self._annotations.clear()

    def _on_click_for_datacursor(self, event):
        if event.button != 1 or not self._datacursor_enabled: return
        ax = event.inaxes
        if ax is None or getattr(ax, 'name', '') == '3d': return

        try:
            best, bestd = None, float("inf")
            for xs, ys in self._line_points:
                dx, dy = xs - event.xdata, ys - event.ydata
                d = dx*dx + dy*dy
                idx = np.nanargmin(d)
                if d[idx] < bestd:
                    bestd, best = d[idx], (xs[idx], ys[idx])

            if best:
                # [NEW] Keep previous annotations if 'Shift' is held
                if event.key != 'shift':
                    self.clear_annotations()
                    
                # [NEW] Professional MATLAB-style tooltip
                ann = ax.annotate(
                    f"X: {best[0]:.4g}\nY: {best[1]:.4g}",
                    xy=best, 
                    xytext=(15, 15), 
                    textcoords="offset points",
                    color="#ffffff", 
                    fontsize=9,
                    fontfamily="Consolas",
                    bbox=dict(boxstyle="round,pad=0.4", fc="#252526", ec="#007acc", lw=1.5, alpha=0.95),
                    arrowprops=dict(arrowstyle="-|>", connectionstyle="arc3,rad=0.2", color="#007acc", lw=1.5)
                )
                self._annotations.append(ann)
                self.canvas.draw_idle()
        except:
            traceback.print_exc()

    def _on_scroll(self, event):
        # -------------------------------------------------------------
        # 1. 3D Zoom Strategy (Global Figure Scope)
        # -------------------------------------------------------------
        # In 3D plots, 'event.inaxes' is unreliable (often None).
        # We detect if a 3D axis exists and zoom it regardless of cursor pos.
        ax_3d = None
        for ax in self.figure.axes:
            if getattr(ax, 'name', '') == '3d':
                ax_3d = ax
                break

        if ax_3d is not None:
            # Sensitivity: 0.9 (In) / 1.1 (Out)
            factor = 0.9 if event.button == 'up' else 1.1
            try:
                # Modifying 'dist' moves the camera. 
                # Default is usually ~10. Lower = Closer.
                ax_3d.dist = ax_3d.dist * factor
            except Exception:
                pass
            
            self.canvas.draw_idle()
            return 

        # -------------------------------------------------------------
        # 2. 2D Zoom Strategy (Local Axes Scope)
        # -------------------------------------------------------------
        ax = event.inaxes
        if ax is None: return

        # Safety check for coordinates
        if event.xdata is None or event.ydata is None: return

        scale = 1.15 if event.button == "up" else 1.0/1.15
        
        try:
            xlim, ylim = ax.get_xlim(), ax.get_ylim()
            x, y = event.xdata, event.ydata
            
            new_w = (xlim[1]-xlim[0]) * scale
            new_h = (ylim[1]-ylim[0]) * scale
            
            rx = (x - xlim[0]) / (xlim[1] - xlim[0])
            ry = (y - ylim[0]) / (ylim[1] - ylim[0])
            
            ax.set_xlim([x - new_w * rx, x + new_w * (1-rx)])
            ax.set_ylim([y - new_h * ry, y + new_h * (1-ry)])
            
            self.canvas.draw_idle()
        except Exception:
            pass

    def _on_button_press(self, event):
        if event.button == 3:
            now = time.time()
            if now - self._last_click_time < 0.3:
                self.toolbar.home()
                return
            self._last_click_time = now
        if event.button == 3 and event.inaxes and getattr(event.inaxes, 'name', '') != '3d':
            self._pan_active = True
            self._pan_start = (event.inaxes, event.xdata, event.ydata)

    def _on_button_release(self, event):
        self._pan_active = False

    def _on_motion(self, event):
        if self._pan_active and event.inaxes:
            ax, x0, y0 = self._pan_start
            dx, dy = event.xdata - x0, event.ydata - y0
            ax.set_xlim(ax.get_xlim() - dx)
            ax.set_ylim(ax.get_ylim() - dy)
            self.canvas.draw_idle()


# ============================================================
# Headless Widget (Mock)
# ============================================================

class HeadlessPlotWidget:
    def __init__(self):
        self.figure = Figure(figsize=(6, 4), dpi=100)
        try:
            if hasattr(self.figure, "set_layout_engine"):
                self.figure.set_layout_engine("none")
            elif hasattr(self.figure, "set_constrained_layout"):
                self.figure.set_constrained_layout(False)
        except Exception:
            pass
        self.canvas = FigureCanvasAgg(self.figure)
    def gca(self): return self.figure.gca()
    def new_axes(self, projection=None): return self.figure.add_subplot(111, projection=projection)
    def configure_layout(self, is_3d: bool): pass  # API Compatibility
    def render(self, *, immediate=False): pass
    def savefig(self, path, **kwargs): self.figure.savefig(path, **kwargs)
    def clear(self):
        self.figure.clf()
        try:
            if hasattr(self.figure, "set_layout_engine"):
                self.figure.set_layout_engine("none")
            elif hasattr(self.figure, "set_constrained_layout"):
                self.figure.set_constrained_layout(False)
        except Exception:
            pass
    def ginput(self, n=1, **k): return []
