from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTableView, QHeaderView, QLabel
)
from PySide6.QtCore import Qt, Signal, QAbstractTableModel, QModelIndex, QEvent
import numpy as np
from ides.mathex.language.locale import tr

# [NEW] Import MatlabArray to check types if needed, or rely on duck typing
# from shared.symbolic_core.arrays import MatlabArray 

class ArrayModel(QAbstractTableModel):
    """
    Virtual Model that allows displaying 1,000,000+ cells instantly.
    """
    def __init__(self, data):
        super().__init__()
        self._data = data

    def rowCount(self, parent=QModelIndex()):
        if self._data is None: return 0
        if self._data.ndim == 0: return 1
        return self._data.shape[0]

    def columnCount(self, parent=QModelIndex()):
        if self._data is None: return 0
        if self._data.ndim < 2: return 1
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        
        row, col = index.row(), index.column()

        if role == Qt.DisplayRole or role == Qt.EditRole:
            # Safe Access logic
            if self._data.ndim == 0:
                val = self._data[()]
            elif self._data.ndim == 1:
                val = self._data[row]
            else:
                val = self._data[row, col]
                
            # [UPDATED] Formatting
            if isinstance(val, (float, np.floating)):
                return f"{val:.4f}"
            if isinstance(val, (complex, np.complexfloating)):
                # MATLAB Style: 1.0000 + 2.0000i
                op = "+" if val.imag >= 0 else "-"
                return f"{val.real:.4f} {op} {abs(val.imag):.4f}i"
            return str(val)
            
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole: return False
        
        row, col = index.row(), index.column()
        
        try:
            # Type Inference (Basic)
            # Replace 'i' with 'j' for Python parsing
            py_val = value.replace('i', 'j') if 'i' in value else value
            
            if 'j' in py_val: new_val = complex(py_val)
            elif '.' in py_val: new_val = float(py_val)
            else: new_val = int(py_val)
            
            if self._data.ndim == 0:
                self._data[()] = new_val
            elif self._data.ndim == 1:
                self._data[row] = new_val
            else:
                self._data[row, col] = new_val
            
            self.dataChanged.emit(index, index, [Qt.DisplayRole])
            return True
        except ValueError:
            return False

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            # MATLAB uses 1-based indexing
            return str(section + 1)
        return None

class VariableInspector(QDialog):
    """
    High-Performance Variable Inspector.
    Supports: Scalars, Vectors, Matrices, ND-Arrays (Slice View).
    """
    value_changed = Signal(object)

    def __init__(self, name, value, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("variable_inspector_title", name=name))
        self.resize(700, 500)
        
        self.var_name = name
        
        # [UPDATED] Robust Unwrap: Handle MatlabArray, standard lists, or raw numpy
        self.raw_data = self._unwrap_value(value)

        # Ensure NumPy array for the model
        if not isinstance(self.raw_data, np.ndarray):
            self.raw_data = np.array(self.raw_data)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        
        # Info Label
        self.info_label = QLabel()
        self.info_label.setStyleSheet("""
            background-color: #252526; color: #888; 
            font-style: italic; padding: 5px; border-bottom: 1px solid #333;
        """)
        self.layout.addWidget(self.info_label)

       # High-Performance Table View
        self.table = QTableView()
        
        # [FIX] UI STRESS TEST: Prevent 10+ second freeze for large matrices (1000x1000+)
        self.table.setUniformRowHeights(True) 
        
        # [FIX] Upgraded to strictly scoped enums to prevent PySide6 AttributeErrors
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setDefaultSectionSize(80)
        self.table.verticalHeader().setDefaultSectionSize(25)
        
        self.table.setStyleSheet("""
            QTableView {
                background-color: #1e1e1e; color: #ffffff;
                gridline-color: #444; selection-background-color: #264f78;
                border: none;
            }
            QHeaderView::section {
                background-color: #2b2b2b; color: #ccc;
                padding: 4px; border: 1px solid #333;
            }
            QTableCornerButton::section { background-color: #2b2b2b; border: 1px solid #333; }
        """)
        self.layout.addWidget(self.table)
        
        self.load_data()

    def changeEvent(self, event):
        if event.type() == QEvent.Type.LanguageChange:
            self.setWindowTitle(tr("variable_inspector_title", name=self.var_name))
            self.load_data()
        super().changeEvent(event)

    def _unwrap_value(self, value):
        """Extracts raw data from MatlabArray or wrappers."""
        if hasattr(value, "_data"):
            return value._data
        return value

    def load_data(self):
        arr = self.raw_data
        
        # Handle Slicing for ND Arrays (Show first 2D slice)
        if arr.ndim > 2:
            extra_dims = arr.ndim - 2
            view_arr = arr
            # Peel dimensions until 2D
            for _ in range(extra_dims): view_arr = view_arr[..., 0]
            
            slice_desc = f"[:,:,{','.join(['1']*extra_dims)}]" # 1-based display
            self.info_label.setText(
                " " + tr("variable_inspector_displaying", slice_desc=slice_desc, shape=arr.shape)
            )
            self.model = ArrayModel(view_arr)
        else:
            self.model = ArrayModel(arr)
            shape_str = f"{arr.shape[0]}x{arr.shape[1]}" if arr.ndim == 2 else str(arr.shape)
            self.info_label.setText(
                " " + tr("variable_inspector_size_class", shape=shape_str, dtype=arr.dtype)
            )

        self.table.setModel(self.model)
        self.model.dataChanged.connect(self._on_data_changed)
    
    def _on_data_changed(self):
        self.value_changed.emit(self.raw_data)
