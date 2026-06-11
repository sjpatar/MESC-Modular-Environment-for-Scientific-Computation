import os
import shutil
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeView, 
    QLineEdit, QToolButton, QFileSystemModel, QFileDialog,
    QHeaderView, QFileIconProvider, QMenu, QMessageBox,
    QInputDialog, QFrame, QLabel, QSizePolicy, QAbstractItemView,
    QStyle
)
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QAction, QCursor, QPen
from PySide6.QtCore import Qt, QDir, Signal, QEvent
from ides.mathex.language.locale import tr

# -----------------------------------------------------------------------------
# Minimalist Icon Generator (Vector Style)
# -----------------------------------------------------------------------------
class MinimalIcon:
    @staticmethod
    def get(name, color="#cccccc", size=24):
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)
        
        pen = QPen(QColor(color))
        pen.setWidth(2)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        c = size // 2
        
        if name == "up":
            # Up Arrow
            painter.drawLine(c, 6, c, 18)
            painter.drawLine(c - 5, 11, c, 6)
            painter.drawLine(c + 5, 11, c, 6)
            
        elif name == "folder":
            # Folder
            painter.drawRoundedRect(4, 6, 16, 12, 2, 2)
            painter.drawLine(4, 8, 10, 8) # Tab line logic simplified
            
        elif name == "trash":
            # Minimalist Trash Bin
            painter.drawRect(7, 8, 10, 11) # Body
            painter.drawLine(5, 6, 19, 6)  # Lid
            painter.drawLine(10, 4, 14, 4) # Handle
            # Vertical lines
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawLine(10, 10, 10, 17)
            painter.drawLine(14, 10, 14, 17)

        elif name == "search":
            # Magnifying Glass
            painter.drawEllipse(6, 6, 10, 10)
            painter.drawLine(14, 14, 19, 19)

        elif name == "check":
            # Checkmark
            pen.setColor(QColor("#98c379")) # Green
            painter.setPen(pen)
            painter.drawLine(6, 12, 10, 16)
            painter.drawLine(10, 16, 18, 8)

        elif name == "close":
            # X
            painter.drawLine(7, 7, 17, 17)
            painter.drawLine(17, 7, 7, 17)

        painter.end()
        return QIcon(pix)

# -----------------------------------------------------------------------------
# Checkable Model
# -----------------------------------------------------------------------------
class CheckableFileSystemModel(QFileSystemModel):
    checkStateChanged = Signal()

    def __init__(self):
        super().__init__()
        self.checked_files = set()
        self.is_checkable = False

    def setCheckable(self, state: bool):
        self.is_checkable = state
        self.checked_files.clear()
        self.layoutChanged.emit()

    def flags(self, index):
        default_flags = super().flags(index)
        if self.is_checkable and index.column() == 0:
            return default_flags | Qt.ItemIsUserCheckable
        return default_flags

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.CheckStateRole and index.column() == 0:
            if self.is_checkable:
                path = self.filePath(index)
                return Qt.Checked if path in self.checked_files else Qt.Unchecked
            return None
        return super().data(index, role)

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.CheckStateRole and index.column() == 0 and self.is_checkable:
            path = self.filePath(index)
            # [FIX] Handle both Enum and Integer comparison for PySide6
            if value == Qt.Checked or value == 2:
                self.checked_files.add(path)
            else:
                self.checked_files.discard(path)
            self.dataChanged.emit(index, index, [Qt.CheckStateRole])
            self.checkStateChanged.emit()
            return True
        return super().setData(index, value, role)
    
    def clear_checks(self):
        self.checked_files.clear()
        self.layoutChanged.emit()

# -----------------------------------------------------------------------------
# Custom Icon Provider (File Type Icons)
# -----------------------------------------------------------------------------
class MathexIconProvider(QFileIconProvider):
    def __init__(self):
        super().__init__()
        self._m_icon = self._create_m_icon()

    def _create_m_icon(self):
        size = 64
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)
        
        font = QFont("Segoe UI", 40, QFont.Bold)
        if hasattr(QFont, "Capitalization"):
            font.setCapitalization(QFont.AllUppercase)
        
        painter.setFont(font)
        painter.setPen(QColor("#e06c75")) 
        painter.drawText(pix.rect(), Qt.AlignCenter, "M")
        
        painter.end()
        return QIcon(pix)

    def icon(self, info):
        if info.isFile() and info.suffix().lower() == 'm':
            return self._m_icon
        return super().icon(info)


# -----------------------------------------------------------------------------
# File Browser Widget
# -----------------------------------------------------------------------------
class FileBrowser(QWidget):
    file_open_requested = Signal(str)
    path_changed = Signal(str)

    def __init__(self):
        super().__init__()
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # --------------------------------------------------
        # 1. Navigation & Action Bar
        # --------------------------------------------------
        self.nav_bar = QFrame()
        # [FIX] Zero spacing, compact padding, sharp borders
        self.nav_bar.setStyleSheet("""
            QFrame { 
                background: #252526; 
                border-bottom: 1px solid #333; 
            }
            QToolButton { 
                background: transparent; 
                border: 1px solid transparent; 
                border-radius: 3px; 
                padding: 3px; /* Compact padding */
                color: #cccccc; 
            }
            QToolButton:hover { 
                background: #3e3e42; 
                color: white; 
            }
            QToolButton:checked { 
                background: #094771; 
                color: white; 
            }
            QLineEdit { 
                background: #333; 
                color: #ccc; 
                border: 1px solid #3e3e42; 
                border-radius: 2px; 
                padding: 2px 4px;
                margin-left: 2px;
                margin-right: 2px;
            }
        """)
        
        nav_layout = QHBoxLayout(self.nav_bar)
        nav_layout.setContentsMargins(2, 2, 2, 2)
        nav_layout.setSpacing(0) # [FIX] Zero Spacing

        # -- Standard Nav Items --
        self.nav_items_container = QWidget()
        nav_items_layout = QHBoxLayout(self.nav_items_container)
        nav_items_layout.setContentsMargins(0,0,0,0)
        nav_items_layout.setSpacing(0) # [FIX] Zero Spacing

        self.btn_up = QToolButton()
        self.btn_up.setIcon(MinimalIcon.get("up"))
        self.btn_up.setToolTip(tr("filebrowser_up_one_level"))
        self.btn_up.clicked.connect(self.go_up)
        
        self.address_bar = QLineEdit()
        self.address_bar.returnPressed.connect(lambda: self.set_path(self.address_bar.text()))
        
        self.btn_browse = QToolButton()
        self.btn_browse.setIcon(MinimalIcon.get("folder"))
        self.btn_browse.setToolTip(tr("filebrowser_browse_folder"))
        self.btn_browse.clicked.connect(self.browse_folder)

        nav_items_layout.addWidget(self.btn_up)
        nav_items_layout.addWidget(self.address_bar)
        nav_items_layout.addWidget(self.btn_browse)

        # -- Mode Toggle Buttons --
        
        self.btn_delete_mode = QToolButton()
        self.btn_delete_mode.setIcon(MinimalIcon.get("trash")) # Custom Minimal Trash
        self.btn_delete_mode.setToolTip(tr("filebrowser_select_files_delete"))
        self.btn_delete_mode.clicked.connect(self._enter_delete_mode)

        self.action_panel = QWidget()
        self.action_panel.setVisible(False)
        action_layout = QHBoxLayout(self.action_panel)
        action_layout.setContentsMargins(0,0,0,0)
        action_layout.setSpacing(0)

        self.btn_cancel_del = QToolButton()
        self.btn_cancel_del.setIcon(MinimalIcon.get("close"))
        self.btn_cancel_del.setToolTip(tr("filebrowser_cancel_selection"))
        self.btn_cancel_del.clicked.connect(self._exit_delete_mode)
        
        self.btn_confirm_del = QToolButton()
        self.btn_confirm_del.setIcon(MinimalIcon.get("check"))
        self.btn_confirm_del.setToolTip(tr("filebrowser_delete_selected"))
        self.btn_confirm_del.clicked.connect(self._delete_checked_files)
        # Subtle red tint for delete confirm
        self.btn_confirm_del.setStyleSheet("QToolButton:hover { background: #4a2020; }")

        self.lbl_sel_count = QLabel(tr("filebrowser_selected_count", count=0))
        self.lbl_sel_count.setStyleSheet("color: #888; font-size: 11px; margin-right: 5px; padding-left: 5px;")

        action_layout.addWidget(self.lbl_sel_count)
        action_layout.addWidget(self.btn_confirm_del)
        action_layout.addWidget(self.btn_cancel_del)

        self.btn_search = QToolButton()
        self.btn_search.setIcon(MinimalIcon.get("search"))
        self.btn_search.setCheckable(True)
        self.btn_search.setToolTip(tr("filebrowser_search_current_folder"))
        self.btn_search.clicked.connect(self._toggle_search)

        nav_layout.addWidget(self.nav_items_container)
        nav_layout.addWidget(self.btn_delete_mode) 
        nav_layout.addWidget(self.action_panel)
        nav_layout.addWidget(self.btn_search)

        self.layout.addWidget(self.nav_bar)

        # --------------------------------------------------
        # 2. Search Bar
        # --------------------------------------------------
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText(tr("filebrowser_filter_files"))
        self.search_bar.setStyleSheet("""
            QLineEdit { 
                background: #1e1e1e; color: #e0e0e0; 
                border-bottom: 1px solid #333; padding: 6px;
                border-radius: 0px;
            }
        """)
        self.search_bar.setVisible(False)
        self.search_bar.textChanged.connect(self._on_search_text_changed)
        self.layout.addWidget(self.search_bar)

        # --------------------------------------------------
        # 3. File Tree
        # --------------------------------------------------
        self.model = CheckableFileSystemModel()
        self.model.setRootPath(QDir.rootPath())
        self.model.checkStateChanged.connect(self._update_selection_label)
        
        self.icon_provider = MathexIconProvider()
        self.model.setIconProvider(self.icon_provider)

        self._default_filters = ["*.m", "*.py", "*.txt", "*.mat", "*.json"]
        self.model.setNameFilters(self._default_filters)
        self.model.setNameFilterDisables(False)

        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(os.getcwd()))
        
        self.tree.hideColumn(1) 
        self.tree.hideColumn(2) 
        self.tree.hideColumn(3) 
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(True)
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        # Context Menu
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        
        self.tree.setStyleSheet("""
            QTreeView { 
                background: #1e1e1e; 
                color: #cccccc; 
                border: none; 
            }
            QTreeView::item { 
                padding: 2px 4px; 
            }
            QTreeView::item:hover { 
                background: #2a2d2e; 
            }
            QTreeView::item:selected { 
                background: #094771; 
                color: white; 
            }
            QTreeView::indicator {
                width: 14px; height: 14px;
                border: 1px solid #555;
                background: #252526;
                border-radius: 3px;
            }
            QTreeView::indicator:checked {
                background: #007acc;
                border: 1px solid #007acc;
            }
            QTreeView::indicator:checked:hover {
                background: #0098ff;
            }
        """)
        
        self.tree.doubleClicked.connect(self._on_item_double_clicked)
        self.layout.addWidget(self.tree)

        self.retranslate_ui()
        self.set_path(os.getcwd())

    def changeEvent(self, event):
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate_ui()
        super().changeEvent(event)

    def retranslate_ui(self):
        self.btn_up.setToolTip(tr("filebrowser_up_one_level"))
        self.btn_browse.setToolTip(tr("filebrowser_browse_folder"))
        self.btn_delete_mode.setToolTip(tr("filebrowser_select_files_delete"))
        self.btn_cancel_del.setToolTip(tr("filebrowser_cancel_selection"))
        self.btn_confirm_del.setToolTip(tr("filebrowser_delete_selected"))
        self.btn_search.setToolTip(tr("filebrowser_search_current_folder"))
        self.search_bar.setPlaceholderText(tr("filebrowser_filter_files"))
        self._update_selection_label()

    # -------------------------------------------------------------------------
    # Mode Switching Logic
    # -------------------------------------------------------------------------
    def _enter_delete_mode(self):
        self.model.setCheckable(True)
        self.nav_items_container.setVisible(False)
        self.btn_delete_mode.setVisible(False)
        self.action_panel.setVisible(True)
        self._update_selection_label()

    def _exit_delete_mode(self):
        self.model.setCheckable(False)
        self.model.clear_checks()
        self.action_panel.setVisible(False)
        self.btn_delete_mode.setVisible(True)
        self.nav_items_container.setVisible(True)

    def _update_selection_label(self):
        count = len(self.model.checked_files)
        self.lbl_sel_count.setText(tr("filebrowser_selected_count", count=count))
        self.btn_confirm_del.setEnabled(count > 0)

    # -------------------------------------------------------------------------
    # File Operations
    # -------------------------------------------------------------------------
    def _delete_checked_files(self):
        checked_paths = list(self.model.checked_files)
        if not checked_paths: return

        count = len(checked_paths)
        msg = QMessageBox(self)
        msg.setWindowTitle(tr("filebrowser_delete_files_title"))
        msg.setText(tr("filebrowser_delete_items_confirm", count=count))
        msg.setIcon(QMessageBox.Warning)
        
        btn_yes = msg.addButton(tr("delete"), QMessageBox.YesRole)
        btn_no = msg.addButton(tr("cancel"), QMessageBox.NoRole)
        
        msg.setStyleSheet("""
            QMessageBox { background-color: #252526; color: #e0e0e0; }
            QLabel { color: #e0e0e0; }
            QPushButton { 
                background: #3e3e42; color: white; border: none; padding: 6px 12px; 
                border-radius: 4px; min-width: 60px;
            }
            QPushButton:hover { background: #4e4e52; }
        """)

        msg.exec()

        if msg.clickedButton() == btn_yes:
            errors = []
            for path in checked_paths:
                if not os.path.exists(path): continue
                try:
                    if os.path.isdir(path): shutil.rmtree(path)
                    else: os.remove(path)
                except Exception as e:
                    errors.append(f"{os.path.basename(path)}")
            
            if errors:
                QMessageBox.warning(
                    self,
                    tr("error"),
                    tr("filebrowser_failed_delete_files", count=len(errors)),
                )
            
            self._exit_delete_mode()

    # -------------------------------------------------------------------------
    # Context Menu
    # -------------------------------------------------------------------------
    def _show_context_menu(self, position):
        index = self.tree.indexAt(position)
        if not index.isValid(): return

        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { 
                background-color: #2d2d2d; 
                color: #e0e0e0; 
                border: 1px solid #454545; 
                border-radius: 8px; 
                padding: 4px; 
            }
            QMenu::item { 
                padding: 6px 24px; 
                border-radius: 4px;
                margin: 2px;
            }
            QMenu::item:selected { 
                background-color: #094771; 
                color: white; 
            }
            QMenu::separator { 
                background-color: #454545; 
                height: 1px; 
                margin: 4px 8px;
            }
        """)
        
        rename_action = QAction(tr("rename"), self)
        rename_action.triggered.connect(lambda: self._rename_item(index))
        menu.addAction(rename_action)

        menu.addSeparator()

        delete_action = QAction(tr("delete"), self)
        delete_action.triggered.connect(lambda: self._delete_single_item(index))
        menu.addAction(delete_action)

        menu.setAttribute(Qt.WA_TranslucentBackground)
        menu.setWindowFlags(menu.windowFlags() | Qt.FramelessWindowHint)

        menu.exec(self.tree.viewport().mapToGlobal(position))

    def _rename_item(self, index):
        old_path = self.model.filePath(index)
        old_name = self.model.fileName(index)
        
        new_name, ok = QInputDialog.getText(
            self,
            tr("rename"),
            tr("filebrowser_new_name"),
            text=old_name,
        )
        if ok and new_name and new_name != old_name:
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            try:
                os.rename(old_path, new_path)
            except Exception as exc:
                QMessageBox.warning(
                    self,
                    tr("error"),
                    f"{tr('rename')} failed: {exc}",
                )

    def _delete_single_item(self, index):
        path = self.model.filePath(index)
        msg = QMessageBox(self)
        msg.setWindowTitle(tr("filebrowser_delete_file_title"))
        msg.setText(tr("filebrowser_delete_named", name=os.path.basename(path)))
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setStyleSheet("""
            QMessageBox { background-color: #252526; color: #e0e0e0; }
            QLabel { color: #e0e0e0; }
            QPushButton { background: #3e3e42; color: white; border: none; padding: 6px 12px; border-radius: 4px; }
            QPushButton:hover { background: #4e4e52; }
        """)
        
        if msg.exec() == QMessageBox.Yes:
            try:
                if os.path.isdir(path): shutil.rmtree(path)
                else: os.remove(path)
            except Exception as exc:
                QMessageBox.warning(
                    self,
                    tr("error"),
                    f"{tr('delete')} failed: {exc}",
                )

    # -------------------------------------------------------------------------
    # Standard Nav Logic
    # -------------------------------------------------------------------------
    def _toggle_search(self, checked):
        self.search_bar.setVisible(checked)
        if checked: self.search_bar.setFocus()
        else: self.search_bar.clear()

    def _on_search_text_changed(self, text):
        if not text.strip():
            self.model.setNameFilters(self._default_filters)
        else:
            query = text.strip()
            filters = [f"*{query}*"]
            filters.extend(f"*{query}*{pattern[1:]}" for pattern in self._default_filters)
            self.model.setNameFilters(filters)

    def set_path(self, path):
        if os.path.exists(path) and os.path.isdir(path):
            self.current_path = path
            self.address_bar.setText(path)
            self.tree.setRootIndex(self.model.index(path))
            os.chdir(path)
            self.path_changed.emit(path)

    def go_up(self):
        parent = os.path.dirname(self.current_path)
        self.set_path(parent)

    def browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, tr("select_folder"), self.current_path)
        if path: self.set_path(path)

    def _on_item_double_clicked(self, index):
        path = self.model.filePath(index)
        if os.path.isdir(path): self.set_path(path)
        else: self.file_open_requested.emit(path)
