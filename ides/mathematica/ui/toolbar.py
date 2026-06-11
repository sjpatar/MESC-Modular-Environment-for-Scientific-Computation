from PySide6.QtWidgets import QToolBar, QWidget, QSizePolicy, QToolButton, QMenu, QMessageBox, QPushButton
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QAction
from PySide6.QtCore import Qt, QSize, QEvent
from shared.config import AppConfig

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

        if name == "trash":
            painter.drawRect(7, 8, 10, 11) 
            painter.drawLine(5, 6, 19, 6)  
            painter.drawLine(10, 4, 14, 4) 
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawLine(10, 10, 10, 17)
            painter.drawLine(14, 10, 14, 17)
        elif name == "list":
            painter.drawLine(9, 7, 18, 7)
            painter.drawLine(9, 12, 18, 12)
            painter.drawLine(9, 17, 18, 17)
            pen.setWidth(3)
            painter.setPen(pen)
            painter.drawPoint(5, 7)
            painter.drawPoint(5, 12)
            painter.drawPoint(5, 17)
        elif name == "load":
            painter.drawRoundedRect(4, 9, 16, 11, 2, 2)
            painter.drawLine(4, 9, 10, 9)
            painter.drawLine(10, 9, 12, 6)
            painter.drawLine(12, 6, 18, 6)
            painter.drawLine(18, 6, 20, 9)
        elif name == "save":
            painter.drawRoundedRect(5, 4, 14, 16, 2, 2)
            painter.drawLine(5, 15, 19, 15)
            painter.drawLine(19, 4, 19, 8) 
            painter.drawRect(8, 15, 8, 5)
        elif name == "pdf":
            painter.drawRect(6, 3, 12, 18)
            painter.drawLine(10, 9, 14, 9)
            painter.drawLine(10, 13, 14, 13)
            painter.drawLine(10, 17, 12, 17)

        painter.end()
        return QIcon(pix)

class MathematicaToolbar(QToolBar):
    def __init__(self, parent_app):
        super().__init__(parent_app)
        self.app = parent_app
        self.setMovable(False)
        self.setIconSize(QSize(16, 16))
        
        self.setStyleSheet("""
            QToolBar { 
                background-color: #2d2d2d; 
                border: none;
                border-bottom: 1px solid #1e1e1e; 
                spacing: 4px; 
                padding: 4px 6px;
            }
            QToolButton { 
                background-color: transparent; 
                border: 1px solid transparent; 
                border-radius: 4px; 
                color: #cccccc; 
                padding: 4px 8px; 
                font-family: "Segoe UI", sans-serif;
                font-size: 10pt; 
            }
            QToolButton:hover { background-color: #454545; }
            QToolButton:pressed, QToolButton::menu-button:pressed { background-color: #094771; color: white; }
            QToolButton::menu-indicator { image: none; }
            QMenu {
                background-color: #252526;
                color: #cccccc;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 4px 0px;
                font-family: "Segoe UI", sans-serif;
            }
            QMenu::item { padding: 6px 24px 6px 24px; }
            QMenu::item:selected { background-color: #0061a8; color: white; }
            QMenu::separator { background-color: #3e3e42; height: 1px; margin: 4px 0px; }
        """)
        self._setup_actions()
        self.retranslate_ui()

    def changeEvent(self, event):
        """Intercept language changes and refresh text."""
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate_ui()
        super().changeEvent(event)

    def retranslate_ui(self):
        """Apply translated strings to all toolbar actions and buttons."""
        self.act_load.setText(self.tr("Load Notebook"))
        self.act_save.setText(self.tr("Save Notebook"))
        self.act_clear.setText(self.tr("Clear Notebook"))
        self.act_pdf.setText(self.tr("Export to PDF"))

        if self.simple_mode_btn.isChecked():
            self.simple_mode_btn.setText(self.tr("Simple Mode: ON"))
        else:
            self.simple_mode_btn.setText(self.tr("Simple Mode: OFF"))

        self.btn_palettes.setText(self.tr("Palettes") + " ▾")
        self.act_basic.setText(self.tr("Basic Math Assistant"))
        self.act_special.setText(self.tr("Special Characters"))

        self.btn_graphics.setText(self.tr("Graphics") + " ▾")
        self.act_2d.setText(self.tr("Insert 2D Plot Template"))
        self.act_3d.setText(self.tr("Insert 3D Plot Template"))

        self.btn_eval.setText(self.tr("Evaluation") + " ▾")
        self.act_eval_nb.setText(self.tr("Evaluate Notebook"))
        self.act_quit.setText(self.tr("Quit Kernel"))

        self.btn_help.setText(self.tr("Help") + " ▾")
        self.act_doc.setText(self.tr("About Mathematica"))
        self.act_syntax.setText(self.tr("Syntax/User Guide"))

    def _setup_actions(self):
        self.act_load = QAction("", self)
        self.act_load.setIcon(MinimalIcon.get("load"))
        self.act_load.triggered.connect(lambda checked=False: self.app.load_session_dialog())
        self.addAction(self.act_load)

        self.act_save = QAction("", self)
        self.act_save.setIcon(MinimalIcon.get("save"))
        self.act_save.triggered.connect(lambda checked=False: self.app.save_session_dialog())
        self.addAction(self.act_save)

        self.act_clear = QAction("", self)
        self.act_clear.setIcon(MinimalIcon.get("trash"))
        self.act_clear.triggered.connect(lambda checked=False: self.app.clear_history())
        self.addAction(self.act_clear)
        
        self.act_pdf = QAction("", self)
        self.act_pdf.setIcon(MinimalIcon.get("pdf"))
        self.act_pdf.triggered.connect(lambda checked=False: self.app.export_pdf_dialog())
        self.addAction(self.act_pdf)

        self.simple_mode_btn = QPushButton("", self)
        self.simple_mode_btn.setCheckable(True)
        self.simple_mode_btn.setCursor(Qt.PointingHandCursor)
        self.simple_mode_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e1e1e;
                color: #888888;
                border: 1px solid #3e3e42;
                border-radius: 12px;
                padding: 4px 18px;
                font-family: "Segoe UI", sans-serif;
                font-size: 9pt;
                font-weight: bold;
                margin: 0px 4px;
            }
            QPushButton:hover { background-color: #2d2d2d; color: #cccccc; border: 1px solid #555555; }
            QPushButton:checked { background-color: #007acc; color: #ffffff; border: 1px solid #005f9e; }
        """)
        self.simple_mode_btn.toggled.connect(self._toggle_simple_mode)
        self.addWidget(self.simple_mode_btn)

        empty = QWidget()
        empty.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        empty.setStyleSheet("background-color: transparent;") 
        self.addWidget(empty)

        self._add_palettes_menu()
        self._add_graphics_menu()
        self._add_evaluation_menu()
        self._add_help_menu()

    def _toggle_simple_mode(self, checked):
        self.simple_mode_btn.setText(self.tr("Simple Mode: ON") if checked else self.tr("Simple Mode: OFF"))
        self.app.set_simple_mode(checked)

    def _create_menu_btn(self):
        btn = QToolButton(self)
        btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        btn.setPopupMode(QToolButton.InstantPopup)
        btn.setCursor(Qt.PointingHandCursor)
        return btn

    def _add_palettes_menu(self):
        self.btn_palettes = self._create_menu_btn()
        # FIX 1: Save the menu to 'self' to stop Python from deleting it via Garbage Collection
        self.palettes_menu = QMenu(self.btn_palettes)
        
        self.act_basic = QAction("", self)
        # FIX 2: Safely absorb the hidden boolean 'checked' parameter sent by PySide6
        self.act_basic.triggered.connect(lambda checked=False: self.app.show_palette("basic"))
        
        self.act_special = QAction("", self)
        self.act_special.triggered.connect(lambda checked=False: self.app.show_palette("special"))
        
        self.palettes_menu.addAction(self.act_basic)
        self.palettes_menu.addAction(self.act_special)
        self.btn_palettes.setMenu(self.palettes_menu)
        self.addWidget(self.btn_palettes)

    def _add_graphics_menu(self):
        self.btn_graphics = self._create_menu_btn()
        self.graphics_menu = QMenu(self.btn_graphics)

        if AppConfig.get_language() == "as":
            plot_2d_template = "আঁকা[Sin[x], {x, -10, 10}]"
            plot_3d_template = "লেখচিত্ৰ3D[Sin[x]*Cos[y], {x, -5, 5}, {y, -5, 5}]"
        else:
            plot_2d_template = "Plot[Sin[x], {x, -10, 10}]"
            plot_3d_template = "Plot3D[Sin[x]*Cos[y], {x, -5, 5}, {y, -5, 5}]"
        
        self.act_2d = QAction("", self)
        self.act_2d.triggered.connect(lambda checked=False, p=plot_2d_template: self.app.insert_template(p))
        
        self.act_3d = QAction("", self)
        self.act_3d.triggered.connect(lambda checked=False, p=plot_3d_template: self.app.insert_template(p))
        
        self.graphics_menu.addAction(self.act_2d)
        self.graphics_menu.addAction(self.act_3d)
        self.btn_graphics.setMenu(self.graphics_menu)
        self.addWidget(self.btn_graphics)

    def _add_evaluation_menu(self):
        self.btn_eval = self._create_menu_btn()
        self.eval_menu = QMenu(self.btn_eval)
        
        self.act_eval_nb = QAction("", self)
        self.act_eval_nb.triggered.connect(lambda checked=False: self.app.evaluate_notebook())
        
        self.act_quit = QAction("", self)
        self.act_quit.triggered.connect(lambda checked=False: self.app.quit_kernel())
        
        self.eval_menu.addAction(self.act_eval_nb)
        self.eval_menu.addSeparator()
        self.eval_menu.addAction(self.act_quit)
        self.btn_eval.setMenu(self.eval_menu)
        self.addWidget(self.btn_eval)

    def _add_help_menu(self):
        self.btn_help = self._create_menu_btn()
        self.help_menu = QMenu(self.btn_help)
        
        self.act_doc = QAction("", self)
        self.act_doc.triggered.connect(lambda checked=False: self.app.show_documentation())

        self.act_syntax = QAction("", self)
        self.act_syntax.triggered.connect(lambda checked=False: self.app.show_syntax_guide())
        
        self.help_menu.addAction(self.act_doc)
        self.help_menu.addAction(self.act_syntax)
        self.btn_help.setMenu(self.help_menu)
        self.addWidget(self.btn_help)