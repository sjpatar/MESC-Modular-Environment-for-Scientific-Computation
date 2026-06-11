from __future__ import annotations

import math
from typing import Callable, List, Optional

import numpy as np
from skimage import measure


class GeoNode:
    """Base class for all mathematical objects in the dependency graph."""

    def __init__(self, name: str, dependencies: Optional[List["GeoNode"]] = None):
        self.name = name
        self.dependencies = dependencies or []
        self.children: List["GeoNode"] = []
        self._observers: List[Callable] = []

        for dep in self.dependencies:
            if self not in dep.children:
                dep.children.append(self)

    def add_observer(self, callback: Callable):
        if callback not in self._observers:
            self._observers.append(callback)

    def notify_observers(self):
        for obs in self._observers:
            obs()

    def update(self):
        self.compute()
        self.notify_observers()
        for child in self.children:
            child.update()

    def compute(self):
        pass

    def describe(self) -> dict:
        return {"name": self.name, "type": self.__class__.__name__}

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name})"


class GeoPoint(GeoNode):
    """A free point that can be dragged by the user."""

    def __init__(self, name: str, x: float, y: float):
        super().__init__(name)
        self.x = float(x)
        self.y = float(y)
        self.is_free = True

    def set_coords(self, x: float, y: float):
        if math.isclose(self.x, x, abs_tol=1e-5) and math.isclose(
            self.y, y, abs_tol=1e-5
        ):
            return
        self.x = float(x)
        self.y = float(y)
        self.update()

    def __str__(self):
        return f"{self.name} = ({self.x:.2f}, {self.y:.2f})"

    def describe(self) -> dict:
        data = super().describe()
        data.update({"x": self.x, "y": self.y, "free": self.is_free})
        return data


class GeoMidpoint(GeoNode):
    def __init__(self, name: str, p1: GeoNode, p2: GeoNode):
        super().__init__(name, dependencies=[p1, p2])
        self.p1 = p1
        self.p2 = p2
        self.x = 0.0
        self.y = 0.0
        self.is_free = False
        self.compute()

    def compute(self):
        self.x = (self.p1.x + self.p2.x) / 2.0
        self.y = (self.p1.y + self.p2.y) / 2.0

    def __str__(self):
        return f"{self.name} (Midpoint) = ({self.x:.2f}, {self.y:.2f})"

    def describe(self) -> dict:
        data = super().describe()
        data.update(
            {
                "x": self.x,
                "y": self.y,
                "point_1": self.p1.name,
                "point_2": self.p2.name,
            }
        )
        return data


class GeoLine(GeoNode):
    def __init__(self, name: str, p1: GeoNode, p2: GeoNode):
        super().__init__(name, dependencies=[p1, p2])
        self.p1 = p1
        self.p2 = p2
        self.a = 0.0
        self.b = 0.0
        self.c = 0.0
        self.compute()

    def compute(self):
        self.a = self.p2.y - self.p1.y
        self.b = self.p1.x - self.p2.x
        self.c = self.p2.x * self.p1.y - self.p1.x * self.p2.y

    def __str__(self):
        terms = []
        if not math.isclose(self.a, 0):
            terms.append(f"{self.a:.2f}x")
        if not math.isclose(self.b, 0):
            sign = "+" if self.b > 0 and terms else ""
            terms.append(f"{sign}{self.b:.2f}y")
        if not math.isclose(self.c, 0):
            sign = "+" if self.c > 0 and terms else ""
            terms.append(f"{sign}{self.c:.2f}")

        equation = " ".join(terms).replace("+ -", "- ")
        return f"Line {self.name}: {equation if equation else '0'} = 0"

    def describe(self) -> dict:
        data = super().describe()
        data.update(
            {
                "point_1": self.p1.name,
                "point_2": self.p2.name,
                "a": self.a,
                "b": self.b,
                "c": self.c,
            }
        )
        return data


class GeoIntersection(GeoNode):
    def __init__(self, name: str, l1: GeoLine, l2: GeoLine):
        super().__init__(name, dependencies=[l1, l2])
        self.l1 = l1
        self.l2 = l2
        self.x = 0.0
        self.y = 0.0
        self.exists = False
        self.is_free = False
        self.compute()

    def compute(self):
        det = self.l1.a * self.l2.b - self.l2.a * self.l1.b
        if math.isclose(det, 0):
            self.exists = False
        else:
            self.x = (self.l1.b * self.l2.c - self.l2.b * self.l1.c) / det
            self.y = (self.l2.a * self.l1.c - self.l1.a * self.l2.c) / det
            self.exists = True

    def __str__(self):
        if not self.exists:
            return f"{self.name} (Intersect) = Undefined"
        return f"{self.name} (Intersect) = ({self.x:.2f}, {self.y:.2f})"

    def describe(self) -> dict:
        data = super().describe()
        data.update(
            {
                "line_1": self.l1.name,
                "line_2": self.l2.name,
                "exists": self.exists,
                "x": self.x,
                "y": self.y,
            }
        )
        return data


class GeoCircle(GeoNode):
    def __init__(self, name: str, center: GeoNode, edge: GeoNode):
        super().__init__(name, dependencies=[center, edge])
        self.center = center
        self.edge = edge
        self.radius = 0.0
        self.compute()

    def compute(self):
        dx = self.edge.x - self.center.x
        dy = self.edge.y - self.center.y
        self.radius = math.hypot(dx, dy)

    def __str__(self):
        hs = "-" if self.center.x > 0 else "+"
        ks = "-" if self.center.y > 0 else "+"
        return (
            f"Circle {self.name}: (x {hs} {abs(self.center.x):.2f})^2 + "
            f"(y {ks} {abs(self.center.y):.2f})^2 = {self.radius**2:.2f}"
        )

    def describe(self) -> dict:
        data = super().describe()
        data.update(
            {
                "center": self.center.name,
                "edge": self.edge.name,
                "radius": self.radius,
            }
        )
        return data


class GeoVector(GeoNode):
    def __init__(self, name: str, origin: GeoPoint, terminal: GeoPoint):
        super().__init__(name, dependencies=[origin, terminal])
        self.origin = origin
        self.terminal = terminal
        self.dx = 0.0
        self.dy = 0.0
        self.magnitude = 0.0
        self.compute()

    def compute(self):
        self.dx = self.terminal.x - self.origin.x
        self.dy = self.terminal.y - self.origin.y
        self.magnitude = math.hypot(self.dx, self.dy)

    def __str__(self):
        return f"Vector {self.name} = [{self.dx:.2f}, {self.dy:.2f}]"

    def describe(self) -> dict:
        data = super().describe()
        data.update(
            {
                "origin": self.origin.name,
                "terminal": self.terminal.name,
                "dx": self.dx,
                "dy": self.dy,
                "magnitude": self.magnitude,
            }
        )
        return data


class GeoInequality(GeoNode):
    def __init__(self, name: str, boundary: GeoLine, operator: str = "<="):
        super().__init__(name, dependencies=[boundary])
        self.boundary = boundary
        self.operator = operator
        self.compute()

    def compute(self):
        pass

    def evaluate(self, x: float, y: float) -> bool:
        val = self.boundary.a * x + self.boundary.b * y + self.boundary.c
        if self.operator == "<=":
            return val <= 0
        if self.operator == ">=":
            return val >= 0
        if self.operator == "<":
            return val < 0
        if self.operator == ">":
            return val > 0
        return False

    def __str__(self):
        line_str = str(self.boundary).split(":")[1].strip().replace("= 0", "")
        return f"Inequality {self.name}: {line_str} {self.operator} 0"

    def describe(self) -> dict:
        data = super().describe()
        data.update({"boundary": self.boundary.name, "operator": self.operator})
        return data


class GeoLinearProgram(GeoNode):
    def __init__(
        self,
        name: str,
        inequalities: List[GeoInequality],
        objective: GeoLine,
        maximize: bool = True,
    ):
        super().__init__(name, dependencies=inequalities + [objective])
        self.inequalities = inequalities
        self.objective = objective
        self.maximize = maximize
        self.optimal_x = 0.0
        self.optimal_y = 0.0
        self.exists = False
        self.is_free = False
        self.compute()

    def compute(self):
        lines = [ineq.boundary for ineq in self.inequalities]
        intersections = []
        for i in range(len(lines)):
            for j in range(i + 1, len(lines)):
                l1, l2 = lines[i], lines[j]
                det = l1.a * l2.b - l2.a * l1.b
                if not math.isclose(det, 0):
                    x = (l1.b * l2.c - l2.b * l1.c) / det
                    y = (l2.a * l1.c - l1.a * l2.c) / det
                    intersections.append((x, y))

        valid_vertices = []
        for x, y in intersections:
            valid = True
            for ineq in self.inequalities:
                val = ineq.boundary.a * x + ineq.boundary.b * y + ineq.boundary.c
                if ineq.operator == "<=" and val > 1e-5:
                    valid = False
                elif ineq.operator == ">=" and val < -1e-5:
                    valid = False
            if valid:
                valid_vertices.append((x, y))

        if not valid_vertices:
            self.exists = False
            return

        self.exists = True
        best_val = -float("inf") if self.maximize else float("inf")
        best_pt = valid_vertices[0]

        for x, y in valid_vertices:
            val = self.objective.a * x + self.objective.b * y
            if self.maximize and val > best_val:
                best_val, best_pt = val, (x, y)
            elif not self.maximize and val < best_val:
                best_val, best_pt = val, (x, y)

        self.optimal_x, self.optimal_y = best_pt

    def __str__(self):
        if not self.exists:
            return f"{self.name} (Optimal) = No Feasible Region"
        return f"{self.name} (Optimal) = ({self.optimal_x:.2f}, {self.optimal_y:.2f})"

    def describe(self) -> dict:
        data = super().describe()
        data.update(
            {
                "objective": self.objective.name,
                "inequalities": [ineq.name for ineq in self.inequalities],
                "maximize": self.maximize,
                "exists": self.exists,
                "optimal_x": self.optimal_x,
                "optimal_y": self.optimal_y,
            }
        )
        return data


class GeoTransformedPoint(GeoNode):
    def __init__(self, name: str, source_point: GeoPoint, v_i: GeoVector, v_j: GeoVector):
        super().__init__(name, dependencies=[source_point, v_i, v_j])
        self.source_point = source_point
        self.v_i = v_i
        self.v_j = v_j
        self.x = 0.0
        self.y = 0.0
        self.is_free = False
        self.compute()

    def compute(self):
        px = self.source_point.x / 100.0
        py = self.source_point.y / 100.0
        self.x = px * self.v_i.dx + py * self.v_j.dx
        self.y = px * self.v_i.dy + py * self.v_j.dy

    def __str__(self):
        return f"{self.name} (Transformed) = ({self.x:.2f}, {self.y:.2f})"

    def describe(self) -> dict:
        data = super().describe()
        data.update(
            {
                "source_point": self.source_point.name,
                "basis_i": self.v_i.name,
                "basis_j": self.v_j.name,
                "x": self.x,
                "y": self.y,
            }
        )
        return data


class GeoImplicitCurve(GeoNode):
    """An implicit algebraic curve defined by f(x, y) = 0."""

    def __init__(
        self,
        name: str,
        expression_text: str,
        evaluator: Callable[[np.ndarray, np.ndarray], np.ndarray],
        bounds: tuple[float, float, float, float] = (-10.0, 10.0, -10.0, 10.0),
        resolution: int = 240,
    ):
        super().__init__(name)
        self.expression_text = expression_text
        self.evaluator = evaluator
        self.bounds = bounds
        self.resolution = max(64, int(resolution))
        self.contours: list[list[tuple[float, float]]] = []
        self.compute()

    def set_view_bounds(
        self,
        bounds: tuple[float, float, float, float],
        resolution: Optional[int] = None,
    ):
        self.bounds = bounds
        if resolution is not None:
            self.resolution = max(64, int(resolution))
        self.compute()
        self.notify_observers()

    def compute(self):
        self.contours = self._sample_contours()

    def _sample_contours(self) -> list[list[tuple[float, float]]]:
        xmin, xmax, ymin, ymax = self.bounds
        if xmin >= xmax or ymin >= ymax:
            return []

        xs = np.linspace(xmin, xmax, self.resolution)
        ys = np.linspace(ymax, ymin, self.resolution)
        x_grid, y_grid = np.meshgrid(xs, ys)

        z = np.asarray(self.evaluator(x_grid, y_grid), dtype=float)
        if z.shape != x_grid.shape:
            z = np.broadcast_to(z, x_grid.shape).astype(float)

        z = np.where(np.isfinite(z), z, np.nan)
        if np.all(np.isnan(z)):
            return []

        finite = z[np.isfinite(z)]
        fill_value = (float(np.max(np.abs(finite))) + 1.0) if finite.size else 1.0
        z = np.nan_to_num(z, nan=fill_value, posinf=fill_value, neginf=-fill_value)

        segments: list[list[tuple[float, float]]] = []
        for contour in measure.find_contours(z, level=0.0):
            points: list[tuple[float, float]] = []
            for row, col in contour:
                x = xmin + (col / (self.resolution - 1)) * (xmax - xmin)
                y = ymax - (row / (self.resolution - 1)) * (ymax - ymin)
                points.append((float(x), float(y)))
            if len(points) >= 2:
                segments.append(points)
        return segments

    def __str__(self):
        return f"Curve {self.name}: {self.expression_text} = 0"

    def describe(self) -> dict:
        data = super().describe()
        data.update(
            {
                "expression": self.expression_text,
                "bounds": self.bounds,
                "resolution": self.resolution,
                "contours": len(self.contours),
            }
        )
        return data
