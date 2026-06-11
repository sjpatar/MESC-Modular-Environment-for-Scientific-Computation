import pytest

from ides.geogebra.engine.graph import GeoLine, GeoMidpoint, GeoPoint


class TestReactiveGeometryEngine:
    def test_geopoint_initialization(self):
        point = GeoPoint("A", 2, 3)

        assert point.name == "A"
        assert point.x == pytest.approx(2.0)
        assert point.y == pytest.approx(3.0)
        assert point.is_free is True
        assert point.dependencies == []
        assert point.children == []

    def test_geoline_calculation(self):
        p1 = GeoPoint("A", 0, 0)
        p2 = GeoPoint("B", 2, 2)
        line = GeoLine("l", p1, p2)

        assert line.a == pytest.approx(2.0)
        assert line.b == pytest.approx(-2.0)
        assert line.c == pytest.approx(0.0)
        assert "Line l:" in str(line)

    def test_dag_dependency_registration(self):
        p1 = GeoPoint("A", 0, 0)
        p2 = GeoPoint("B", 1, 1)
        line = GeoLine("l", p1, p2)

        assert line.dependencies == [p1, p2]
        assert line in p1.children
        assert line in p2.children

    def test_reactive_update_propagation(self):
        p1 = GeoPoint("A", 0, 0)
        p2 = GeoPoint("B", 2, 0)
        midpoint = GeoMidpoint("M", p1, p2)
        notifications = []
        midpoint.add_observer(lambda: notifications.append("updated"))

        p2.set_coords(4, 2)

        assert midpoint.x == pytest.approx(2.0)
        assert midpoint.y == pytest.approx(1.0)
        assert notifications == ["updated"]

    def test_vertical_line_edge_case(self):
        p1 = GeoPoint("A", 2, 1)
        p2 = GeoPoint("B", 2, 5)
        line = GeoLine("v", p1, p2)

        assert line.a == pytest.approx(4.0)
        assert line.b == pytest.approx(0.0)
        assert line.c == pytest.approx(-8.0)
        assert "4.00x" in str(line)
