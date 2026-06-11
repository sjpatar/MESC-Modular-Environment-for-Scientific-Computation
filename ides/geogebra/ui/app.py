from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QAction, QActionGroup, QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from shared.config import AppConfig
from .canvas import CanvasMode, GeometryCanvas
from ..engine.graph import (
    GeoCircle,
    GeoImplicitCurve,
    GeoIntersection,
    GeoLine,
    GeoMidpoint,
    GeoPoint,
    GeoVector,
)
from ..engine.parser import CommandProcessor


class GeoGebraApp(QMainWindow):
    ASSAMESE_TEXT = {
        "MESC Algebraic Geometry Studio": "MESC বীজগাণিতিক জ্যামিতি ষ্টুডিঅ'",
        "Objects": "বস্তুসমূহ",
        "Curves": "বক্ৰৰেখাসমূহ",
        "Selection": "বাছনি",
        "Object Explorer": "বস্তু অনুসন্ধানক",
        "Details": "বিৱৰণ",
        "Examples": "উদাহৰণ",
        "Coordinate Plane": "স্থানাংক সমতল",
        "Command": "কমান্ড",
        "Try: A = (2, 3), l1 = line(A, B), or C = curve(x^2 + y^2 - 25)": "চেষ্টা কৰক: A = (2, 3), l1 = ৰেখা(A, B), বা C = বক্ৰৰেখা(x^2 + y^2 - 25)",
        "Mode: ": "অৱস্থা: ",
        "Current Tool: ": "বৰ্তমানৰ সঁজুলি: ",
        "Error: ": "ভুল: ",
        "Command accepted.": "কমান্ড গৃহীত হৈছে।",
        "None": "নাই",
        "Select / Move": "বাছনি কৰক / স্থানান্তৰ কৰক",
        "Point": "বিন্দু",
        "Line": "ৰেখা",
        "Circle": "বৃত্ত",
        "Midpoint": "মধ্যবিন্দু",
        "Intersect": "ছেদ",
        "Vector": "ভেক্টৰ",
        "Shade Inequality": "অসমতা ছাঁ দিয়ক",
        "Select": "বাছনি কৰক",
        "Inequality": "অসমতা",
        "Created point {name}.": "বিন্দু {name} সৃষ্টি কৰা হৈছে।",
        "Created algebraic curve {name}.": "বীজগাণিতিক বক্ৰৰেখা {name} সৃষ্টি কৰা হৈছে।",
        "Created {type_name} {name}.": "{type_name} {name} সৃষ্টি কৰা হৈছে।",
        "Unsupported command. Try examples like 'A = (2, 3)', 'l1 = line(A, B)', or 'C = curve(x^2 + y^2 - 25)'.": "অসমৰ্থিত কমান্ড। 'A = (2, 3)', 'l1 = line(A, B)', বা 'C = curve(x^2 + y^2 - 25)' ৰ দৰে উদাহৰণ চেষ্টা কৰক।",
        "Unknown constructor '{func_name}'. Supported commands: line, circle, midpoint, vector, intersect, curve.": "অজ্ঞাত কনষ্ট্ৰাক্টৰ '{func_name}'। সমৰ্থিত কমান্ডসমূহ: line, circle, midpoint, vector, intersect, curve।",
        "{func_name} expects {expected} arguments, got {actual}.": "{func_name} এ {expected}টা আৰ্গুমেণ্ট আশা কৰে, কিন্তু {actual}টা পোৱা গ'ল।",
        "Unknown object '{key}'. Create it first.": "অজ্ঞাত বস্তু '{key}'। আগতে ইয়াক সৃষ্টি কৰক।",
        "Object '{key}' must be a {expected_type}, got {actual_type}.": "বস্তু '{key}' এটা {expected_type} হ'ব লাগিব, কিন্তু {actual_type} পোৱা গ'ল।",
        "Could not parse algebraic curve: {error}": "বীজগাণিতিক বক্ৰৰেখা বিশ্লেষণ কৰিব পৰা নগ'ল: {error}",
        "Curves can only use x and y. Unsupported symbols: {symbols}.": "বক্ৰৰেখাত কেৱল x আৰু y ব্যৱহাৰ কৰিব পাৰি। অসমৰ্থিত চিহ্নসমূহ: {symbols}।",
        "Only polynomial implicit curves are supported right now.": "বৰ্তমান কেৱল বহুপদী অন্তৰ্নিহিত বক্ৰৰেখাই সমৰ্থিত।",
        "The curve equation simplifies to 0 = 0 and is not drawable.": "বক্ৰৰেখাৰ সমীকৰণটো 0 = 0 লৈ সৰল হয় আৰু আঁকিব নোৱাৰি।",
        "An object named '{name}' already exists. Use a new name to avoid ambiguity.": "'{name}' নামৰ এটা বস্তু ইতিমধ্যে আছে। বিভ্ৰান্তি এৰাবলৈ নতুন নাম ব্যৱহাৰ কৰক।",
        "Line {name}: {equation}": "ৰেখা {name}: {equation}",
        "Circle {name}: {equation}": "বৃত্ত {name}: {equation}",
        "{name} (Midpoint) = ({x:.2f}, {y:.2f})": "{name} (মধ্যবিন্দু) = ({x:.2f}, {y:.2f})",
        "{name} (Intersect) = Undefined": "{name} (ছেদ) = অসংজ্ঞায়িত",
        "{name} (Intersect) = ({x:.2f}, {y:.2f})": "{name} (ছেদ) = ({x:.2f}, {y:.2f})",
        "Vector {name} = [{dx:.2f}, {dy:.2f}]": "ভেক্টৰ {name} = [{dx:.2f}, {dy:.2f}]",
        "Curve {name}: {expression} = 0": "বক্ৰৰেখা {name}: {expression} = 0",
        "Name": "নাম",
        "Type": "ধৰণ",
        "X": "X",
        "Y": "Y",
        "Free": "মুক্ত",
        "Point 1": "বিন্দু ১",
        "Point 2": "বিন্দু ২",
        "A": "A",
        "B": "B",
        "C": "C",
        "Line 1": "ৰেখা ১",
        "Line 2": "ৰেখা ২",
        "Exists": "আছে",
        "Center": "কেন্দ্ৰ",
        "Edge": "প্ৰান্ত",
        "Radius": "ব্যাসাৰ্ধ",
        "Origin": "আৰম্ভবিন্দু",
        "Terminal": "শেষবিন্দু",
        "DX": "DX",
        "DY": "DY",
        "Magnitude": "মান",
        "Expression": "ৰাশি",
        "Bounds": "সীমা",
        "Resolution": "ৰেজলিউশ্যন",
        "Contours": "কনট্যুৰ",
        "Yes": "হয়",
        "No": "নাই",
    }

    def __init__(self):
        super().__init__()
        self.processor = CommandProcessor(
            translate=self._geo_text,
            language_getter=AppConfig.get_language,
        )
        self.toolbar_actions = {}
        self.toolbar_modes = {}
        self.mode_group = None
        self.selected_node_name = None

        self.setObjectName("GeoGebraWindow")
        self.resize(1400, 900)
        self.setStyleSheet(self._build_stylesheet())

        self.setup_ui()
        self.setup_toolbar()
        self.populate_examples()
        self.retranslate_ui()
        self.set_mode(CanvasMode.SELECT)

    def _build_stylesheet(self) -> str:
        return """
            QMainWindow#GeoGebraWindow {
                background-color: #1a1a1a;
            }
            QWidget {
                color: #d4d4d4;
                background-color: transparent;
                font-family: "Segoe UI", "Helvetica Neue", sans-serif;
            }
            QFrame#Page {
                background-color: #1a1a1a;
            }
            QFrame#HeaderCard, QFrame#SidebarCard, QFrame#CanvasCard, QFrame#CommandCard {
                background-color: #202225;
                border: 1px solid #2d3138;
                border-radius: 12px;
            }
            QFrame#HeaderCard {
                background-color: #1d2025;
                border-color: #313641;
            }
            QFrame#MetricChip {
                background-color: #17191d;
                border: 1px solid #2d3138;
                border-radius: 8px;
            }
            QLabel#MetricValue {
                color: #f5f7fa;
                font-size: 15px;
                font-weight: 700;
            }
            QLabel#MetricLabel {
                color: #7f8898;
                font-size: 10px;
                font-weight: 600;
                text-transform: uppercase;
            }
            QLabel#SectionTitle {
                color: #f0f2f6;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.4px;
                text-transform: uppercase;
            }
            QToolBar {
                spacing: 3px;
                background-color: transparent;
                border: none;
                padding: 0px;
            }
            QToolBar QToolButton {
                background-color: #202225;
                color: #d4d8df;
                border: 1px solid #313641;
                border-radius: 7px;
                padding: 4px 8px;
                margin-right: 3px;
                font-size: 10px;
                font-weight: 600;
            }
            QToolBar QToolButton:hover {
                background-color: #2a2e36;
                border-color: #3d4a60;
            }
            QToolBar QToolButton:checked {
                background-color: #0d3c61;
                border-color: #176ea6;
                color: #ffffff;
            }
            QSplitter::handle {
                background: transparent;
                width: 6px;
                height: 6px;
            }
            QListWidget, QTextEdit {
                background-color: #17191d;
                border: 1px solid #2d3138;
                border-radius: 10px;
                color: #d9dce3;
                selection-background-color: #0d3c61;
                selection-color: #ffffff;
                padding: 4px;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-radius: 7px;
                margin: 1px 0px;
            }
            QListWidget::item:hover {
                background-color: #252a31;
            }
            QListWidget::item:selected {
                background-color: #0d3c61;
            }
            QTextEdit {
                font-family: Consolas, "Cascadia Mono", monospace;
                font-size: 11px;
                padding: 8px;
            }
            QTabWidget::pane {
                border: none;
                background: transparent;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #17191d;
                border: 1px solid #2d3138;
                color: #8d95a3;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 6px 10px;
                margin-right: 4px;
                font-size: 10px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background-color: #202225;
                color: #f4f6fa;
                border-bottom-color: #202225;
            }
            QLineEdit {
                background-color: #17191d;
                color: #eef2f7;
                border: 1px solid #2d3138;
                border-radius: 10px;
                padding: 9px 12px;
                font-size: 13px;
                selection-background-color: #0d3c61;
            }
            QLineEdit:focus {
                border: 1px solid #176ea6;
            }
            QLabel#FeedbackLabel {
                background-color: #17191d;
                border: 1px solid #2d3138;
                border-radius: 10px;
                padding: 8px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QLabel#CanvasHeaderTitle {
                color: #f3f5f8;
                font-size: 12px;
                font-weight: 700;
            }
            QLabel#CanvasPill {
                background-color: #17191d;
                border: 1px solid #2d3138;
                border-radius: 8px;
                color: #adb5c3;
                padding: 4px 8px;
                font-size: 10px;
                font-weight: 600;
            }
            QStatusBar {
                background: #17191d;
                color: #98a2b3;
                border-top: 1px solid #101214;
            }
            QStatusBar::item {
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: #17191d;
                width: 10px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: #3a414d;
                border-radius: 5px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: #4a5463;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                border: none;
                background: #17191d;
                height: 10px;
                margin: 2px;
            }
            QScrollBar::handle:horizontal {
                background: #3a414d;
                border-radius: 5px;
                min-width: 24px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #4a5463;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """

    def setup_ui(self):
        page = QFrame()
        page.setObjectName("Page")
        self.setCentralWidget(page)

        root = QVBoxLayout(page)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(8)

        header_card = QFrame()
        header_card.setObjectName("HeaderCard")
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(10, 7, 10, 7)
        header_layout.setSpacing(10)
        root.addWidget(header_card)

        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        header_layout.addWidget(self.toolbar, 1)

        metric_strip = QWidget()
        metric_layout = QHBoxLayout(metric_strip)
        metric_layout.setContentsMargins(0, 0, 0, 0)
        metric_layout.setSpacing(6)
        header_layout.addWidget(metric_strip)

        self.metric_total = self._build_metric(metric_layout)
        self.metric_curves = self._build_metric(metric_layout)
        self.metric_selection = self._build_metric(metric_layout)

        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setChildrenCollapsible(False)
        root.addWidget(main_splitter, 1)

        sidebar_card = QFrame()
        sidebar_card.setObjectName("SidebarCard")
        sidebar_card.setMinimumWidth(250)
        sidebar_card.setMaximumWidth(360)
        sidebar_layout = QVBoxLayout(sidebar_card)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(8)
        main_splitter.addWidget(sidebar_card)

        self.algebra_label = QLabel()
        self.algebra_label.setObjectName("SectionTitle")
        sidebar_layout.addWidget(self.algebra_label)

        sidebar_splitter = QSplitter(Qt.Vertical)
        sidebar_splitter.setChildrenCollapsible(False)
        sidebar_splitter.setHandleWidth(5)
        sidebar_layout.addWidget(sidebar_splitter, 1)

        self.algebra_list = QListWidget()
        self.algebra_list.currentItemChanged.connect(self.handle_algebra_selection)
        sidebar_splitter.addWidget(self.algebra_list)

        self.info_tabs = QTabWidget()
        sidebar_splitter.addWidget(self.info_tabs)
        sidebar_splitter.setSizes([360, 190])

        details_tab = QWidget()
        details_layout = QVBoxLayout(details_tab)
        details_layout.setContentsMargins(0, 6, 0, 0)
        details_layout.setSpacing(6)
        self.details_view = QTextEdit()
        self.details_view.setReadOnly(True)
        details_layout.addWidget(self.details_view, 1)
        self.info_tabs.addTab(details_tab, "")

        examples_tab = QWidget()
        examples_layout = QVBoxLayout(examples_tab)
        examples_layout.setContentsMargins(0, 6, 0, 0)
        examples_layout.setSpacing(6)
        self.examples_list = QListWidget()
        self.examples_list.itemDoubleClicked.connect(self.load_example)
        examples_layout.addWidget(self.examples_list, 1)
        self.info_tabs.addTab(examples_tab, "")

        canvas_card = QFrame()
        canvas_card.setObjectName("CanvasCard")
        canvas_layout = QVBoxLayout(canvas_card)
        canvas_layout.setContentsMargins(10, 10, 10, 10)
        canvas_layout.setSpacing(8)
        main_splitter.addWidget(canvas_card)
        main_splitter.setSizes([280, 1120])

        canvas_header = QHBoxLayout()
        canvas_header.setContentsMargins(0, 0, 0, 0)
        canvas_header.setSpacing(8)
        canvas_layout.addLayout(canvas_header)

        self.canvas_title = QLabel()
        self.canvas_title.setObjectName("CanvasHeaderTitle")
        canvas_header.addWidget(self.canvas_title, 1)

        self.mode_pill = QLabel()
        self.mode_pill.setObjectName("CanvasPill")
        canvas_header.addWidget(self.mode_pill, 0, Qt.AlignTop)

        self.canvas = GeometryCanvas(
            engine_namespace=self.processor.namespace,
            on_object_added=self.update_algebra_view,
            on_selection_changed=self.handle_canvas_selection,
        )
        self.canvas.setFrameShape(QFrame.NoFrame)
        self.canvas.setStyleSheet(
            "QGraphicsView { background-color: #0f1115; border: 1px solid #2d3138; border-radius: 10px; }"
        )
        canvas_layout.addWidget(self.canvas, 1)

        command_card = QFrame()
        command_card.setObjectName("CommandCard")
        command_layout = QHBoxLayout(command_card)
        command_layout.setContentsMargins(10, 8, 10, 8)
        command_layout.setSpacing(8)
        root.addWidget(command_card)

        self.command_title = QLabel()
        self.command_title.setObjectName("SectionTitle")
        command_layout.addWidget(self.command_title)

        self.input_bar = QLineEdit()
        self.input_bar.returnPressed.connect(self.process_input)
        command_layout.addWidget(self.input_bar, 1)

        self.command_feedback = QLabel()
        self.command_feedback.setObjectName("FeedbackLabel")
        self.command_feedback.setVisible(False)
        self.command_feedback.setWordWrap(True)
        command_layout.addWidget(self.command_feedback)

    def _build_metric(self, parent_layout):
        card = QFrame()
        card.setObjectName("MetricChip")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(9, 7, 9, 7)
        layout.setSpacing(1)
        value = QLabel("0")
        value.setObjectName("MetricValue")
        label = QLabel("")
        label.setObjectName("MetricLabel")
        layout.addWidget(value)
        layout.addWidget(label)
        parent_layout.addWidget(card)
        return {"value": value, "label": label}

    def setup_toolbar(self):
        self.mode_group = QActionGroup(self)
        self.mode_group.setExclusive(True)

        actions = [
            ("Select / Move", CanvasMode.SELECT),
            ("Point", CanvasMode.POINT),
            ("Line", CanvasMode.LINE),
            ("Circle", CanvasMode.CIRCLE),
            ("Midpoint", CanvasMode.MIDPOINT),
            ("Intersect", CanvasMode.INTERSECT),
            ("Vector", CanvasMode.VECTOR),
            ("Shade Inequality", CanvasMode.INEQUALITY),
        ]

        for default_name, mode in actions:
            action = QAction("", self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, m=mode: self.set_mode(m))
            self.mode_group.addAction(action)
            self.toolbar.addAction(action)
            self.toolbar_actions[default_name] = action
            self.toolbar_modes[mode] = action

    def populate_examples(self):
        self.examples_list.clear()
        for example in self.processor.get_examples():
            self.examples_list.addItem(example)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate_ui()
        super().changeEvent(event)

    def retranslate_ui(self):
        self.setWindowTitle(self._geo_text("MESC Algebraic Geometry Studio"))
        self.metric_total["label"].setText(self._geo_text("Objects"))
        self.metric_curves["label"].setText(self._geo_text("Curves"))
        self.metric_selection["label"].setText(self._geo_text("Selection"))
        self.algebra_label.setText(self._geo_text("Object Explorer"))
        self.info_tabs.setTabText(0, self._geo_text("Details"))
        self.info_tabs.setTabText(1, self._geo_text("Examples"))
        self.canvas_title.setText(self._geo_text("Coordinate Plane"))
        self.command_title.setText(self._geo_text("Command"))
        self.input_bar.setPlaceholderText(
            self._geo_text(
                "Try: A = (2, 3), l1 = line(A, B), or C = curve(x^2 + y^2 - 25)"
            )
        )
        self.populate_examples()

        for default_name, action in self.toolbar_actions.items():
            action.setText(self._geo_text(default_name))

        self.refresh_metrics()
        if hasattr(self.canvas, "mode"):
            mode_name = self._mode_label(self.canvas.mode)
            self.statusBar().showMessage(self._geo_text("Current Tool: ") + mode_name)
            self.mode_pill.setText(self._geo_text("Mode: ") + mode_name)

    def _mode_label(self, mode: CanvasMode) -> str:
        mode_name = mode.name.replace("_", " ").title()
        return self._geo_text(mode_name)

    def set_mode(self, mode: CanvasMode):
        self.canvas.mode = mode
        self.canvas.click_buffer.clear()
        self.canvas.scene.clearSelection()
        mode_name = self._mode_label(mode)
        self.statusBar().showMessage(self._geo_text("Current Tool: ") + mode_name)
        self.mode_pill.setText(self._geo_text("Mode: ") + mode_name)
        action = self.toolbar_modes.get(mode)
        if action is not None:
            action.setChecked(True)

    def process_input(self):
        text = self.input_bar.text().strip()
        if not text:
            return

        try:
            node = self.processor.parse_and_execute(text)
            if node:
                self.canvas.add_engine_node(node)
                self.canvas.select_node(node.name)
                self.show_node_details(node.name)
            self.input_bar.clear()
            self.set_feedback(
                self._creation_feedback(node)
                if node
                else self._geo_text("Command accepted.")
            )
        except Exception as exc:
            self.set_feedback(str(exc), is_error=True)
            self.statusBar().showMessage(self._geo_text("Error: ") + str(exc), 5000)

    def update_algebra_view(self, node=None):
        selected_name = self.canvas.selected_node_name() or self.selected_node_name
        self.algebra_list.blockSignals(True)
        self.algebra_list.clear()

        sorted_items = sorted(
            self.processor.namespace.items(),
            key=lambda item: (item[1].__class__.__name__, item[0].lower()),
        )
        for name, obj in sorted_items:
            item = QListWidgetItem(self._format_object_label(obj))
            item.setData(Qt.UserRole, name)
            self.algebra_list.addItem(item)
            if name == selected_name:
                self.algebra_list.setCurrentItem(item)

        self.algebra_list.blockSignals(False)
        self.refresh_metrics()
        if selected_name:
            self.show_node_details(selected_name)

    def handle_algebra_selection(self, current, previous):
        if current is None:
            return
        name = current.data(Qt.UserRole)
        self.canvas.select_node(name)
        self.show_node_details(name)

    def handle_canvas_selection(self, name: str | None):
        self.selected_node_name = name
        self.algebra_list.blockSignals(True)
        if name is None:
            self.algebra_list.clearSelection()
            self.details_view.clear()
            self.algebra_list.blockSignals(False)
            self.refresh_metrics()
            return

        for index in range(self.algebra_list.count()):
            item = self.algebra_list.item(index)
            if item.data(Qt.UserRole) == name:
                self.algebra_list.setCurrentItem(item)
                break
        self.algebra_list.blockSignals(False)
        self.show_node_details(name)

    def show_node_details(self, name: str | None):
        self.selected_node_name = name
        if not name or name not in self.processor.namespace:
            self.details_view.clear()
            self.refresh_metrics()
            return

        node = self.processor.namespace[name]
        details = node.describe()
        lines = [
            f"{self._detail_label(key)}: {self._detail_value(value)}"
            for key, value in details.items()
        ]
        self.details_view.setPlainText("\n".join(lines))
        self.refresh_metrics()

    def refresh_metrics(self):
        total = len(self.processor.namespace)
        curves = sum(
            1 for obj in self.processor.namespace.values() if isinstance(obj, GeoImplicitCurve)
        )
        selection = self.selected_node_name or self._geo_text("None")

        self.metric_total["value"].setText(str(total))
        self.metric_curves["value"].setText(str(curves))
        self.metric_selection["value"].setText(selection)

    def load_example(self, item):
        self.input_bar.setText(item.text())
        self.input_bar.setFocus()

    def set_feedback(self, text: str, is_error: bool = False):
        if not text:
            self.command_feedback.clear()
            self.command_feedback.setVisible(False)
            return

        color = QColor("#f58f8f") if is_error else QColor("#73d0a2")
        border = "#6b2c2c" if is_error else "#244734"
        bg = "#261819" if is_error else "#16231d"
        self.command_feedback.setStyleSheet(
            "QLabel#FeedbackLabel {"
            f"background-color: {bg};"
            f"border: 1px solid {border};"
            "border-radius: 10px;"
            "padding: 8px 10px;"
            "font-size: 11px;"
            "font-weight: 600;"
            f"color: {color.name()};"
            "}"
        )
        self.command_feedback.setText(text)
        self.command_feedback.setVisible(True)

    def _format_object_label(self, obj) -> str:
        if isinstance(obj, GeoPoint):
            return f"{obj.name} = ({obj.x:.2f}, {obj.y:.2f})"
        if isinstance(obj, GeoLine):
            equation = str(obj).split(": ", 1)[1]
            return self._geo_text("Line {name}: {equation}").format(
                name=obj.name, equation=equation
            )
        if isinstance(obj, GeoCircle):
            equation = str(obj).split(": ", 1)[1]
            return self._geo_text("Circle {name}: {equation}").format(
                name=obj.name, equation=equation
            )
        if isinstance(obj, GeoMidpoint):
            return self._geo_text("{name} (Midpoint) = ({x:.2f}, {y:.2f})").format(
                name=obj.name, x=obj.x, y=obj.y
            )
        if isinstance(obj, GeoIntersection):
            if not obj.exists:
                return self._geo_text("{name} (Intersect) = Undefined").format(name=obj.name)
            return self._geo_text("{name} (Intersect) = ({x:.2f}, {y:.2f})").format(
                name=obj.name, x=obj.x, y=obj.y
            )
        if isinstance(obj, GeoVector):
            return self._geo_text("Vector {name} = [{dx:.2f}, {dy:.2f}]").format(
                name=obj.name, dx=obj.dx, dy=obj.dy
            )
        if isinstance(obj, GeoImplicitCurve):
            return self._geo_text("Curve {name}: {expression} = 0").format(
                name=obj.name, expression=obj.expression_text
            )
        return str(obj)

    def _detail_label(self, key: str) -> str:
        label_map = {
            "name": self._geo_text("Name"),
            "type": self._geo_text("Type"),
            "x": self._geo_text("X"),
            "y": self._geo_text("Y"),
            "free": self._geo_text("Free"),
            "point_1": self._geo_text("Point 1"),
            "point_2": self._geo_text("Point 2"),
            "a": self._geo_text("A"),
            "b": self._geo_text("B"),
            "c": self._geo_text("C"),
            "line_1": self._geo_text("Line 1"),
            "line_2": self._geo_text("Line 2"),
            "exists": self._geo_text("Exists"),
            "center": self._geo_text("Center"),
            "edge": self._geo_text("Edge"),
            "radius": self._geo_text("Radius"),
            "origin": self._geo_text("Origin"),
            "terminal": self._geo_text("Terminal"),
            "dx": self._geo_text("DX"),
            "dy": self._geo_text("DY"),
            "magnitude": self._geo_text("Magnitude"),
            "expression": self._geo_text("Expression"),
            "bounds": self._geo_text("Bounds"),
            "resolution": self._geo_text("Resolution"),
            "contours": self._geo_text("Contours"),
        }
        return label_map.get(key, key.replace("_", " ").title())

    def _detail_value(self, value):
        if isinstance(value, bool):
            return self._geo_text("Yes") if value else self._geo_text("No")
        return value

    def _creation_feedback(self, node) -> str:
        if isinstance(node, GeoPoint):
            return self._geo_text("Created point {name}.").format(name=node.name)
        if isinstance(node, GeoImplicitCurve):
            return self._geo_text("Created algebraic curve {name}.").format(
                name=node.name
            )
        return self._geo_text("Created {type_name} {name}.").format(
            type_name=node.__class__.__name__, name=node.name
        )

    def _geo_text(self, text: str) -> str:
        if AppConfig.get_language() == "as":
            return self.ASSAMESE_TEXT.get(text, text)
        return text
