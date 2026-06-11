import os
import sys
import platform
import ctypes
import subprocess
import webbrowser

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, QThread, QTimer, QTranslator, Signal
from PySide6.QtGui import QCloseEvent, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from shared.config import AppConfig
from shared.updater.client import check_for_updates, download_asset


def get_resource_path(relative_path):
    """Get an absolute resource path in dev and PyInstaller builds."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(base_path, relative_path)


def get_app_icon_path():
    """Prefer a native Windows .ico for the taskbar, with a PNG fallback."""
    candidates = []
    if platform.system() == "Windows":
        candidates.append(os.path.join("ides", "mathex", "resources", "icon.ico"))
    candidates.append(os.path.join("ides", "mathex", "resources", "logo.png"))

    for relative_path in candidates:
        absolute_path = get_resource_path(relative_path)
        if os.path.exists(absolute_path):
            return absolute_path
    return None


def set_windows_rounded_corners(window_id, enable: bool):
    """Dynamically toggle Windows 11 rounded corners."""
    if platform.system() != "Windows":
        return
        
    try:
        import sys
        # Check if the OS is Windows 11 (Build 22000 or higher)
        if sys.getwindowsversion().build < 22000:
            return

        hwnd = int(window_id)
        DWMWA_WINDOW_CORNER_PREFERENCE = 33
        
        # 2 = DWMWCP_ROUND (Enabled), 1 = DWMWCP_DONOTROUND (Disabled)
        corner_preference = 2 if enable else 1 
        value = ctypes.c_int(corner_preference)
        
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 
            DWMWA_WINDOW_CORNER_PREFERENCE, 
            ctypes.byref(value), 
            ctypes.sizeof(value)
        )
    except Exception as e:
        print(f"Could not toggle rounded corners: {e}")


class CustomTitleBar(QFrame):
    change_language_sig = Signal(str)
    change_theme_sig = Signal(str)
    check_updates_sig = Signal()
    auto_update_toggled_sig = Signal(bool)

    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self._drag_pos = None
        self.current_category = "tool"

        self.setFixedHeight(40)
        self.setObjectName("TitleBar")
        self.setStyleSheet(
            """
            QFrame#TitleBar {
                background-color: #181818;
                border-bottom: 1px solid #2d2d2d;
            }
            QWidget#transparent-box {
                background-color: transparent;
                border: none;
            }
            QLabel {
                background-color: transparent;
                color: #cccccc;
                font-family: "Segoe UI", "Helvetica Neue", sans-serif;
                font-size: 10pt;
            }
            QLabel#app-title {
                font-weight: 600;
                font-size: 9pt;
                color: #e0e0e0;
                letter-spacing: 0.5px;
            }
            /* Window Control Buttons */
            QPushButton[cssClass="ctrl-btn"] {
                background-color: transparent;
                border: none;
                color: #b0b0b0;
                font-family: "Segoe UI", "Helvetica Neue", sans-serif;
                font-size: 10pt;
                width: 46px;
                height: 40px;
                margin: 0px;
                border-radius: 0px;
            }
            QPushButton[cssClass="ctrl-btn"]:hover { 
                background-color: #333333; 
                color: #ffffff; 
            }
            QPushButton#close-btn:hover { 
                background-color: #e81123; 
                color: #ffffff; 
            }
            /* Breadcrumb Navigation Pill */
            QFrame#breadcrumb-pill {
                background-color: #252526;
                border: 1px solid #3e3e42;
                border-radius: 12px; /* Smooth rounded pill */
            }
            QFrame#breadcrumb-pill:hover {
                background-color: #2d2d30;
                border: 1px solid #555555;
            }
            QPushButton[cssClass="breadcrumb-btn"] {
                background-color: transparent;
                color: #d4d4d4;
                border: none;
                font-family: "Segoe UI", sans-serif;
                font-size: 9pt;
                padding: 4px 12px;
                border-radius: 10px;
                font-weight: 500;
            }
            QPushButton[cssClass="breadcrumb-btn"]:hover {
                background-color: #3e3e42;
                color: #ffffff;
            }
            QPushButton[cssClass="breadcrumb-btn"]::menu-indicator {
                image: none;
            }
            """
        )

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(12, 0, 0, 0)
        self.layout.setSpacing(0)

        self.left_container = QWidget()
        self.left_container.setObjectName("transparent-box")
        self.left_layout = QHBoxLayout(self.left_container)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(10)

        self.logo_label = QLabel()
        logo_path = get_resource_path(os.path.join("ides", "mathex", "resources", "logo.png"))
        logo_pixmap = QPixmap(logo_path)
        if not logo_pixmap.isNull():
            self.logo_label.setPixmap(
                logo_pixmap.scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

        self.app_title = QLabel("MESC")
        self.app_title.setObjectName("app-title")
        self.left_layout.addWidget(self.logo_label)
        self.left_layout.addWidget(self.app_title)
        self.layout.addWidget(self.left_container)
        self.layout.addStretch(1)

        self.ctrl_container = QWidget()
        self.ctrl_container.setObjectName("transparent-box")
        self.ctrl_layout = QHBoxLayout(self.ctrl_container)
        self.ctrl_layout.setContentsMargins(0, 0, 0, 0)
        self.ctrl_layout.setSpacing(0)

        # Using modern geometric Unicode characters for window controls
        self.min_btn = QPushButton("─")
        self.min_btn.setProperty("cssClass", "ctrl-btn")
        self.min_btn.clicked.connect(self.parent_window.showMinimized)

        self.max_btn = QPushButton("◻")
        self.max_btn.setProperty("cssClass", "ctrl-btn")
        self.max_btn.clicked.connect(self.toggle_maximize)

        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("close-btn")
        self.close_btn.setProperty("cssClass", "ctrl-btn")
        self.close_btn.clicked.connect(self.parent_window.close)

        self.ctrl_layout.addWidget(self.min_btn)
        self.ctrl_layout.addWidget(self.max_btn)
        self.ctrl_layout.addWidget(self.close_btn)
        self.layout.addWidget(self.ctrl_container)

        self.breadcrumb_pill = QFrame(self)
        self.breadcrumb_pill.setObjectName("breadcrumb-pill")
        self.bc_layout = QHBoxLayout(self.breadcrumb_pill)
        self.bc_layout.setContentsMargins(4, 2, 4, 2)
        self.bc_layout.setSpacing(2)

        self.category_btn = QPushButton()
        self.category_btn.setCursor(Qt.PointingHandCursor)
        self.category_btn.setProperty("cssClass", "breadcrumb-btn")

        self.category_menu = QMenu(self)
        self._style_menu(self.category_menu)
        self.action_cat_tool = self.category_menu.addAction(self.tr("Select Tool"))
        self.action_cat_lang = self.category_menu.addAction(self.tr("Language"))
        self.action_cat_theme = self.category_menu.addAction(self.tr("Theme"))
        self.action_cat_updates = self.category_menu.addAction(self.tr("Updates"))
        self.action_cat_tool.triggered.connect(lambda: self.set_category("tool"))
        self.action_cat_lang.triggered.connect(lambda: self.set_category("language"))
        self.action_cat_theme.triggered.connect(lambda: self.set_category("theme"))
        self.action_cat_updates.triggered.connect(lambda: self.set_category("updates"))
        self.category_btn.setMenu(self.category_menu)

        # Using a sleek chevron character instead of a basic >
        self.separator = QLabel("›")
        self.separator.setStyleSheet("color: #777777; font-size: 14pt; padding-bottom: 3px; font-weight: 300;")

        self.options_btn = QPushButton()
        self.options_btn.setCursor(Qt.PointingHandCursor)
        self.options_btn.setProperty("cssClass", "breadcrumb-btn")

        self.tool_menu = QMenu(self)
        self._style_menu(self.tool_menu)

        self.lang_menu = QMenu(self)
        self._style_menu(self.lang_menu)
        self.action_en = self.lang_menu.addAction("English")
        self.action_as = self.lang_menu.addAction("Assamese")
        self.action_en.triggered.connect(lambda: self.change_language_sig.emit("en"))
        self.action_as.triggered.connect(lambda: self.change_language_sig.emit("as"))

        self.theme_menu = QMenu(self)
        self._style_menu(self.theme_menu)
        self.action_light = self.theme_menu.addAction(self.tr("Light"))
        self.action_dark = self.theme_menu.addAction(self.tr("Dark"))
        self.action_light.triggered.connect(lambda: self.change_theme_sig.emit("light"))
        self.action_dark.triggered.connect(lambda: self.change_theme_sig.emit("dark"))

        self.update_menu = QMenu(self)
        self._style_menu(self.update_menu)
        self.action_check_updates = self.update_menu.addAction(self.tr("Check for Updates"))
        self.action_check_updates.triggered.connect(self.check_updates_sig.emit)
        self.action_auto_updates = self.update_menu.addAction(self.tr("Check on Startup"))
        self.action_auto_updates.setCheckable(True)
        self.action_auto_updates.toggled.connect(self.auto_update_toggled_sig.emit)

        self.options_btn.setMenu(self.tool_menu)
        self.bc_layout.addWidget(self.category_btn)
        self.bc_layout.addWidget(self.separator)
        self.bc_layout.addWidget(self.options_btn)

        self.set_category(self.current_category)

    def _menu_label(self, text: str) -> str:
        return f"{text}  ▾"

    def _style_menu(self, menu):
        menu.setStyleSheet(
            """
            QMenu {
                background-color: #252526;
                color: #cccccc;
                border: 1px solid #3e3e42;
                border-radius: 6px;
                font-family: "Segoe UI", sans-serif;
                font-size: 9pt;
                padding: 4px 0px;
                margin-top: 6px;
            }
            QMenu::item { padding: 6px 32px 6px 24px; }
            QMenu::item:selected { background-color: #094771; color: white; border-radius: 4px; margin: 0px 4px; }
            """
        )

    def _update_breadcrumb_position(self):
        bc_width = self.breadcrumb_pill.sizeHint().width()
        bc_height = self.breadcrumb_pill.sizeHint().height()
        x_center = (self.width() - bc_width) // 2
        y_center = (self.height() - bc_height) // 2
        self.breadcrumb_pill.setGeometry(x_center, y_center, bc_width, bc_height)

    def set_category(self, category_key):
        self.current_category = category_key

        if category_key == "tool":
            self.category_btn.setText(self._menu_label(self.tr("Select Tool")))
            self.options_btn.setMenu(self.tool_menu)
            stack = getattr(self.parent_window, "stack", None)
            tools = getattr(self.parent_window, "tools", [])
            if stack is None or stack.count() == 0:
                self.options_btn.setText(self._menu_label(self.tr("Select IDE")))
            else:
                idx = stack.currentIndex()
                if 0 <= idx < len(tools):
                    self.options_btn.setText(self._menu_label(tools[idx].get_name()))
                else:
                    self.options_btn.setText(self._menu_label(self.tr("Select IDE")))
        elif category_key == "language":
            self.category_btn.setText(self._menu_label(self.tr("Language")))
            self.options_btn.setMenu(self.lang_menu)
            self.options_btn.setText(self._menu_label(self.tr("Choose Language")))
        elif category_key == "theme":
            self.category_btn.setText(self._menu_label(self.tr("Theme")))
            self.options_btn.setMenu(self.theme_menu)
            self.options_btn.setText(self._menu_label(self.tr("Choose Theme")))
        elif category_key == "updates":
            self.category_btn.setText(self._menu_label(self.tr("Updates")))
            self.options_btn.setMenu(self.update_menu)
            self.options_btn.setText(self._menu_label(self.tr("Actions")))

        self._update_breadcrumb_position()

    def retranslate_ui(self):
        self.action_cat_tool.setText(self.tr("Select Tool"))
        self.action_cat_lang.setText(self.tr("Language"))
        self.action_cat_theme.setText(self.tr("Theme"))
        self.action_cat_updates.setText(self.tr("Updates"))
        self.action_light.setText(self.tr("Light"))
        self.action_dark.setText(self.tr("Dark"))
        self.action_check_updates.setText(self.tr("Check for Updates"))
        self.action_auto_updates.setText(self.tr("Check on Startup"))
        self.set_category(self.current_category)

    def set_auto_update_enabled(self, enabled: bool):
        previous = self.action_auto_updates.blockSignals(True)
        self.action_auto_updates.setChecked(enabled)
        self.action_auto_updates.blockSignals(previous)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_breadcrumb_position()

    def toggle_maximize(self):
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
            self.max_btn.setText("◻")
            # Turn rounded corners BACK ON when restoring to normal size
            set_windows_rounded_corners(self.parent_window.winId(), True)
        else:
            self.parent_window.showMaximized()
            self.max_btn.setText("❐")
            # Turn rounded corners OFF when maximizing to get a flush fit
            set_windows_rounded_corners(self.parent_window.winId(), False)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.parent_window.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() == Qt.LeftButton:
            if self.parent_window.isMaximized():
                self.parent_window.showNormal()
                self.max_btn.setText("◻")
                set_windows_rounded_corners(self.parent_window.winId(), True)
                self._drag_pos = QPoint(self.width() // 2, event.pos().y())

            self.parent_window.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_maximize()


class UpdateCheckWorker(QObject):
    finished = Signal(object, object, bool)

    def __init__(self, manifest_url: str, release_channel: str, silent: bool):
        super().__init__()
        self.manifest_url = manifest_url
        self.release_channel = release_channel
        self.silent = silent

    def run(self):
        try:
            result = check_for_updates(self.manifest_url, self.release_channel)
            self.finished.emit(result, None, self.silent)
        except Exception as exc:
            self.finished.emit(None, exc, self.silent)


class UpdateDownloadWorker(QObject):
    finished = Signal(object, object)

    def __init__(self, asset):
        super().__init__()
        self.asset = asset

    def run(self):
        try:
            installer_path = download_asset(self.asset)
            self.finished.emit(installer_path, None)
        except Exception as exc:
            self.finished.emit(None, exc)


class StemShell(QMainWindow):
    def __init__(self):
        super().__init__()

        self.app_translator = QTranslator()

        # Preserve the standard top-level window hints so Windows still treats
        # this frameless shell as a regular taskbar window.
        self.setWindowFlags(
            self.windowFlags()
            | Qt.Window
            | Qt.WindowSystemMenuHint
            | Qt.WindowMinMaxButtonsHint
            | Qt.WindowCloseButtonHint
            | Qt.FramelessWindowHint
        )
        self.setWindowTitle("MESC")

        icon_path = get_app_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))

        self.resize(1400, 900)

        self.central_widget = QWidget()
        self.central_widget.setObjectName("AppCentralWidget")
        self.central_widget.setStyleSheet(
            "QWidget#AppCentralWidget { background-color: #1e1e1e; }"
        )
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self)
        self.main_layout.addWidget(self.title_bar)
        self.title_bar.change_language_sig.connect(self.switch_language)
        self.title_bar.change_theme_sig.connect(self.switch_theme)
        self.title_bar.check_updates_sig.connect(self.check_for_updates_interactive)
        self.title_bar.auto_update_toggled_sig.connect(self.set_auto_check_updates)
        self.title_bar.set_auto_update_enabled(AppConfig.get_auto_check_updates())

        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack)

        self.tools = []
        self.tool_widgets = []
        self._update_thread = None
        self._update_worker = None
        self._download_thread = None
        self._download_worker = None

        saved_lang = AppConfig.get_language()
        self.switch_language(saved_lang)

        if AppConfig.get_auto_check_updates():
            QTimer.singleShot(2500, self.check_for_updates_silent)

        self.switch_theme(AppConfig.get_theme_mode())

    def switch_language(self, lang_code):
        AppConfig.set_language(lang_code)

        app = QApplication.instance()
        if lang_code == "as":
            translation_path = get_resource_path("translations/mesc_as.qm")
            if self.app_translator.load(translation_path):
                app.installTranslator(self.app_translator)
            else:
                print(f"Notice: Assamese translation file not compiled yet at {translation_path}")
        else:
            app.removeTranslator(self.app_translator)

        if self.title_bar.current_category == "language":
            display_text = "Assamese" if lang_code == "as" else "English"
            self.title_bar.options_btn.setText(self.title_bar._menu_label(display_text))
        else:
            self.title_bar.set_category(self.title_bar.current_category)

        self.title_bar._update_breadcrumb_position()

    def switch_theme(self, theme_mode):
        AppConfig.set_theme_mode(theme_mode)
        if theme_mode == "light":
            self.central_widget.setStyleSheet(
                "QWidget#AppCentralWidget { background-color: #f3f3f3; }"
            )
            self.stack.setStyleSheet("QStackedWidget { background-color: #f3f3f3; }")
        else:
            self.central_widget.setStyleSheet(
                "QWidget#AppCentralWidget { background-color: #1e1e1e; }"
            )
            self.stack.setStyleSheet("QStackedWidget { background-color: #1e1e1e; }")

        if self.title_bar.current_category == "theme":
            display_text = self.tr("Light") if theme_mode == "light" else self.tr("Dark")
            self.title_bar.options_btn.setText(self.title_bar._menu_label(display_text))
        self.title_bar._update_breadcrumb_position()

    def set_auto_check_updates(self, enabled: bool):
        AppConfig.set_auto_check_updates(enabled)
        self.title_bar.set_auto_update_enabled(enabled)

    def check_for_updates_silent(self):
        self._start_update_check(silent=True)

    def check_for_updates_interactive(self):
        self._start_update_check(silent=False)

    def _start_update_check(self, silent: bool):
        if self._update_thread is not None:
            return

        self._update_thread = QThread(self)
        self._update_worker = UpdateCheckWorker(
            AppConfig.get_update_manifest_url(),
            AppConfig.get_release_channel(),
            silent,
        )
        self._update_worker.moveToThread(self._update_thread)
        self._update_thread.started.connect(self._update_worker.run)
        self._update_worker.finished.connect(self._handle_update_result)
        self._update_worker.finished.connect(self._cleanup_update_thread)
        self._update_thread.start()

    def _handle_update_result(self, result, error, silent: bool):
        if error is not None:
            if not silent:
                QMessageBox.warning(self, "Update Check Failed", str(error))
            return

        if result is None:
            return

        if not result.update_available:
            if not silent:
                QMessageBox.information(
                    self,
                    "MESC is Up to Date",
                    f"You are already running the latest version ({result.current_version}).",
                )
            return

        skipped_version = AppConfig.get_skipped_version()
        if silent and skipped_version == result.latest_version:
            return

        if result.asset is None:
            if not silent:
                QMessageBox.information(
                    self,
                    "Update Available",
                    (
                        f"MESC {result.latest_version} is available, but there is no installer asset "
                        f"for this platform in the release manifest."
                    ),
                )
            return

        notes = result.manifest.notes if result.manifest else ""
        details = (
            f"Current version: {result.current_version}\n"
            f"Latest version: {result.latest_version}\n\n"
            f"{notes or 'A new version of MESC is available.'}"
        )

        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Information)
        dialog.setWindowTitle("Update Available")
        dialog.setText(details)
        update_button = dialog.addButton("Download and Install", QMessageBox.AcceptRole)
        skip_button = dialog.addButton("Skip This Version", QMessageBox.DestructiveRole)
        later_button = dialog.addButton("Later", QMessageBox.RejectRole)
        dialog.exec()

        clicked = dialog.clickedButton()
        if clicked == update_button:
            self._download_update_asset(result.asset)
        elif clicked == skip_button:
            AppConfig.set_skipped_version(result.latest_version)
        elif clicked == later_button:
            return

    def _cleanup_update_thread(self, *_args):
        if self._update_thread is not None:
            self._update_thread.quit()
            self._update_thread.wait()
        self._update_thread = None
        self._update_worker = None

    def _download_update_asset(self, asset):
        if self._download_thread is not None:
            return

        self._download_thread = QThread(self)
        self._download_worker = UpdateDownloadWorker(asset)
        self._download_worker.moveToThread(self._download_thread)
        self._download_thread.started.connect(self._download_worker.run)
        self._download_worker.finished.connect(self._handle_download_result)
        self._download_worker.finished.connect(self._cleanup_download_thread)
        self._download_thread.start()

    def _handle_download_result(self, installer_path, error):
        if error is not None:
            QMessageBox.warning(self, "Update Download Failed", str(error))
            return

        if installer_path is None:
            return

        if platform.system() == "Windows":
            answer = QMessageBox.question(
                self,
                "Ready to Install Update",
                (
                    "The update installer has been verified and downloaded.\n\n"
                    "MESC will close and launch the installer."
                ),
            )
            if answer == QMessageBox.StandardButton.Yes:
                subprocess.Popen([str(installer_path)])
                QApplication.instance().quit()
        else:
            webbrowser.open(installer_path.as_uri())

    def _cleanup_download_thread(self, *_args):
        if self._download_thread is not None:
            self._download_thread.quit()
            self._download_thread.wait()
        self._download_thread = None
        self._download_worker = None

    def changeEvent(self, event):
        if event.type() == QEvent.Type.LanguageChange:
            self.title_bar.retranslate_ui()
        super().changeEvent(event)

    def register_tool(self, tool):
        index = len(self.tools)
        self.tools.append(tool)
        placeholder = QWidget()
        placeholder.setStyleSheet("background-color: #1e1e1e;")
        self.tool_widgets.append(None)
        self.stack.addWidget(placeholder)

        action = self.title_bar.tool_menu.addAction(tool.get_name())
        action.triggered.connect(lambda checked=False, idx=index: self.switch_tool(idx))

        if index == 0:
            self.switch_tool(0)

    def switch_tool(self, index):
        old_index = self.stack.currentIndex()
        is_maximized = self.isMaximized() # 1. Capture current state

        if 0 <= old_index < len(self.tools) and self.tool_widgets[old_index] is not None:
            self.tools[old_index].on_deactivate()

        if self.tool_widgets[index] is None:
            placeholder = self.stack.widget(index)
            widget = self.tools[index].get_widget()
            self.stack.removeWidget(placeholder)
            placeholder.deleteLater()
            self.stack.insertWidget(index, widget)
            self.tool_widgets[index] = widget

        self.stack.setCurrentIndex(index)
        active_tool = self.tools[index]
        active_tool.on_activate()
        active_widget = self.tool_widgets[index]
        if hasattr(active_widget, "_refresh_plot_dock"):
            QTimer.singleShot(0, active_widget._refresh_plot_dock)

        # 2. FIX: Force DWM to restore the flush maximized frameless state
        if is_maximized:
            self.showNormal()
            self.showMaximized()
            from app_platform.ui_shell.app_shell import set_windows_rounded_corners
            set_windows_rounded_corners(self.winId(), False) 

        if self.title_bar.current_category == "tool":
            self.title_bar.options_btn.setText(
                self.title_bar._menu_label(active_tool.get_name())
            )
        self.title_bar._update_breadcrumb_position()

    def closeEvent(self, event):
        for widget in self.tool_widgets:
            if widget is None:
                continue
            if hasattr(widget, "closeEvent"):
                close_evt = QCloseEvent()
                widget.closeEvent(close_evt)
        event.accept()
