# mathex/ui/workspace.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
    QToolButton, QTableWidget, QTableWidgetItem, 
    QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtGui import QColor, QBrush
import types
from ides.mathex.language.locale import tr

# IMPORT THE INSPECTOR
from ides.mathex.ui.variable_inspector import VariableInspector

class WorkspaceWidget(QWidget):
    """
    Professional Workspace with Tabular Borders and Inspector.
    """
    
    # Define Signals for the Toolbar Actions
    clear_requested = Signal()
    save_requested = Signal()
    load_requested = Signal()
    
    # Signal emitted when a variable is modified in the inspector
    variable_edited = Signal(str, object)

    def __init__(self):
        super().__init__()
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # --- Toolbar ---
        self.toolbar = QWidget()
        self.toolbar.setStyleSheet("background-color: #252526; border-bottom: 1px solid #333;")
        tb_layout = QHBoxLayout(self.toolbar)
        tb_layout.setContentsMargins(4, 4, 4, 4)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText(tr("workspace_filter"))
        self.search_bar.setStyleSheet("""
            QLineEdit {
                background: #333333;
                color: #cccccc;
                border: 1px solid #3e3e42;
                padding: 2px 4px;
            }
            QLineEdit:focus { border: 1px solid #007acc; }
        """)
        self.search_bar.textChanged.connect(lambda: self.filter_table(self.search_bar.text()))
        tb_layout.addWidget(self.search_bar)
        
        # Connect buttons to signals
        actions = [
            ("clear", self.clear_requested),
            ("save", self.save_requested),
            ("load", self.load_requested),
        ]

        self._toolbar_buttons = []
        for text_key, signal in actions:
            btn = QToolButton()
            btn.setText(tr(text_key))
            btn.setStyleSheet("QToolButton{color:#ccc;background:transparent;padding:2px;} QToolButton:hover{background:#3e3e42;}")
            
            # Connect the click to the signal emission
            btn.clicked.connect(signal.emit)
            
            tb_layout.addWidget(btn)
            self._toolbar_buttons.append((btn, text_key))
            
        self.layout.addWidget(self.toolbar)

        # --- Table ---
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([tr("name"), tr("value"), tr("class")])
        self.table.setShowGrid(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                color: #cccccc;
                gridline-color: #333333; 
                border: none;
            }
            QTableWidget::item { padding: 4px; border-bottom: 1px solid #2d2d2d; }
            QHeaderView::section {
                background-color: #252526;
                color: #cccccc;
                padding: 4px;
                border: 1px solid #333333;
                font-weight: bold;
            }
        """)
        self.table.setColumnWidth(0, 100)
        self.table.setColumnWidth(1, 150)
        
        # CONNECT DOUBLE CLICK TO INSPECTOR
        self.table.cellDoubleClicked.connect(self.on_table_double_click)
        
        self.layout.addWidget(self.table)
        self.current_globals = {}

    def changeEvent(self, event):
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate_ui()
        super().changeEvent(event)

    def retranslate_ui(self):
        self.search_bar.setPlaceholderText(tr("workspace_filter"))
        self.table.setHorizontalHeaderLabels([tr("name"), tr("value"), tr("class")])
        for btn, text_key in getattr(self, "_toolbar_buttons", []):
            btn.setText(tr(text_key))

    def update_table(self, globals_dict):
        self.current_globals = globals_dict.copy()
        self.filter_table(self.search_bar.text())

    def filter_table(self, query):
        query = query.lower()
        vars_to_show = {}
        for k, v in self.current_globals.items():
            if k.startswith('_'): continue
            
            # [MODIFIED] Show functions but hide standard Python modules (like 'os', 'sys')
            if isinstance(v, types.ModuleType): 
                continue
                
            if query in k.lower():
                vars_to_show[k] = v
        
        self.table.setRowCount(len(vars_to_show))
        
        error_color = QColor("#ff5555")
        
        # [NEW] Define "Shades of Dark" for row backgrounds
        bg_func = QColor("#2a2b2e")   # Lighter, slightly cool dark for functions
        bg_char = QColor("#232323")   # Subtle difference for strings/text
        bg_var  = QColor("#1e1e1e")   # Standard deep dark for variables
        
        # Text color for function values (dimmed)
        func_val_color = QColor("#777777")

        for row, (name, val) in enumerate(sorted(vars_to_show.items())):
            # 1. Determine Type & Background Color
            is_matlab_array = hasattr(val, '_data') and hasattr(val, 'shape')
            is_func = not is_matlab_array and (callable(val) or isinstance(val, type))
            is_str = isinstance(val, str)
            
            if is_func:   row_bg = bg_func
            elif is_str:  row_bg = bg_char
            else:         row_bg = bg_var

            # 2. Name Column
            item_name = QTableWidgetItem(name)
            item_name.setBackground(row_bg)
            self.table.setItem(row, 0, item_name)
            
            # 3. Value Column
            try: 
                val_str = self._format_value(val)
                is_error = False
            except: 
                val_str = tr("error")
                is_error = True
            
            item_val = QTableWidgetItem(val_str)
            item_val.setBackground(row_bg)
            
            if is_error or val_str == tr("error"):
                item_val.setForeground(error_color)
                item_val.setToolTip(tr("unable_display_value"))
            elif is_func:
                # Dim the function value text (e.g. <function_handle>)
                item_val.setForeground(func_val_color)

            self.table.setItem(row, 1, item_val)
            
            # 4. Class Column (MATLAB Naming)
            t_name = type(val).__name__
            if t_name == 'MatlabArray': t_name = 'double'
            elif is_func: t_name = 'function_handle'
            elif is_str: t_name = 'char'
            elif t_name == 'list': t_name = 'cell' # Python list roughly maps to cell array conceptually
            
            item_class = QTableWidgetItem(t_name)
            item_class.setBackground(row_bg)
            self.table.setItem(row, 2, item_class)

    def _format_value(self, val):
        # Arrays/Shapes
        if hasattr(val, 'shape'):
             if isinstance(val.shape, (tuple, list)):
                 dims = 'x'.join(map(str, val.shape))
                 # If it's small, show value? For now, stick to standard workspace summary
                 return f"<{dims} double>" 
        
        # Numbers
        if isinstance(val, (int, float, complex)): 
            return str(val)
        
        # Functions
        if callable(val) and not hasattr(val, '_data'): 
            # If it has a __name__, show it, otherwise generic handle
            if hasattr(val, '__name__'):
                return f"@{val.__name__}"
            return "<function_handle>"
            
        return str(val)[:50]

    # --- INSPECTOR LOGIC ---
    def on_table_double_click(self, row, col):
        # Get variable name from first column
        item = self.table.item(row, 0)
        if not item: return
        name = item.text()
        
        val = self.current_globals.get(name)
        if val is not None:
            # Launch Inspector
            dlg = VariableInspector(name, val, self)
            
            # Handle edits
            dlg.value_changed.connect(lambda new_val: self._handle_var_update(name, new_val))
            
            dlg.exec()

    def _handle_var_update(self, name, new_val):
        """Called when inspector emits a change."""
        # 1. Update local copy so table refreshes correctly
        self.current_globals[name] = new_val
        
        # 2. Refresh the table (simple way)
        self.filter_table(self.search_bar.text())
        
        # 3. Emit signal so App can update the real Kernel Session
        self.variable_edited.emit(name, new_val)

    def highlight_rows(self, row_indices):
        """
        Highlight visible workspace rows that correspond to selected plot indices.
        Indices are zero-based, matching Plotly pointIndex/customdata semantics.
        """
        try:
            indices = sorted({int(idx) for idx in row_indices if idx is not None})
        except Exception:
            indices = []

        self.table.clearSelection()
        if not indices:
            return

        row_count = self.table.rowCount()
        for idx in indices:
            if 0 <= idx < row_count:
                self.table.selectRow(idx)

        first = next((idx for idx in indices if 0 <= idx < row_count), None)
        if first is not None:
            item = self.table.item(first, 0)
            if item is not None:
                self.table.scrollToItem(item)
