import sys
import os
import ctypes
import time
import re  
import io
import threading
import traceback
from contextlib import redirect_stdout
from PySide6.QtWidgets import (
    QMainWindow, QDockWidget, QApplication, QLabel, QWidget,
    QHBoxLayout, QVBoxLayout, QPushButton, QStyle, QFileDialog, QDialog
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QTimer, QSettings, QSize, QEvent, QThread, Signal, Slot

# --- Mathex Internal Imports ---
# [FIX] KernelSession & PlotEngine removed from top-level to prevent UI freezing
from ides.mathex.ui.kernel_worker import start_kernel_worker
from ides.mathex.language.locale import tr as ml_tr

# --- UI Components ---
from .console import ConsoleWidget
from .editor import ScriptEditor
from .plotdock import PlotDock
from app_platform.ui_shell.workspace_manager import WorkspaceWidget
from app_platform.ui_shell.menus import MainMenuBar
from .filebrowser import FileBrowser

NON_TIMED_COMMANDS = {
    "clc", "clf", "clear", "clear all", "close", 
    "close all", "who", "whos", "format",
    "মচিদিয়া", "দেখুওৱা", "সহায়"
}

PLOT_COMMAND_PATTERN = re.compile(
    r"\b("
    r"plot|plot3|scatter|scatter3|surf|mesh|contour|contour3|contourf|contourf3|"
    r"quiver|quiver3|streamline|imagesc|imshow|heatmap|bar|barh|hist|histogram|"
    r"pie|stem|stairs|boxplot|gscatter|plotmatrix|subplot|figure|clf|cla|hold|brush|"
    r"grid|axis|view|shading|lighting|camlight|colorbar|legend|xlabel|ylabel|"
    r"zlabel|xlim|ylim|zlim|animatedline|addpoints|clearpoints|drawnow|"
    r"drawnowlimit|comet|comet3|getframe|movie"
    r")\b",
    re.IGNORECASE,
)

def get_app_icon_path():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = []
    if os.name == "nt":
        candidates.extend([
                os.path.join(base_dir, "resources", "icon.ico"),
                os.path.join(base_dir, "..", "resources", "icon.ico"),
                "icon.ico",
        ])
    candidates.extend([
            os.path.join(base_dir, "resources", "logo.png"),
            os.path.join(base_dir, "..", "resources", "logo.png"),
            "logo.png",
    ])
    for path in candidates:
        if os.path.exists(path): return path
    return None

class DockTitleBar(QWidget):
    def __init__(self, dock: QDockWidget, title_key: str):
        super().__init__(dock)
        self.dock = dock
        self.title_key = title_key
        self._is_fullscreen = False
        self._normal_geometry = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)

        self.title_label = QLabel()
        self.title_label.setStyleSheet("color: #cccccc; font-weight: bold;")
        layout.addWidget(self.title_label)
        layout.addStretch(1)

        BTN_SIZE = 14
        BTN_STYLE = "QPushButton { border: none; background: transparent; color: #9e9e9e; font-size: 11px; padding: 0px; } QPushButton:hover { color: #d4d4d4; }"

        fs_btn = QPushButton("⛶")
        fs_btn.setFixedSize(BTN_SIZE, BTN_SIZE)
        fs_btn.setStyleSheet(BTN_STYLE)
        fs_btn.clicked.connect(self._toggle_fullscreen)
        layout.addWidget(fs_btn)

        float_btn = QPushButton()
        float_btn.setIcon(dock.style().standardIcon(QStyle.SP_TitleBarNormalButton))
        float_btn.setIconSize(QSize(12, 12))
        float_btn.setFixedSize(BTN_SIZE, BTN_SIZE)
        float_btn.setStyleSheet(BTN_STYLE)
        float_btn.clicked.connect(lambda: dock.setFloating(not dock.isFloating()))
        layout.addWidget(float_btn)

        close_btn = QPushButton()
        close_btn.setIcon(dock.style().standardIcon(QStyle.SP_TitleBarCloseButton))
        close_btn.setIconSize(QSize(12, 12))
        close_btn.setFixedSize(BTN_SIZE, BTN_SIZE)
        close_btn.setStyleSheet(BTN_STYLE)
        close_btn.clicked.connect(dock.close)
        layout.addWidget(close_btn)
        
        self.retranslate_ui()

    def changeEvent(self, event):
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate_ui()
        super().changeEvent(event)

    def retranslate_ui(self):
        self.title_label.setText(ml_tr(self.title_key.lower().replace(" ", "_")))

    def _toggle_fullscreen(self):
        if not self._is_fullscreen:
            self._normal_geometry = self.dock.saveGeometry()
            self.dock.setFloating(True)
            self.dock.showFullScreen()
            self._is_fullscreen = True
        else:
            self.dock.showNormal()
            self.dock.setFloating(False)
            if self._normal_geometry:
                self.dock.restoreGeometry(self._normal_geometry)
            self._is_fullscreen = False

class DetachedPlotDialog(QDialog):
    """
    Persistent top-level figure window.

    Closing the window hides it so future figure(N) calls reuse the same
    Matplotlib state, toolbar history, and window placement.
    """
    plot_selection_changed = Signal(list)

    def __init__(self, fig_id: int, parent=None):
        super().__init__(parent)
        from shared.plotting_engine.mpl_backend import PlotWidget

        self.fig_id = int(fig_id)
        self._active_backend = "mpl"
        self.plotly_widget = None
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setWindowTitle(f"Figure {self.fig_id}")
        self.resize(900, 650)

        self.backend_stack = QWidget(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.canvas_widget = PlotWidget(parent=self)
        layout.addWidget(self.canvas_widget)

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def get_canvas(self):
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
            self.plotly_widget = PlotlyWidget(parent=self)
            self.plotly_widget.selection_changed.connect(self.plot_selection_changed.emit)
            self.layout().addWidget(self.plotly_widget)
            self.plotly_widget.hide()
        return self.plotly_widget

    def switch_backend(self, target: str):
        target = str(target or "mpl").lower()
        if target in ("matplotlib", "mpl"):
            self._active_backend = "mpl"
            self.canvas_widget.show()
            if self.plotly_widget is not None:
                self.plotly_widget.hide()
            return self.canvas_widget

        if target == "plotly":
            widget = self.get_plotly_widget()
            self._active_backend = "plotly"
            self.canvas_widget.hide()
            widget.show()
            return widget

        raise ValueError("Backend must be 'matplotlib', 'mpl', or 'plotly'")

    def render_figure(self, fig):
        widget = self.switch_backend("plotly")
        widget.render_figure(fig)
        return widget

    def set_brush_mode(self, mode: str = "select"):
        widget = self.get_plotly_widget()
        widget.set_brush_mode(mode)

class MathexApp(QMainWindow):
    _figure_create_requested = Signal(int, str)

    def __init__(self):
        super().__init__()
        # Unify settings under the parent MESC environment
        self.settings = QSettings("MESC", "MathexIDE")
        self.resize(1400, 900)
        self._set_window_icon()

        self.setStyleSheet("""
            QMainWindow { background-color: #1A1A1A; }
            QDockWidget { color: #cccccc; border: 1px solid #333333; }
            QDockWidget::title { background: #252526; padding: 6px; font-weight: bold; }
            QStatusBar { background: #1A1A1A; color: #cccccc; border-top: 1px solid #121212; }
            QStatusBar::item { border: none; }
            QLabel { padding: 0; margin: 0; background: transparent; }
        """)

        # [FIX] Session starts completely empty to keep UI loading instant
        self.session = None 
        
        self.editor = ScriptEditor()
        self.console = ConsoleWidget()
        self.workspace = WorkspaceWidget()
        self.plot_dock = PlotDock()
        self.file_browser = FileBrowser()
        self._detached_plot_windows = {}
        self._pending_plot_windows = {}
        self._pending_plot_lock = threading.Lock()
        self._plot_window_policy = "docked"
        self._detached_plot_order = {}
        self._figure_create_requested.connect(self._create_detached_figure_on_ui)

        self.setCentralWidget(self.editor)

        self.files_dock = self._add_dock("Current Folder", self.file_browser, Qt.LeftDockWidgetArea)
        self.console_dock = self._add_dock("Command Window", self.console, Qt.BottomDockWidgetArea)
        self.workspace_dock = self._add_dock("Workspace", self.workspace, Qt.RightDockWidgetArea)
        self.plotdock_dock = self._add_dock("Figures", self.plot_dock, Qt.RightDockWidgetArea)
        
        self.custom_title_bar = DockTitleBar(self.plotdock_dock, "Figures")
        self.plotdock_dock.setTitleBarWidget(self.custom_title_bar)

        last_path = self.settings.value("last_path", "")
        if last_path: self.file_browser.set_path(last_path)

        open_files = self.settings.value("open_files", [])
        if open_files:
            if self.editor.count() == 1:
                current = self.editor.current_editor()
                if not getattr(current, 'filename', None) and not current.toPlainText().strip():
                     self.editor.close_tab(0)
            for fpath in open_files: self.editor.open_file_by_path(fpath)
            last_idx = self.settings.value("active_tab", 0)
            if last_idx: self.editor.setCurrentIndex(int(last_idx))

        self.console.command_entered.connect(self._run_code_from_console)
        self.file_browser.file_open_requested.connect(self.editor.open_file_by_path)

        self.workspace.clear_requested.connect(self._clear_workspace)
        self.workspace.save_requested.connect(self._save_workspace)
        self.workspace.load_requested.connect(self._load_workspace)
        self.workspace.variable_edited.connect(self._sync_variable_to_kernel)
        self.plot_dock.plot_selection_changed.connect(self._on_plot_selection_changed)

        self.menu = MainMenuBar(self)
        self.setMenuBar(self.menu)
        self._attach_menu_signals()

        self.files_dock.visibilityChanged.connect(lambda v: self._sync_dock_menu(self.menu.files_action, v))
        self.console_dock.visibilityChanged.connect(lambda v: self._sync_dock_menu(self.menu.console_action, v))
        self.workspace_dock.visibilityChanged.connect(lambda v: self._sync_dock_menu(self.menu.workspace_action, v))
        self.plotdock_dock.visibilityChanged.connect(self._on_plot_dock_visibility_changed)

        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #e5c07b; font-weight: bold;")
        self.statusBar().addWidget(self.status_label, 1)

        self.kernel_led = QLabel("●")
        self.kernel_led.setStyleSheet("color: #e5c07b;")
        self.statusBar().addWidget(self.kernel_led)

        self.time_label = QLabel("")
        self.time_label.setStyleSheet("color: #61afef;")
        self.statusBar().addPermanentWidget(self.time_label)

        self.selection_label = QLabel("")
        self.selection_label.setStyleSheet("color: #c678dd;")
        self.statusBar().addPermanentWidget(self.selection_label)

        self.mode_label = QLabel("")
        self.mode_label.setStyleSheet("color: #aaaaaa; font-weight: bold;")
        self.statusBar().addPermanentWidget(self.mode_label)

        self.cursor_label = QLabel("")
        self.cursor_label.setStyleSheet("color: #aaaaaa; background: transparent; padding: 0; margin: 0;")
        self.statusBar().addPermanentWidget(self.cursor_label)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #e06c75;")
        self.statusBar().addPermanentWidget(self.error_label)

        self._last_connected_editor = None
        self.editor.currentChanged.connect(self._update_cursor_connection)
        self._update_cursor_connection()

        self._kernel_thread = None
        self._kernel_worker = None
        self._busy = False
        self._error_count = 0
        self._exec_start = None
        self._current_task_name = ""

        self.retranslate_ui()
        self.console.initialize(ml_tr("loading_kernel", default="Initializing Kernel..."))
        
        # [FIX] Triggers heavy module load 100ms AFTER the window draws
        QTimer.singleShot(100, self._initialize_heavy_components)

    def _initialize_heavy_components(self):
        """Spins up the Mathex Kernel silently in the background."""
        from ides.mathex.kernel.session import KernelSession
        from shared.plotting_engine.engine import PlotEngine
        from shared.plotting_engine.figure import init_ui_widget
        from shared.plotting_engine.state import plot_manager

        # Setup Plotting First
        PlotEngine.initialize("ui")
        init_ui_widget(self.plot_dock)
        plot_manager.set_figure_creator(self._ensure_plot_figure)

        # Launch the heavy kernel
        self.session = KernelSession()
        
        # Start Plotting Render Timer
        self._plot_timer = QTimer(self)
        self._plot_timer.timeout.connect(PlotEngine.tick)
        self._plot_timer.start(33)

        self.workspace.update_table(self.session.globals)
        self.status_label.setStyleSheet("color: #98c379; font-weight: bold;")
        self.kernel_led.setStyleSheet("color: #98c379;")
        self.status_label.setText(ml_tr("ready"))
        self.console.write_output("Mathex Ready.")

    def _ensure_plot_figure(self, fig_id: int = 1, *, backend: str = "mpl"):
        """
        Figure factory registered with PlotStateManager.

        In docked mode, every figure id maps to the main PlotDock. In detached
        mode, every figure id maps to its own persistent dialog.
        """
        fig_id = int(fig_id or 1)
        if self._plot_window_policy == "docked":
            widget = self.plot_dock
            from shared.plotting_engine.state import plot_manager
            plot_manager.bind_figure(fig_id, widget)
            return widget

        if QThread.currentThread() is self.thread():
            return self._ensure_detached_plot_window(fig_id, backend=backend)

        ready = threading.Event()
        result = {}
        with self._pending_plot_lock:
            self._pending_plot_windows[fig_id] = (ready, result)

        self._figure_create_requested.emit(fig_id, backend)
        if not ready.wait(timeout=3.0):
            raise RuntimeError(f"Timed out creating Figure {fig_id}.")

        if result.get("error") is not None:
            raise RuntimeError(f"Could not create Figure {fig_id}: {result['error']}")

        widget = result.get("widget")
        if widget is None:
            raise RuntimeError(f"Could not create Figure {fig_id}.")
        return widget

    @Slot(int, str)
    def _create_detached_figure_on_ui(self, fig_id: int, backend: str = "mpl"):
        try:
            widget = self._ensure_detached_plot_window(fig_id, backend=backend)
            error = None
        except Exception as exc:
            widget = None
            error = exc

        with self._pending_plot_lock:
            pending = self._pending_plot_windows.pop(int(fig_id), None)

        if pending is not None:
            ready, result = pending
            result["widget"] = widget
            result["error"] = error
            ready.set()

    def _ensure_detached_plot_window(self, fig_id: int, *, backend: str = "mpl"):
        from shared.plotting_engine.state import plot_manager

        fig_id = int(fig_id)
        dialog = self._detached_plot_windows.get(fig_id)
        if dialog is None:
            dialog = DetachedPlotDialog(fig_id, parent=self)
            dialog.plot_selection_changed.connect(self._on_plot_selection_changed)
            self._detached_plot_windows[fig_id] = dialog

        dialog.show()
        self._position_detached_plot_window(fig_id, dialog)
        dialog.raise_()
        dialog.activateWindow()

        dialog.switch_backend(backend)
        plot_manager.bind_figure(fig_id, dialog)
        return dialog

    def _position_detached_plot_window(self, fig_id: int, dialog: QDialog):
        if fig_id not in self._detached_plot_order:
            self._detached_plot_order[fig_id] = len(self._detached_plot_order)

        offset = self._detached_plot_order[fig_id] * 34
        base = self.frameGeometry().topLeft()
        dialog.move(base.x() + 120 + offset, base.y() + 90 + offset)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate_ui()
        super().changeEvent(event)

    def retranslate_ui(self):
        self.setWindowTitle(ml_tr("mathex_environment"))
        self.files_dock.setWindowTitle(ml_tr("current_folder"))
        self.console_dock.setWindowTitle(ml_tr("command_window"))
        self.workspace_dock.setWindowTitle(ml_tr("workspace"))
        self.plotdock_dock.setWindowTitle(ml_tr("figures"))
        
        if self._busy:
            self.status_label.setText(ml_tr("busy_running", name=self._current_task_name))
        elif self._error_count > 0:
            self.status_label.setText(ml_tr("finished_with_errors"))
            self.error_label.setText(ml_tr("errors_count", count=self._error_count))
        else:
            self.status_label.setText(ml_tr("ready"))

        self._update_cursor_info()

    def _is_non_timed_code(self, code: str) -> bool:
        lines = [line.strip().lower() for line in code.splitlines() if line.strip() and not line.strip().startswith("%")]
        if not lines: return True
        return all(line in NON_TIMED_COMMANDS for line in lines)

    def _update_cursor_connection(self):
        new_editor = self.editor.current_editor()
        old_editor = self._last_connected_editor
        if old_editor and old_editor != new_editor:
            try: old_editor.cursorPositionChanged.disconnect(self._update_cursor_info)
            except Exception: pass
        if new_editor:
            if new_editor != old_editor:
                try: new_editor.cursorPositionChanged.connect(self._update_cursor_info)
                except Exception: pass
            self._update_cursor_info()
        else:
            self.cursor_label.setText("")
            self.mode_label.setText("")
            self.selection_label.setText("")
        self._last_connected_editor = new_editor

    def _update_cursor_info(self):
        editor = self.editor.current_editor()
        if editor:
            cursor = editor.textCursor()
            ln = cursor.blockNumber() + 1
            col = cursor.columnNumber() + 1
            self.cursor_label.setText(ml_tr("cursor_position", line=ln, col=col))
            self.mode_label.setText(ml_tr("overwrite_mode") if editor.overwriteMode() else ml_tr("insert_mode"))
            if cursor.hasSelection():
                text = cursor.selectedText()
                self.selection_label.setText(
                    ml_tr("selection_status", lines=text.count("\u2029") + 1, chars=len(text))
                )
            else:
                self.selection_label.setText("")
        else:
            self.cursor_label.setText("")
            self.mode_label.setText("")
            self.selection_label.setText("")

    def _set_window_icon(self):
        icon_path = get_app_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))

    def _add_dock(self, title_key, widget, area):
        dock = QDockWidget("", self)
        dock.setWidget(widget)
        self.addDockWidget(area, dock)
        return dock

    def _sync_dock_menu(self, action, visible):
        action.blockSignals(True)
        action.setChecked(visible)
        action.blockSignals(False)

    def _on_plot_dock_visibility_changed(self, visible):
        self._sync_dock_menu(self.menu.plot_action, visible)
        if visible:
            self._refresh_plot_dock()

    def _refresh_plot_dock(self):
        try:
            if hasattr(self.plot_dock, "refresh_plot"):
                self.plot_dock.refresh_plot()
        except Exception: pass

    def _attach_menu_signals(self):
        m = self.menu.signals
        m.new_file.connect(self.editor.new_file)
        m.open_file.connect(self.editor.open_file)
        m.save_file.connect(self.editor.save_current)
        m.save_as.connect(self.editor.save_as)
        m.close_file.connect(self.editor.close_current)
        m.undo.connect(lambda: self.menu.invoke_editor_action("undo"))
        m.redo.connect(lambda: self.menu.invoke_editor_action("redo"))
        m.cut.connect(lambda: self.menu.invoke_editor_action("cut"))
        m.copy.connect(lambda: self.menu.invoke_editor_action("copy"))
        m.paste.connect(lambda: self.menu.invoke_editor_action("paste"))
        m.select_all.connect(lambda: self.menu.invoke_editor_action("selectAll"))
        m.toggle_files.connect(lambda v: self.files_dock.setVisible(v))
        m.toggle_console.connect(lambda v: self.console_dock.setVisible(v))
        m.toggle_workspace.connect(lambda v: self.workspace_dock.setVisible(v))
        m.toggle_plots.connect(lambda v: self.plotdock_dock.setVisible(v))
        m.run_script.connect(self._run_script)
        m.debug_script.connect(self._debug_script)

    def _run_code_from_console(self, code):
        self._run_code(code, task_name=ml_tr("console_command"))

    def _run_script(self):
        code = self.editor.get_current_code()
        filepath = self.editor.get_current_filename()
        if not code.strip():
            self.console.write_error(ml_tr("nothing_to_execute"))
            return
        fname = os.path.basename(filepath) if filepath else ml_tr("untitled")
        self.console.write_output(f"--- {ml_tr('running_task', name=fname)} ---")
        self._run_code(code, task_name=fname)

    def _debug_script(self):
        code = self.editor.get_current_code()
        filepath = self.editor.get_current_filename()
        if not code.strip():
            self.console.write_error(ml_tr("nothing_to_debug"))
            return
        breakpoints = self.editor.get_breakpoints() if hasattr(self.editor, 'get_breakpoints') else []
        fname = os.path.basename(filepath) if filepath else ml_tr("untitled")
        self.console.write_output(f"--- {ml_tr('debugging_task', name=fname)} ---")
        self._run_code(code, task_name=fname, breakpoints=breakpoints)

    def _run_code(self, code: str, task_name: str = None, breakpoints: list = None):
        if not self.session:
            self.console.write_error("Kernel is currently loading. Please wait.")
            return

        if task_name is None:
            task_name = ml_tr("default_code_task")
        if self._busy:
            self.console.write_error(ml_tr("kernel_busy"))
            return
        if not code.strip():
            self.console.execution_finished()
            return
        if self.editor.current_editor():
            self.editor.current_editor().clear_errors()

        self._prepare_plot_windows_for_run(code)

        self._busy = True
        self._current_task_name = task_name

        try:
            self._exec_start = None
            if not self._is_non_timed_code(code): self._exec_start = time.perf_counter()

            self.kernel_led.setStyleSheet("color: #e06c75;")
            self.time_label.setText("")
            self.console.busy = True
            self._error_count = 0
            self.error_label.setText("")

            self.status_label.setStyleSheet("color: #e06c75; font-weight: bold;")
            self.retranslate_ui() 

            # UI Blocking logic has been completely removed.
            # Matplotlib and Plotly background rendering is handled safely 
            # via headless Base64 HTML buffering in the worker thread.
            self._kernel_thread, self._kernel_worker = start_kernel_worker(
                self.session, code,
                breakpoints=breakpoints, 
                on_output=self.console.write_output,
                on_error=self._on_kernel_error,
                on_finished=self._on_execution_finished,
            )
        except Exception as e:
            self._busy = False
            self.console.busy = False
            self.console.write_error(ml_tr("ide_error", msg=str(e)))
            self.status_label.setText(ml_tr("ready_error"))
            self.kernel_led.setStyleSheet("color: #e06c75;")

    def _prepare_plot_windows_for_run(self, code: str):
        has_multiple_figures = self._script_requests_multiple_figures(code)
        self._plot_window_policy = "detached" if has_multiple_figures else "docked"
        self._detached_plot_order = {}

        try:
            import importlib
            from shared.plotting_engine.state import plot_manager
            figure_module = importlib.import_module("shared.plotting_engine.figure")

            plot_manager.reset_figures()
            reset_registry = getattr(figure_module, "reset_registry", None)
            if callable(reset_registry):
                reset_registry(include_ui=not has_multiple_figures)

            if has_multiple_figures:
                self.plot_dock.switch_backend("mpl")
                for dialog in self._detached_plot_windows.values():
                    dialog.hide()
            else:
                for dialog in self._detached_plot_windows.values():
                    dialog.hide()
                self.plot_dock.switch_backend("mpl")
                plot_manager.bind_figure(1, self.plot_dock)
        except Exception:
            pass

    def _script_requests_multiple_figures(self, code: str) -> bool:
        cleaned_lines = []
        for line in (code or "").splitlines():
            cleaned_lines.append(line.split("%", 1)[0])
        cleaned = "\n".join(cleaned_lines)

        figure_calls = []
        for match in re.finditer(r"\bfigure\s*\(\s*([0-9]+)?", cleaned, flags=re.IGNORECASE):
            value = match.group(1)
            figure_calls.append(int(value) if value else 1)

        for match in re.finditer(r"(?im)^\s*figure(?!\s*\()\s*([0-9]+)?\b", cleaned):
            value = match.group(1)
            figure_calls.append(int(value) if value else 1)

        return len(set(figure_calls)) > 1

    def _should_run_on_ui_thread(self, code: str) -> bool:
        return bool(PLOT_COMMAND_PATTERN.search(code or ""))

    def _execute_code_on_ui_thread(self, code: str):
        stdout_buf = io.StringIO()
        try:
            with redirect_stdout(stdout_buf):
                self.session.execute(code)
        except Exception as exc:
            traceback.print_exc()
            self._on_kernel_error(f"{type(exc).__name__}: {exc}")
        finally:
            out = stdout_buf.getvalue()
            if out:
                self.console.write_output(out)
            self._on_execution_finished()

    def _on_kernel_error(self, error_msg):
        self._error_count += 1
        self.error_label.setText(ml_tr("errors_count", count=self._error_count))
        self.console.write_error(error_msg)
        match = re.search(r"\((?:Line|শাৰী)\s+(\d+)\)", error_msg)
        if match:
            try:
                line_num = int(match.group(1))
                editor = self.editor.current_editor()
                if editor: editor.set_error_line(line_num)
            except Exception: pass
        self.workspace.update_table(self.session.globals)

    def _on_execution_finished(self):
        if self._plot_window_policy == "docked":
            self._refresh_plot_dock()
        if self._exec_start is not None:
            self.time_label.setText(f"{time.perf_counter() - self._exec_start:.3f} s")
        else:
            self.time_label.setText("")

        self.workspace.update_table(self.session.globals)
        self.console.execution_finished()
        self.console.busy = False

        try:
            from shared.plotting_engine.state import plot_manager
            for widget in plot_manager.widgets:
                if hasattr(widget, "render"):
                    widget.render(immediate=True)
        except Exception: pass

        self._busy = False

        if self._error_count > 0:
            self.kernel_led.setStyleSheet("color: #e5c07b;")
            self.status_label.setStyleSheet("color: #e06c75; font-weight: bold;")
        else:
            self.kernel_led.setStyleSheet("color: #98c379;")
            self.status_label.setStyleSheet("color: #98c379; font-weight: bold;")
            self.error_label.setText("")
            
        self.retranslate_ui()

    def _sync_variable_to_kernel(self, name, value):
        if self.session: self.session.globals[name] = value

    def _on_plot_selection_changed(self, indices):
        try:
            self.workspace.highlight_rows(indices)
            self.selection_label.setText(f"Plot Sel {len(indices)}")
        except Exception:
            pass

    def _clear_workspace(self):
        if not self.session: return
        self.session._clear_user()
        self.workspace.update_table(self.session.globals)
        self.console.write_output(ml_tr("workspace_cleared"))

    def _save_workspace(self):
        if not self.session: return
        filepath, _ = QFileDialog.getSaveFileName(self, ml_tr("save_workspace"), "", ml_tr("mat_files_filter"))
        if filepath:
            self.console.write_output(ml_tr("saving_workspace_to", path=filepath))
            from ides.mathex.io.saver import save_workspace
            try:
                save_workspace(self.session, filepath)
                self.console.write_output(ml_tr("workspace_saved_successfully"))
            except Exception as e:
                self.console.write_error(ml_tr("error_saving_workspace", msg=str(e)))

    def _load_workspace(self):
        if not self.session: return
        filepath, _ = QFileDialog.getOpenFileName(self, ml_tr("load_workspace"), "", ml_tr("mat_files_filter"))
        if filepath:
            self.console.write_output(ml_tr("loading_workspace_from", path=filepath))
            from ides.mathex.io.datareader import load_workspace
            try:
                load_workspace(self.session, filepath)
                self.workspace.update_table(self.session.globals)
                self.console.write_output(ml_tr("workspace_loaded_successfully"))
            except Exception as e:
                self.console.write_error(ml_tr("error_loading_workspace", msg=str(e)))

    def closeEvent(self, event):
        if hasattr(self.file_browser, 'current_path'):
            self.settings.setValue("last_path", self.file_browser.current_path)
        if hasattr(self.editor, 'get_open_filepaths'):
            self.settings.setValue("open_files", self.editor.get_open_filepaths())
            self.settings.setValue("active_tab", self.editor.currentIndex())
        try: 
            from shared.plotting_engine.engine import PlotEngine
            PlotEngine.shutdown()
        except Exception: pass
        for dialog in list(getattr(self, "_detached_plot_windows", {}).values()):
            try:
                dialog.hide()
                dialog.deleteLater()
            except Exception:
                pass
        event.accept()

def run():
    if hasattr(Qt, 'AA_EnableHighDpiScaling'): QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'): QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    if os.name == 'nt':
        # Removed legacy "mathexlab" reference to comply with architecture rules
        try: ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('mathex.ide.1.0.0')
        except Exception: pass

    app = QApplication(sys.argv)
    from PySide6.QtGui import QFont
    app.setFont(QFont("Segoe UI", 10))

    icon_path = get_app_icon_path()
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))

    win = MathexApp()
    win.show()
    sys.exit(app.exec())
