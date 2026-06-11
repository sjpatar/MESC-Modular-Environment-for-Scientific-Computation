import pytest

from ides.geogebra.engine.graph import GeoImplicitCurve, GeoIntersection, GeoLine, GeoPoint
from ides.geogebra.engine.parser import CommandProcessor


def test_point_command_creates_named_point():
    processor = CommandProcessor()

    node = processor.parse_and_execute("A = (2, -3.5)")

    assert isinstance(node, GeoPoint)
    assert processor.namespace["A"] is node
    assert node.x == pytest.approx(2.0)
    assert node.y == pytest.approx(-3.5)


def test_geometry_constructor_commands_use_existing_objects():
    processor = CommandProcessor()
    processor.parse_and_execute("A = (0, 0)")
    processor.parse_and_execute("B = (4, 4)")
    processor.parse_and_execute("C = (0, 4)")
    processor.parse_and_execute("D = (4, 0)")

    first = processor.parse_and_execute("l1 = line(A, B)")
    second = processor.parse_and_execute("l2 = line(C, D)")
    point = processor.parse_and_execute("P = intersect(l1, l2)")

    assert isinstance(first, GeoLine)
    assert isinstance(second, GeoLine)
    assert isinstance(point, GeoIntersection)
    assert point.exists is True
    assert point.x == pytest.approx(2.0)
    assert point.y == pytest.approx(2.0)


def test_curve_wrapper_command_builds_implicit_curve():
    processor = CommandProcessor()

    curve = processor.parse_and_execute("C = curve(x^2 + y^2 - 4)")

    assert isinstance(curve, GeoImplicitCurve)
    assert curve.expression_text == "x^2 + y^2 - 4"
    assert len(curve.contours) > 0


def test_equation_syntax_builds_curve():
    processor = CommandProcessor()

    curve = processor.parse_and_execute("Folium: x^3 + y^3 = 3*x*y")

    assert isinstance(curve, GeoImplicitCurve)
    assert "x^3" in curve.expression_text
    assert len(curve.contours) > 0


def test_curve_rejects_non_polynomial_expression():
    processor = CommandProcessor()

    with pytest.raises(ValueError, match="Only polynomial implicit curves"):
        processor.parse_and_execute("Bad = curve(sin(x) - y)")


def test_duplicate_names_are_rejected():
    processor = CommandProcessor()
    processor.parse_and_execute("A = (1, 1)")

    with pytest.raises(ValueError, match="already exists"):
        processor.parse_and_execute("A = (2, 2)")


def test_assamese_command_aliases_are_supported():
    processor = CommandProcessor(language_getter=lambda: "as")
    processor.parse_and_execute("A = (0, 0)")
    processor.parse_and_execute("B = (2, 2)")

    line = processor.parse_and_execute("l1 = ৰেখা(A, B)")
    midpoint = processor.parse_and_execute("M = মধ্যবিন্দু(A, B)")
    vector = processor.parse_and_execute("V = ভেক্টৰ(A, B)")
    curve = processor.parse_and_execute("C = বক্ৰৰেখা(x^2 + y^2 - 1)")

    assert isinstance(line, GeoLine)
    assert midpoint.x == pytest.approx(1.0)
    assert midpoint.y == pytest.approx(1.0)
    assert vector.dx == pytest.approx(2.0)
    assert isinstance(curve, GeoImplicitCurve)
