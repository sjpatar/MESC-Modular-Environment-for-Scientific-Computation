import re
from typing import Callable

import sympy as sp

from .graph import (
    GeoCircle,
    GeoImplicitCurve,
    GeoIntersection,
    GeoLine,
    GeoMidpoint,
    GeoPoint,
    GeoVector,
)


class CommandProcessor:
    """Parse algebra input and create first-class geometry objects."""

    POINT_RE = re.compile(
        r"^\s*([A-Za-z]\w*)\s*=\s*\(\s*([-+]?\d*\.?\d+)\s*,\s*([-+]?\d*\.?\d+)\s*\)\s*$"
    )
    FUNCTION_RE = re.compile(
        r"^\s*([A-Za-z]\w*)\s*=\s*([^\s(=]+)\((.*)\)\s*$"
    )
    EQUATION_RE = re.compile(r"^\s*([A-Za-z]\w*)\s*:\s*(.+?)\s*=\s*(.+)\s*$")

    def __init__(
        self,
        translate: Callable[[str], str] | None = None,
        language_getter: Callable[[], str] | None = None,
    ):
        self.namespace = {}
        self.last_feedback = ""
        self._translate = translate or (lambda text: text)
        self._language_getter = language_getter or (lambda: "en")
        self.examples = [
            "A = (2, 3)",
            "B = (-1, 4)",
            "l1 = line(A, B)",
            "M = midpoint(A, B)",
            "l2 = line(A, M)",
            "c1 = circle(A, B)",
            "P = intersect(l1, l2)",
            "Q = vector(A, B)",
            "C = curve(x^2 + y^2 - 25)",
            "Folium: x^3 + y^3 = 3*x*y",
            "Lemniscate = curve((x^2 + y^2)^2 - 2*(x^2 - y^2))",
        ]
        self.assamese_examples = [
            "A = (2, 3)",
            "B = (-1, 4)",
            "l1 = রেখা(A, B)",
            "M = মধ্যবিন্দু(A, B)",
            "l2 = রেখা(A, M)",
            "c1 = বৃত্ত(A, B)",
            "P = ছেদ(l1, l2)",
            "Q = ভেক্টৰ(A, B)",
            "C = বক্ৰৰেখা(x^2 + y^2 - 25)",
            "Folium: x^3 + y^3 = 3*x*y",
            "Lemniscate = বক্ৰৰেখা((x^2 + y^2)^2 - 2*(x^2 - y^2))",
        ]

    def t(self, text: str) -> str:
        return self._translate(text)

    def get_examples(self) -> list[str]:
        if self._language_getter() == "as":
            return self.assamese_examples
        return self.examples

    def parse_and_execute(self, text: str):
        text = text.strip()
        if not text:
            self.last_feedback = ""
            return None

        point_match = self.POINT_RE.match(text)
        if point_match:
            name, x_raw, y_raw = point_match.groups()
            self._ensure_name_available(name)
            node = GeoPoint(name, float(x_raw), float(y_raw))
            self.namespace[name] = node
            self.last_feedback = self.t("Created point {name}.").format(name=name)
            return node

        equation_match = self.EQUATION_RE.match(text)
        if equation_match:
            name, lhs, rhs = equation_match.groups()
            self._ensure_name_available(name)
            node = self._create_curve(name, f"({lhs}) - ({rhs})")
            self.namespace[name] = node
            self.last_feedback = self.t("Created algebraic curve {name}.").format(
                name=name
            )
            return node

        function_match = self.FUNCTION_RE.match(text)
        if function_match:
            name, func_name, arg_blob = function_match.groups()
            self._ensure_name_available(name)
            func_name = self._canonical_command(func_name.lower())
            if func_name == "curve":
                node = self._create_curve(name, arg_blob)
            else:
                args = self._split_args(arg_blob)
                node = self._dispatch_function(name, func_name, args)
            self.namespace[name] = node
            self.last_feedback = self.t("Created {type_name} {name}.").format(
                type_name=node.__class__.__name__, name=name
            )
            return node

        raise ValueError(
            self.t(
                "Unsupported command. Try examples like 'A = (2, 3)', "
                "'l1 = line(A, B)', or 'C = curve(x^2 + y^2 - 25)'."
            )
        )

    def _dispatch_function(self, name: str, func_name: str, args: list[str]):
        func_name = self._canonical_command(func_name)
        command_map = {
            "line": (GeoLine, (GeoPoint, GeoPoint)),
            "circle": (GeoCircle, (GeoPoint, GeoPoint)),
            "midpoint": (GeoMidpoint, (GeoPoint, GeoPoint)),
            "vector": (GeoVector, (GeoPoint, GeoPoint)),
            "intersect": (GeoIntersection, (GeoLine, GeoLine)),
        }
        if func_name not in command_map:
            raise ValueError(
                self.t(
                    "Unknown constructor '{func_name}'. Supported commands: "
                    "line, circle, midpoint, vector, intersect, curve."
                ).format(func_name=func_name)
            )

        constructor, expected_types = command_map[func_name]
        if len(args) != len(expected_types):
            raise ValueError(
                self.t("{func_name} expects {expected} arguments, got {actual}.").format(
                    func_name=func_name,
                    expected=len(expected_types),
                    actual=len(args),
                )
            )

        resolved = [
            self._get_named_object(arg, expected_type)
            for arg, expected_type in zip(args, expected_types)
        ]
        return constructor(name, *resolved)

    def _get_named_object(self, name: str, expected_type):
        key = name.strip()
        if key not in self.namespace:
            raise ValueError(
                self.t("Unknown object '{key}'. Create it first.").format(key=key)
            )
        obj = self.namespace[key]
        if not isinstance(obj, expected_type):
            raise ValueError(
                self.t(
                    "Object '{key}' must be a {expected_type}, got {actual_type}."
                ).format(
                    key=key,
                    expected_type=expected_type.__name__,
                    actual_type=obj.__class__.__name__,
                )
            )
        return obj

    def _create_curve(self, name: str, expression_text: str) -> GeoImplicitCurve:
        x, y = sp.symbols("x y")
        normalized = expression_text.strip().replace("^", "**")
        try:
            expr = sp.expand(sp.sympify(normalized, locals={"x": x, "y": y}))
        except Exception as exc:
            raise ValueError(
                self.t("Could not parse algebraic curve: {error}").format(error=exc)
            ) from exc

        extra_symbols = expr.free_symbols.difference({x, y})
        if extra_symbols:
            extra = ", ".join(sorted(str(symbol) for symbol in extra_symbols))
            raise ValueError(
                self.t(
                    "Curves can only use x and y. Unsupported symbols: {symbols}."
                ).format(symbols=extra)
            )

        try:
            sp.Poly(expr, x, y)
        except sp.PolynomialError as exc:
            raise ValueError(
                self.t("Only polynomial implicit curves are supported right now.")
            ) from exc

        if expr == 0:
            raise ValueError(
                self.t("The curve equation simplifies to 0 = 0 and is not drawable.")
            )

        evaluator = sp.lambdify((x, y), expr, modules=["numpy"])
        display_expr = str(expr).replace("**", "^")
        return GeoImplicitCurve(name, display_expr, evaluator)

    def _ensure_name_available(self, name: str):
        if name in self.namespace:
            raise ValueError(
                self.t(
                    "An object named '{name}' already exists. Use a new name to avoid ambiguity."
                ).format(name=name)
            )

    @staticmethod
    def _canonical_command(func_name: str) -> str:
        aliases = {
            "line": "line",
            "ৰেখা": "line",
            "রেখা": "line",
            "circle": "circle",
            "বৃত্ত": "circle",
            "midpoint": "midpoint",
            "মধ্যবিন্দু": "midpoint",
            "intersect": "intersect",
            "ছেদ": "intersect",
            "vector": "vector",
            "ভেক্টৰ": "vector",
            "ভেক্টর": "vector",
            "curve": "curve",
            "বক্ৰৰেখা": "curve",
            "বক্রৰেখা": "curve",
            "বক্ররেখা": "curve",
        }
        return aliases.get(func_name, func_name)

    @staticmethod
    def _split_args(arg_blob: str) -> list[str]:
        args = []
        depth = 0
        current = []
        for char in arg_blob:
            if char == "," and depth == 0:
                arg = "".join(current).strip()
                if arg:
                    args.append(arg)
                current = []
                continue
            if char == "(":
                depth += 1
            elif char == ")":
                depth = max(0, depth - 1)
            current.append(char)

        tail = "".join(current).strip()
        if tail:
            args.append(tail)
        return args
