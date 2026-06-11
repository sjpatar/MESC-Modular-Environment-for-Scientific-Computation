from PySide6.QtWidgets import QMenuBar, QMessageBox
from PySide6.QtGui import QAction
from PySide6.QtCore import QObject, Signal, QEvent

from ides.mathex.ui.guide import GuideDialog

class MenuSignals(QObject):
    new_file = Signal()
    open_file = Signal()
    save_file = Signal()
    save_as = Signal()
    close_file = Signal()
    run_script = Signal()
    debug_script = Signal()

    undo = Signal()
    redo = Signal()
    cut = Signal()
    copy = Signal()
    paste = Signal()
    select_all = Signal()

    toggle_files = Signal(bool)
    toggle_console = Signal(bool)
    toggle_workspace = Signal(bool)
    toggle_plots = Signal(bool)

class MainMenuBar(QMenuBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent 
        self.signals = MenuSignals()
        self.build_menus()
        self.retranslate_ui() # Load text immediately

    def build_menus(self):
        # ---------- MENUS ----------
        self.file_menu = self.addMenu("")
        self.edit_menu = self.addMenu("")
        self.view_menu = self.addMenu("")
        self.run_menu = self.addMenu("")
        self.help_menu = self.addMenu("")

        # ---------- FILE ----------
        self.new_action = QAction("", self)
        self.new_action.setShortcut("Ctrl+N")
        self.new_action.triggered.connect(self.signals.new_file.emit)
        self.file_menu.addAction(self.new_action)

        self.open_action = QAction("", self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self.signals.open_file.emit)
        self.file_menu.addAction(self.open_action)

        self.save_action = QAction("", self)
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.triggered.connect(self.signals.save_file.emit)
        self.file_menu.addAction(self.save_action)

        self.save_as_action = QAction("", self)
        self.save_as_action.triggered.connect(self.signals.save_as.emit)
        self.file_menu.addAction(self.save_as_action)

        self.file_menu.addSeparator()

        self.close_action = QAction("", self)
        self.close_action.setShortcut("Ctrl+W")
        self.close_action.triggered.connect(self.signals.close_file.emit)
        self.file_menu.addAction(self.close_action)

        self.file_menu.addSeparator()

        self.exit_action = QAction("", self)
        self.exit_action.setShortcut("Alt+F4")
        self.exit_action.triggered.connect(self.parent().close)
        self.file_menu.addAction(self.exit_action)

        # ---------- EDIT ----------
        self.undo_action = QAction("", self)
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.triggered.connect(self.signals.undo.emit)
        self.edit_menu.addAction(self.undo_action)

        self.redo_action = QAction("", self)
        self.redo_action.setShortcut("Ctrl+Y")
        self.redo_action.triggered.connect(self.signals.redo.emit)
        self.edit_menu.addAction(self.redo_action)

        self.edit_menu.addSeparator()

        self.cut_action = QAction("", self)
        self.cut_action.setShortcut("Ctrl+X")
        self.cut_action.triggered.connect(self.signals.cut.emit)
        self.edit_menu.addAction(self.cut_action)

        self.copy_action = QAction("", self)
        self.copy_action.setShortcut("Ctrl+C")
        self.copy_action.triggered.connect(self.signals.copy.emit)
        self.edit_menu.addAction(self.copy_action)

        self.paste_action = QAction("", self)
        self.paste_action.setShortcut("Ctrl+V")
        self.paste_action.triggered.connect(self.signals.paste.emit)
        self.edit_menu.addAction(self.paste_action)

        self.select_all_action = QAction("", self)
        self.select_all_action.setShortcut("Ctrl+A")
        self.select_all_action.triggered.connect(self.signals.select_all.emit)
        self.edit_menu.addAction(self.select_all_action)

        # ---------- VIEW ----------
        self.files_action = QAction("", self, checkable=True, checked=True)
        self.files_action.triggered.connect(lambda c: self.signals.toggle_files.emit(c))
        self.view_menu.addAction(self.files_action)

        self.console_action = QAction("", self, checkable=True, checked=True)
        self.console_action.triggered.connect(lambda c: self.signals.toggle_console.emit(c))
        self.view_menu.addAction(self.console_action)

        self.workspace_action = QAction("", self, checkable=True, checked=True)
        self.workspace_action.triggered.connect(lambda c: self.signals.toggle_workspace.emit(c))
        self.view_menu.addAction(self.workspace_action)

        self.plot_action = QAction("", self, checkable=True, checked=True)
        self.plot_action.triggered.connect(lambda c: self.signals.toggle_plots.emit(c))
        self.view_menu.addAction(self.plot_action)

        # ---------- RUN ----------
        self.run_script_action = QAction("", self)
        self.run_script_action.setShortcut("F5")
        self.run_script_action.triggered.connect(self.signals.run_script.emit)
        self.run_menu.addAction(self.run_script_action)

        self.debug_script_action = QAction("", self)
        self.debug_script_action.setShortcut("F9")
        self.debug_script_action.triggered.connect(self.signals.debug_script.emit)
        self.run_menu.addAction(self.debug_script_action)

        # ---------- HELP ----------
        self.guide_action = QAction("", self)
        self.guide_action.setShortcut("F1")
        self.guide_action.triggered.connect(self._show_guide)
        self.help_menu.addAction(self.guide_action)
        
        self.help_menu.addSeparator()
        
        self.about_action = QAction("", self)
        self.about_action.triggered.connect(self._show_about)
        self.help_menu.addAction(self.about_action)

    def changeEvent(self, event):
        """Intercept language changes and refresh text."""
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate_ui()
        super().changeEvent(event)

    def retranslate_ui(self):
        """Apply translated strings to all visible items."""
        # Menus
        self.file_menu.setTitle(self.tr("File"))
        self.edit_menu.setTitle(self.tr("Edit"))
        self.view_menu.setTitle(self.tr("View"))
        self.run_menu.setTitle(self.tr("Run"))
        self.help_menu.setTitle(self.tr("Help"))

        # File Menu Items
        self.new_action.setText(self.tr("New"))
        self.open_action.setText(self.tr("Open..."))
        self.save_action.setText(self.tr("Save"))
        self.save_as_action.setText(self.tr("Save As..."))
        self.close_action.setText(self.tr("Close File"))
        self.exit_action.setText(self.tr("Exit"))

        # Edit Menu Items
        self.undo_action.setText(self.tr("Undo"))
        self.redo_action.setText(self.tr("Redo"))
        self.cut_action.setText(self.tr("Cut"))
        self.copy_action.setText(self.tr("Copy"))
        self.paste_action.setText(self.tr("Paste"))
        self.select_all_action.setText(self.tr("Select All"))

        # View Menu Items
        self.files_action.setText(self.tr("Current Folder"))
        self.console_action.setText(self.tr("Command Window"))
        self.workspace_action.setText(self.tr("Workspace"))
        self.plot_action.setText(self.tr("Figures"))

        # Run Menu Items
        self.run_script_action.setText(self.tr("Run Script"))
        self.debug_script_action.setText(self.tr("Debug Script"))

        # Help Menu Items
        self.guide_action.setText(self.tr("User Guide"))
        self.about_action.setText(self.tr("About Mathex"))

    def _show_guide(self):
        try:
            dialog = GuideDialog(self.parent_window)
            dialog.exec()
        except Exception as e:
            print(f"Error launching guide: {e}")

    def _show_about(self):
        QMessageBox.about(
            self, 
            self.tr("About Mathex"),
            "<h3>Mathex Environment</h3>"
            "<p>A professional, MATLAB-compatible Python IDE.</p>"
            "<p><b>Version:</b> 0.1.0-Alpha</p>"
            "<p>Built with PySide6 & NumPy.</p>"
            "<p>Author: <b>Samarjit Patar</b></p>"
        )

    def invoke_editor_action(self, action_name: str):
        parent = self.parent_window
        if parent is None or not hasattr(parent, "editor"):
            return

        editor = parent.editor.current_editor()
        if editor is None or not hasattr(editor, action_name):
            return

        getattr(editor, action_name)()
