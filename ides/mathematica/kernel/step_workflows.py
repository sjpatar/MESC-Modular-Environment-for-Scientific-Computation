import sympy
from sympy import Derivative, Integral, Limit, Product, Sum, latex

from .common_types import StepResult
from .i18n import tr
from .nstep_logic import generate_nsteps
from .solver_logic import nsteps_mathematica_style, steps_mathematica_style
from .step_logic import StepDet, StepEigenvals, StepInv, generate_steps


ALGEBRA_HEADS = {"Simplify", "FullSimplify", "Expand", "Factor", "Apart", "Together"}
CALCULUS_HEADS = {"Integrate", "Integral", "D", "Diff", "Derivative", "Limit"}
MATRIX_HEADS = {"Det", "Inverse", "Eigenvalues"}
SERIES_HEADS = {"Sum", "Product"}
SOLVER_HEADS = {"Solve", "NSolve"}
UNSUPPORTED_UI_HEADS = {"Plot", "Plot3D", "Manipulate"}


def _latex(obj):
    try:
        return latex(obj)
    except Exception:
        return str(obj)


def _build_card(title, lines, result, formal=False):
    html = "<div style='font-family: Consolas; margin: 10px; color: #d4d4d4; text-align: left;'>"
    html += (
        f"<div style='color: #61afef; margin-bottom: 12px; border-bottom: 1px solid #3e3e42; "
        f"padding-bottom: 4px; font-weight: bold; font-size: 1.1em;'>{title}</div>"
    )

    for line in lines:
        html += f"<div style='margin-bottom: 12px;'>{line}</div>"

    result_label = tr("math_result")
    html += f"""
    <div style='color: #98c379; margin-top: 15px; font-weight: bold; border-top: 1px solid #3e3e42; padding-top: 5px; text-align: left;'>
        {result_label}: \\( \\displaystyle {_latex(result)} \\)
    </div>
    </div>
    """
    return StepResult(html)


def _same_expression(lhs, rhs):
    try:
        return sympy.simplify(lhs - rhs) == 0
    except Exception:
        return lhs == rhs


def build_inert_step_target(func_name, evaluated_args):
    if func_name in {"Integrate", "Integral"}:
        return Integral(*evaluated_args)
    if func_name in {"D", "Diff", "Derivative"}:
        return Derivative(*evaluated_args)
    if func_name == "Limit":
        return Limit(*evaluated_args)
    if func_name == "Det":
        return StepDet(evaluated_args[0])
    if func_name == "Inverse":
        return StepInv(evaluated_args[0])
    if func_name == "Eigenvalues":
        return StepEigenvals(evaluated_args[0])
    return None


def generate_command_steps(func_name, evaluated_args, formal=False):
    if func_name in UNSUPPORTED_UI_HEADS:
        return StepResult(
            f"<span style='color: #e06c75'><b>{tr('err_step_gen')}:</b> {tr('err_step_gen_ui')}</span>"
        )

    if func_name in SOLVER_HEADS:
        expr = evaluated_args[0] if evaluated_args else None
        variables = tuple(evaluated_args[1:])
        if formal:
            return nsteps_mathematica_style(expr, *variables)
        return steps_mathematica_style(expr, *variables, numeric=(func_name == "NSolve"))

    if func_name in ALGEBRA_HEADS:
        return generate_algebra_steps(func_name, evaluated_args[0], formal=formal)

    if func_name in SERIES_HEADS:
        return generate_series_steps(func_name, evaluated_args, formal=formal)

    inert_target = build_inert_step_target(func_name, evaluated_args)
    if inert_target is not None:
        return generate_nsteps(inert_target) if formal else generate_steps(inert_target)

    return None


def generate_expression_steps(expr, formal=False):
    if isinstance(expr, sympy.Rel):
        return nsteps_mathematica_style(expr) if formal else steps_mathematica_style(expr)

    title = tr("title_formal_expression_steps") if formal else tr("title_expression_steps")
    lines = [f"{tr('math_input')}: \\( {_latex(expr)} \\)"] if formal else [f"{tr('math_start_with')} \\( {_latex(expr)} \\)."]

    seen = {sympy.srepr(expr)}

    candidates = [
        ("Expand", sympy.expand(expr)),
        ("Together", sympy.together(expr)),
        ("Cancel", sympy.cancel(expr)),
        ("Factor", sympy.factor(expr)),
    ]

    simplifiable = expr.doit() if hasattr(expr, "doit") else expr
    candidates.append(("Simplify", sympy.simplify(simplifiable)))

    current = expr
    for label, candidate in candidates:
        key = sympy.srepr(candidate)
        if key in seen or _same_expression(candidate, current):
            continue
        seen.add(key)
        if formal:
            lines.append(
                f"<div style='color: #61afef; font-weight: bold; margin-top: 15px;'>"
                f"{label}:</div>\\( \\displaystyle {_latex(current)} \\to {_latex(candidate)} \\)"
            )
        else:
            lines.append(f"{tr('math_apply_rule')} {label.lower()} to obtain \\( {_latex(candidate)} \\).")
        current = candidate

    return _build_card(title, lines, current, formal=formal)


def generate_algebra_steps(head, expr, formal=False):
    lines = []
    if formal:
        lines.append(f"\\( \\displaystyle {_latex(expr)} \\)")
    else:
        lines.append(f"{tr('math_start_with')} \\( {_latex(expr)} \\).")

    try:
        if head == "Expand":
            result = sympy.expand(expr)
            lines.append(tr("math_distribute") if not formal else "\\( \\text{Distribute products and powers across sums.} \\)")
        elif head == "Factor":
            result = sympy.factor(expr)
            lines.append(tr("math_factor_common") if not formal else "\\( \\text{Factor common and polynomial terms.} \\)")
        elif head == "Together":
            result = sympy.together(expr)
            lines.append(tr("math_common_denominator") if not formal else "\\( \\text{Combine rational terms over a common denominator.} \\)")
        elif head == "Apart":
            result = sympy.apart(expr)
            lines.append(tr("math_partial_fractions") if not formal else "\\( \\text{Apply partial-fraction decomposition.} \\)")
        else:
            together = sympy.together(expr)
            canceled = sympy.cancel(together)
            result = sympy.simplify(canceled)
            if together != expr:
                lines.append(f"{tr('math_common_denominator_form')}: \\( {_latex(together)} \\)")
            if canceled != together:
                lines.append(f"{tr('math_cancel_common')}: \\( {_latex(canceled)} \\)")
            lines.append(tr("math_simplify_remaining") if not formal else "\\( \\text{Simplify the remaining expression.} \\)")
    except Exception:
        result = sympy.simplify(expr)
        lines.append(tr("math_general_simplify") if not formal else "\\( \\text{Fall back to general symbolic simplification.} \\)")

    lines.append(f"\\( \\displaystyle {_latex(result)} \\)")
    return _build_card(f"{head}: {tr('title_expression_steps')}", lines, result, formal=formal)


def generate_series_steps(head, evaluated_args, formal=False):
    operator = Sum if head == "Sum" else Product
    result = operator(*evaluated_args)
    evaluated = result.doit()

    lines = []
    if formal:
        lines.append(f"\\( \\displaystyle {_latex(result)} \\)")
        lines.append(tr("math_eval_operator_formal"))
        lines.append(f"\\( \\displaystyle = {_latex(evaluated)} \\)")
    else:
        lines.append(f"{tr('math_interpret_as')} \\( {_latex(result)} \\).")
        lines.append(tr("math_eval_operator"))
        lines.append(f"\\( {_latex(evaluated)} \\)")

    return _build_card(f"{head}: {tr('title_expression_steps')}", lines, evaluated, formal=formal)
