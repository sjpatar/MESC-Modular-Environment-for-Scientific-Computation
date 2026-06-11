import math
from enum import Enum
from typing import Callable

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsPolygonItem,
    QGraphicsScene,
    QGraphicsView,
)

from ..engine.graph import (
    GeoCircle,
    GeoImplicitCurve,
    GeoInequality,
    GeoIntersection,
    GeoLine,
    GeoLinearProgram,
    GeoMidpoint,
    GeoPoint,
    GeoTransformedPoint,
    GeoVector,
)


class CanvasMode(Enum):
    SELECT = 0
    POINT = 1
    LINE = 2
    CIRCLE = 3
    MIDPOINT = 4
    INTERSECT = 5
    VECTOR = 6
    INEQUALITY = 7


class ReactivePoint(QGraphicsEllipseItem):
    def __init__(self, canvas, geo_node, radius=5):
        super().__init__(-radius, -radius, radius * 2, radius * 2)
        self.canvas = canvas
        self.geo_node = geo_node
        self._is_updating = False
        self.is_free = getattr(geo_node, "is_free", True)
        self.selected_color = QColor("#ff7a00")

        if isinstance(geo_node, GeoLinearProgram):
            self.default_color = QColor("#d4a017")
            self.setPen(QPen(QColor("#8f6a00"), 2.5))
            self.setScale(1.5)
        elif isinstance(geo_node, GeoTransformedPoint):
            self.default_color = QColor("#0f9d8a")
            self.setPen(QPen(Qt.white, 1.5))
        else:
            self.default_color = QColor("#165dff") if self.is_free else QColor("#555555")
            self.setPen(QPen(Qt.white, 1.5))

        self.setBrush(QBrush(self.default_color))

        flags = QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsGeometryChanges
        if self.is_free:
            flags |= QGraphicsItem.ItemIsMovable

        self.setFlags(flags)
        self.setAcceptHoverEvents(True)
        self.setZValue(10)

        self.geo_node.add_observer(self.redraw)
        self.redraw()

    def redraw(self):
        if isinstance(self.geo_node, GeoIntersection) and not self.geo_node.exists:
            self.setVisible(False)
            return
        if isinstance(self.geo_node, GeoLinearProgram) and not self.geo_node.exists:
            self.setVisible(False)
            return

        self.setVisible(True)
        self._is_updating = True
        x = getattr(self.geo_node, "optimal_x", self.geo_node.x)
        y = getattr(self.geo_node, "optimal_y", self.geo_node.y)
        self.setPos(self.canvas.world_to_scene_point(x, y))
        self._is_updating = False

    def itemChange(self, change, value):
        if (
            change == QGraphicsItem.ItemPositionChange
            and not self._is_updating
            and self.is_free
        ):
            world = self.canvas.scene_to_world_point(value)
            self.geo_node.set_coords(world.x(), world.y())
            return self.canvas.world_to_scene_point(self.geo_node.x, self.geo_node.y)
        if change == QGraphicsItem.ItemSelectedHasChanged:
            self.setBrush(
                QBrush(self.selected_color if self.isSelected() else self.default_color)
            )
        return super().itemChange(change, value)

    def hoverEnterEvent(self, event):
        if not self.isSelected():
            self.setBrush(QBrush(self.default_color.lighter(120)))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        if not self.isSelected():
            self.setBrush(QBrush(self.default_color))
        super().hoverLeaveEvent(event)


class ReactiveLine(QGraphicsLineItem):
    def __init__(self, canvas, geo_line: GeoLine):
        super().__init__()
        self.canvas = canvas
        self.geo_line = geo_line
        self.setPen(QPen(QColor("#333333"), 2))
        self.setFlags(QGraphicsItem.ItemIsSelectable)
        self.setZValue(0)
        self.geo_line.add_observer(self.redraw)
        self.redraw()

    def redraw(self):
        p1, p2 = self.geo_line.p1, self.geo_line.p2
        dx, dy = p2.x - p1.x, p2.y - p1.y
        length = math.hypot(dx, dy)
        if length == 0:
            return

        span = max(abs(v) for v in self.canvas.world_bounds()) + 20.0
        nx, ny = (dx / length) * span, (dy / length) * span
        start = self.canvas.world_to_scene_point(p1.x - nx, p1.y - ny)
        end = self.canvas.world_to_scene_point(p2.x + nx, p2.y + ny)
        self.setLine(start.x(), start.y(), end.x(), end.y())

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            pen = self.pen()
            pen.setColor(QColor("#ff7a00") if self.isSelected() else QColor("#333333"))
            pen.setWidth(3 if self.isSelected() else 2)
            self.setPen(pen)
        return super().itemChange(change, value)


class ReactiveCircle(QGraphicsEllipseItem):
    def __init__(self, canvas, geo_circle: GeoCircle):
        super().__init__()
        self.canvas = canvas
        self.geo_circle = geo_circle
        self.setBrush(QBrush(QColor(12, 140, 233, 24)))
        self.setPen(QPen(QColor("#1488e9"), 2))
        self.setFlags(QGraphicsItem.ItemIsSelectable)
        self.setZValue(-1)
        self.geo_circle.add_observer(self.redraw)
        self.redraw()

    def redraw(self):
        center = self.canvas.world_to_scene_point(
            self.geo_circle.center.x, self.geo_circle.center.y
        )
        radius = self.geo_circle.radius * self.canvas.GRID_SIZE
        self.setRect(center.x() - radius, center.y() - radius, radius * 2, radius * 2)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            pen = self.pen()
            pen.setColor(QColor("#ff7a00") if self.isSelected() else QColor("#1488e9"))
            pen.setWidth(3 if self.isSelected() else 2)
            self.setPen(pen)
        return super().itemChange(change, value)


class ReactiveVector(QGraphicsLineItem):
    def __init__(self, canvas, geo_vector: GeoVector):
        super().__init__()
        self.canvas = canvas
        self.geo_vector = geo_vector
        self.setPen(QPen(QColor("#1a7f5a"), 2.5))
        self.setFlags(QGraphicsItem.ItemIsSelectable)
        self.setZValue(1)

        self.arrow_head = QGraphicsPolygonItem(self)
        self.arrow_head.setBrush(QBrush(QColor("#1a7f5a")))
        self.arrow_head.setPen(QPen(Qt.NoPen))

        self.geo_vector.add_observer(self.redraw)
        self.redraw()

    def redraw(self):
        p1 = self.canvas.world_to_scene_point(
            self.geo_vector.origin.x, self.geo_vector.origin.y
        )
        p2 = self.canvas.world_to_scene_point(
            self.geo_vector.terminal.x, self.geo_vector.terminal.y
        )
        self.setLine(p1.x(), p1.y(), p2.x(), p2.y())

        angle = math.atan2(p2.y() - p1.y(), p2.x() - p1.x())
        arrow_size = 12
        tip = QPointF(p2.x(), p2.y())
        left = QPointF(
            p2.x() - arrow_size * math.cos(angle - math.pi / 6),
            p2.y() - arrow_size * math.sin(angle - math.pi / 6),
        )
        right = QPointF(
            p2.x() - arrow_size * math.cos(angle + math.pi / 6),
            p2.y() - arrow_size * math.sin(angle + math.pi / 6),
        )
        self.arrow_head.setPolygon(QPolygonF([tip, left, right]))

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            color = QColor("#ff7a00") if self.isSelected() else QColor("#1a7f5a")
            self.setPen(QPen(color, 3.5 if self.isSelected() else 2.5))
            self.arrow_head.setBrush(QBrush(color))
        return super().itemChange(change, value)


class ReactiveInequality(QGraphicsPolygonItem):
    def __init__(self, canvas, geo_ineq: GeoInequality):
        super().__init__()
        self.canvas = canvas
        self.geo_ineq = geo_ineq
        self.setBrush(QBrush(QColor(65, 105, 225, 40)))
        self.setPen(QPen(Qt.NoPen))
        self.setZValue(-2)
        self.geo_ineq.add_observer(self.redraw)
        self.redraw()

    def redraw(self):
        line = self.geo_ineq.boundary
        if math.isclose(line.a, 0) and math.isclose(line.b, 0):
            return

        xmin, xmax, ymin, ymax = self.canvas.world_bounds(expand=5.0)
        corners = [
            QPointF(xmin, ymin),
            QPointF(xmax, ymin),
            QPointF(xmax, ymax),
            QPointF(xmin, ymax),
        ]
        valid = [point for point in corners if self.geo_ineq.evaluate(point.x(), point.y())]

        intersections = []
        if not math.isclose(line.b, 0):
            y_left = (-line.c - line.a * xmin) / line.b
            if ymin <= y_left <= ymax:
                intersections.append(QPointF(xmin, y_left))
            y_right = (-line.c - line.a * xmax) / line.b
            if ymin <= y_right <= ymax:
                intersections.append(QPointF(xmax, y_right))

        if not math.isclose(line.a, 0):
            x_top = (-line.c - line.b * ymax) / line.a
            if xmin <= x_top <= xmax:
                intersections.append(QPointF(x_top, ymax))
            x_bottom = (-line.c - line.b * ymin) / line.a
            if xmin <= x_bottom <= xmax:
                intersections.append(QPointF(x_bottom, ymin))

        all_points = valid + intersections
        if len(all_points) >= 3:
            cx = sum(point.x() for point in all_points) / len(all_points)
            cy = sum(point.y() for point in all_points) / len(all_points)
            all_points.sort(key=lambda p: math.atan2(p.y() - cy, p.x() - cx))
            polygon = [self.canvas.world_to_scene_point(point.x(), point.y()) for point in all_points]
            self.setPolygon(QPolygonF(polygon))


class ReactiveImplicitCurve(QGraphicsPathItem):
    def __init__(self, canvas, geo_curve: GeoImplicitCurve):
        super().__init__()
        self.canvas = canvas
        self.geo_curve = geo_curve
        self.setPen(QPen(QColor("#8b1e3f"), 2.2))
        self.setBrush(Qt.NoBrush)
        self.setFlags(QGraphicsItem.ItemIsSelectable)
        self.setZValue(-0.5)
        self.geo_curve.add_observer(self.redraw)
        self.redraw()

    def redraw(self):
        path = QPainterPath()
        for contour in self.geo_curve.contours:
            if not contour:
                continue
            start = self.canvas.world_to_scene_point(*contour[0])
            path.moveTo(start)
            for point in contour[1:]:
                path.lineTo(self.canvas.world_to_scene_point(*point))
        self.setPath(path)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            self.setPen(
                QPen(QColor("#ff7a00") if self.isSelected() else QColor("#8b1e3f"), 2.8)
            )
        return super().itemChange(change, value)


class GeometryCanvas(QGraphicsView):
    SCENE_EXTENT = 5000
    GRID_SIZE = 50.0

    def __init__(
        self,
        engine_namespace: dict,
        on_object_added: Callable,
        on_selection_changed: Callable | None = None,
    ):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(
            -self.SCENE_EXTENT,
            -self.SCENE_EXTENT,
            self.SCENE_EXTENT * 2,
            self.SCENE_EXTENT * 2,
        )
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setBackgroundBrush(QBrush(QColor("#f6f7fb")))

        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.current_zoom = 1.0

        self.mode = CanvasMode.SELECT
        self.click_buffer = []

        self.engine_namespace = engine_namespace
        self.on_object_added = on_object_added
        self.on_selection_changed = on_selection_changed
        self.point_counter = 65
        self.obj_counter = 1
        self.item_by_name = {}
        self.scene.selectionChanged.connect(self._emit_selection_change)

    def drawBackground(self, painter: QPainter, rect: QRectF):
        super().drawBackground(painter, rect)
        grid_size = int(self.GRID_SIZE)
        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)

        painter.setPen(QPen(QColor(230, 232, 240), 1))
        x = left
        while x < rect.right():
            painter.drawLine(x, int(rect.top()), x, int(rect.bottom()))
            x += grid_size
        y = top
        while y < rect.bottom():
            painter.drawLine(int(rect.left()), y, int(rect.right()), y)
            y += grid_size

        painter.setPen(QPen(QColor(160, 165, 180), 2))
        if rect.left() <= 0 <= rect.right():
            painter.drawLine(0, int(rect.top()), 0, int(rect.bottom()))
        if rect.top() <= 0 <= rect.bottom():
            painter.drawLine(int(rect.left()), 0, int(rect.right()), 0)

    def world_to_scene_point(self, x: float, y: float) -> QPointF:
        return QPointF(x * self.GRID_SIZE, -y * self.GRID_SIZE)

    def scene_to_world_point(self, point: QPointF) -> QPointF:
        return QPointF(point.x() / self.GRID_SIZE, -point.y() / self.GRID_SIZE)

    def world_bounds(self, expand: float = 0.0) -> tuple[float, float, float, float]:
        rect = self.mapToScene(self.viewport().rect()).boundingRect()
        top_left = self.scene_to_world_point(rect.topLeft())
        bottom_right = self.scene_to_world_point(rect.bottomRight())
        xmin = min(top_left.x(), bottom_right.x()) - expand
        xmax = max(top_left.x(), bottom_right.x()) + expand
        ymin = min(top_left.y(), bottom_right.y()) - expand
        ymax = max(top_left.y(), bottom_right.y()) + expand
        return xmin, xmax, ymin, ymax

    def curve_resolution(self) -> int:
        return max(160, min(420, self.viewport().width() // 3))

    def refresh_curves_for_view(self):
        bounds = self.world_bounds(expand=2.0)
        resolution = self.curve_resolution()
        for node in self.engine_namespace.values():
            if isinstance(node, GeoImplicitCurve):
                node.set_view_bounds(bounds, resolution=resolution)

    def generate_name(self, prefix="") -> str:
        if prefix == "P":
            name = chr(self.point_counter)
            self.point_counter += 1
            return name
        name = f"{prefix}{self.obj_counter}"
        self.obj_counter += 1
        return name

    def add_engine_node(self, node):
        if node.name in self.item_by_name:
            return

        if isinstance(node, GeoImplicitCurve):
            node.set_view_bounds(self.world_bounds(expand=2.0), self.curve_resolution())

        if isinstance(
            node,
            (GeoPoint, GeoMidpoint, GeoIntersection, GeoLinearProgram, GeoTransformedPoint),
        ):
            ui_item = ReactivePoint(self, node)
        elif isinstance(node, GeoLine):
            ui_item = ReactiveLine(self, node)
        elif isinstance(node, GeoCircle):
            ui_item = ReactiveCircle(self, node)
        elif isinstance(node, GeoVector):
            ui_item = ReactiveVector(self, node)
        elif isinstance(node, GeoInequality):
            ui_item = ReactiveInequality(self, node)
        elif isinstance(node, GeoImplicitCurve):
            ui_item = ReactiveImplicitCurve(self, node)
        else:
            return

        self.engine_namespace[node.name] = node
        self.item_by_name[node.name] = ui_item
        ui_item.setData(0, node.name)
        self.scene.addItem(ui_item)
        self.on_object_added(node)

    def select_node(self, name: str | None):
        self.scene.clearSelection()
        if not name:
            return
        item = self.item_by_name.get(name)
        if item is not None:
            item.setSelected(True)
            self.centerOn(item)

    def selected_node_name(self):
        selected = self.scene.selectedItems()
        if not selected:
            return None
        return selected[0].data(0)

    def _emit_selection_change(self):
        if self.on_selection_changed is not None:
            self.on_selection_changed(self.selected_node_name())

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton or (
            event.button() == Qt.LeftButton
            and self.mode == CanvasMode.SELECT
            and event.modifiers() == Qt.ShiftModifier
        ):
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            fake_event = event.clone()
            super().mousePressEvent(fake_event)
            return

        scene_pos = self.mapToScene(event.pos())
        world_pos = self.scene_to_world_point(scene_pos)
        item = self.scene.itemAt(scene_pos, self.transform())

        if self.mode == CanvasMode.POINT:
            if not isinstance(item, ReactivePoint):
                point = GeoPoint(self.generate_name("P"), world_pos.x(), world_pos.y())
                self.add_engine_node(point)

        elif self.mode in (
            CanvasMode.LINE,
            CanvasMode.CIRCLE,
            CanvasMode.MIDPOINT,
            CanvasMode.VECTOR,
        ):
            if isinstance(item, ReactivePoint):
                if item.geo_node not in self.click_buffer:
                    self.click_buffer.append(item.geo_node)
                    item.setSelected(True)

                if len(self.click_buffer) == 2:
                    p1, p2 = self.click_buffer
                    if self.mode == CanvasMode.LINE:
                        node = GeoLine(self.generate_name("l"), p1, p2)
                    elif self.mode == CanvasMode.CIRCLE:
                        node = GeoCircle(self.generate_name("c"), p1, p2)
                    elif self.mode == CanvasMode.MIDPOINT:
                        node = GeoMidpoint(self.generate_name("M"), p1, p2)
                    else:
                        node = GeoVector(self.generate_name("u"), p1, p2)

                    self.add_engine_node(node)
                    self.scene.clearSelection()
                    self.click_buffer.clear()

        elif self.mode == CanvasMode.INTERSECT:
            if isinstance(item, ReactiveLine):
                if item.geo_line not in self.click_buffer:
                    self.click_buffer.append(item.geo_line)
                    item.setSelected(True)

                if len(self.click_buffer) == 2:
                    l1, l2 = self.click_buffer
                    node = GeoIntersection(self.generate_name("P"), l1, l2)
                    self.add_engine_node(node)
                    self.scene.clearSelection()
                    self.click_buffer.clear()

        elif self.mode == CanvasMode.INEQUALITY:
            if isinstance(item, ReactiveLine):
                node = GeoInequality(self.generate_name("ineq"), item.geo_line, operator="<=")
                self.add_engine_node(node)
                self.scene.clearSelection()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self.dragMode() == QGraphicsView.ScrollHandDrag:
            self.setDragMode(QGraphicsView.RubberBandDrag)
        self.refresh_curves_for_view()

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0 and self.current_zoom < 10.0:
            self.current_zoom *= 1.15
            self.scale(1.15, 1.15)
        elif event.angleDelta().y() < 0 and self.current_zoom > 0.1:
            self.current_zoom *= 1 / 1.15
            self.scale(1 / 1.15, 1 / 1.15)
        self.refresh_curves_for_view()
