from pathlib import Path
from PySide6.QtWidgets import QTabWidget, QFileDialog, QMessageBox
from PySide6.QtCore import Qt

from .codeeditor import CodeEditor


class ScriptEditor(QTabWidget):
    """
    MATLAB-like multi-file M-editor:
    - Multiple tabs
    - New files
    - Close tabs
    - Get current filename + code
    - [NEW] Breakpoint management
    """
    def __init__(self):
        super().__init__()

        self.setTabsClosable(True)
        self.setMovable(True)

        self.tabCloseRequested.connect(self.close_tab)

        # FIX: Updated CSS to prevent tab overlapping and achieve a true VS Code look
        self.setStyleSheet("""
            QTabWidget::pane { 
                border: none; 
                border-top: 1px solid #333333; /* Crisp line separating tabs from code */
                background: #1e1e1e; 
            }
            QTabWidget::tab-bar {
                left: 0px; /* Force tabs to start flush left */
            }
            QTabBar::tab {
                background: #2d2d2d;
                color: #969696;
                padding: 8px 20px;
                border: none;
                border-right: 1px solid #252526; /* Separator between inactive tabs */
                min-width: 80px;
                font-family: "Segoe UI", sans-serif;
                font-size: 10pt;
            }
            QTabBar::tab:selected {
                background: #1e1e1e; /* Matches the editor background */
                color: #ffffff;
                border-top: 2px solid #007acc; /* VS Code style top blue highlight */
                border-right: 1px solid #333333;
                border-left: 1px solid #333333;
                margin-bottom: -1px; /* Seamlessly connects tab to the editor pane below */
            }
            QTabBar::tab:first:selected {
                border-left: none; /* Keep the far-left edge clean */
            }
            QTabBar::tab:!selected:hover { 
                background: #333333; 
                color: #e0e0e0;
            }
        """)

        self.new_file()

    def current_editor(self):
        """Returns the CodeEditor widget of the currently active tab."""
        return self.currentWidget()

    def new_file(self):
        editor = CodeEditor()
        # Attach a 'filename' attribute to the editor to track its save path
        editor.filename = None 
        idx = self.addTab(editor, "Untitled.m")
        self.setCurrentIndex(idx)
        editor.setFocus()

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "MATLAB Files (*.m);;All Files (*)"
        )
        if file_path:
            self.open_file_by_path(file_path)

    def save_current(self):
        editor = self.current_editor()
        if not editor:
            return

        # If we already have a filename, save directly; otherwise, "Save As"
        if getattr(editor, 'filename', None):
            self._save_to_path(editor, editor.filename)
        else:
            self.save_as()

    def save_as(self):
        editor = self.current_editor()
        if not editor:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save File", "Untitled.m", "MATLAB Files (*.m);;All Files (*)"
        )
        if file_path:
            self._save_to_path(editor, file_path)
            editor.filename = file_path
            self.setTabText(self.currentIndex(), Path(file_path).name)

    def _save_to_path(self, editor, path):
        try:
            Path(path).write_text(editor.toPlainText(), encoding='utf-8')
        except Exception as e:
            print(f"Error saving file: {e}")

    def close_current(self):
        idx = self.currentIndex()
        if idx != -1:
            self.close_tab(idx)

    def close_tab(self, index):
        # Prevent closing the last tab if you want to keep at least one open
        if self.count() > 1:
            self.removeTab(index)
        else:
            # If they close the last tab, just clear it or make a new one
            self.removeTab(index)
            self.new_file()

    def get_current_code(self):
        editor = self.currentWidget()
        return editor.toPlainText() if editor else ""
    
    # [FIX] Return full path if available, else tab text
    def get_current_filename(self):
        editor = self.currentWidget()
        if hasattr(editor, 'filename') and editor.filename:
            return editor.filename
        return self.tabText(self.currentIndex())

    # ----------------------------------------------------------------
    # [NEW] BREAKPOINT RETRIEVAL
    # ----------------------------------------------------------------
    def get_breakpoints(self) -> list[int]:
        """
        Returns a list of 1-based line numbers where breakpoints are set
        in the current editor.
        """
        editor = self.current_editor()
        if not editor:
            return []
        
        # 1. Try to get from editor (if implemented in CodeEditor)
        if hasattr(editor, 'get_breakpoints'):
            return editor.get_breakpoints()
            
        # 2. Try to get from editor's gutter (common pattern)
        if hasattr(editor, 'gutter') and hasattr(editor.gutter, 'get_breakpoints'):
            return editor.gutter.get_breakpoints()
            
        # 3. Fallback: No breakpoints supported yet
        return []

    def open_file_by_path(self, file_path):
        """Opens a specific file path directly without a dialog."""
        path = Path(file_path)
        if not path.exists():
            return

        # Check if already open
        for i in range(self.count()):
            editor = self.widget(i)
            if hasattr(editor, 'filename') and editor.filename == str(path):
                self.setCurrentIndex(i)
                return

        try:
            text = path.read_text(encoding='utf-8')

            current = self.current_editor()
            reuse_current = (
                current is not None
                and self.count() == 1
                and not getattr(current, 'filename', None)
                and not current.toPlainText().strip()
            )

            if reuse_current:
                editor = current
                editor.setPlainText(text)
                editor.filename = str(path)
                idx = 0
                self.setTabText(idx, path.name)
            else:
                editor = CodeEditor()
                editor.setPlainText(text)
                editor.filename = str(path)
                idx = self.addTab(editor, path.name)

            self.setCurrentIndex(idx)
            editor.setFocus()
        except Exception as e:
            print(f"Error opening file: {e}")

    def get_open_filepaths(self):
        paths = []
        for i in range(self.count()):
            editor = self.widget(i)
            # Only save tabs that point to actual files
            if hasattr(editor, 'filename') and editor.filename:
                paths.append(editor.filename)
        return paths
