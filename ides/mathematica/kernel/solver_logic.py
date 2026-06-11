import sympy
from sympy import Eq, Poly, diff, latex
from sympy.core.relational import Relational

from .common_types import SolutionResult, StepResult
from .i18n import step_heading, tr


def _latex_or_text(obj):
    try:
        return latex(obj)
    except Exception:
        return str(obj)


def _build_step_card(title, lines, result):
    html = "<div style='font-family: Consolas; margin: 10px; color: #d4d4d4; text-align: left;'>"
    html += (
        f"<div style='color: #61afef; margin-bottom: 12px; border-bottom: 1px solid #3e3e42; "
        f"padding-bottom: 4px; font-weight: bold; font-size: 1.1em;'>{title}</div>"
    )

    for line in lines:
        html += f"<div style='margin-bottom: 12px;'>{line}</div>"

    html += f"""
    <div style='color: #98c379; margin-top: 15px; font-weight: bold; border-top: 1px solid #3e3e42; padding-top: 5px; text-align: left;'>
        {tr('math_result')}: \\( \\displaystyle {_latex_or_text(result)} \\)
    </div>
    </div>
    """
    return StepResult(html)


def _flatten_symbols(symbols):
    flat = []
    for item in symbols:
        if isinstance(item, sympy.Symbol):
            flat.append(item)
        elif isinstance(item, (list, tuple, sympy.Tuple, sympy.FiniteSet)):
            flat.extend(_flatten_symbols(tuple(item)))
        elif isinstance(item, sympy.MatrixBase):
            flat.extend(_flatten_symbols(tuple(item)))
    return flat


def _normalize_equations(expr):
    if isinstance(expr, (list, tuple, sympy.Tuple, sympy.FiniteSet)):
        normalized = []
        for item in expr:
            normalized.extend(_normalize_equations(item))
        return normalized
    if isinstance(expr, Relational):
        return [Eq(expr.lhs, expr.rhs)]
    return [expr]


def _normalize_symbols(symbols, expr):
    flat = _flatten_symbols(symbols)
    ordered = []
    seen = set()

    for symbol in flat:
        if symbol not in seen:
            ordered.append(symbol)
            seen.add(symbol)

    if ordered:
        return ordered

    free_symbols = []
    equations = _normalize_equations(expr)
    for item in equations:
        source = item.lhs - item.rhs if isinstance(item, Eq) else item
        for symbol in sorted(source.free_symbols, key=lambda s: s.name):
            if symbol not in seen:
                free_symbols.append(symbol)
                seen.add(symbol)
    return free_symbols


def _result_expression(solution_dicts, variables):
    if not solution_dicts:
        return sympy.EmptySet

    if len(variables) == 1:
        target = variables[0]
        values = []
        seen = set()
        for solution in solution_dicts:
            if target not in solution:
                continue
            value = sympy.simplify(solution[target])
            key = sympy.srepr(value)
            if key not in seen:
                values.append(value)
                seen.add(key)

        if not values:
            return sympy.EmptySet
        if len(values) == 1:
            return Eq(target, values[0])
        return Eq(target, sympy.FiniteSet(*values))

    tuples = []
    for solution in solution_dicts:
        tuples.append(sympy.Tuple(*(sympy.simplify(solution.get(var, var)) for var in variables)))
    return sympy.FiniteSet(*tuples)


def _coerce_solution_dicts(raw, variables):
    if raw is None:
        return []

    if isinstance(raw, dict):
        return [raw]

    if isinstance(raw, (list, tuple)):
        if raw and all(isinstance(item, dict) for item in raw):
            return list(raw)
        if len(variables) == 1:
            var = variables[0]
            return [{var: item} for item in raw]

    return []


def _numeric_guesses():
    return [-10, -5, -2, -1, -0.5, 0.5, 1, 2, 5, 10]


def _numeric_solutions(expr, variables):
    if not variables:
        return []

    target = variables[0]
    equations = _normalize_equations(expr)
    if len(equations) != 1:
        return []

    equation = equations[0]
    function = equation.lhs - equation.rhs if isinstance(equation, Eq) else equation
    found = []
    solutions = []

    for guess in _numeric_guesses():
        try:
            root = sympy.nsolve(function, target, guess)
        except Exception:
            continue

        if any(abs(complex(root.evalf()) - complex(existing.evalf())) < 1e-7 for existing in found):
            continue

        found.append(root)
        solutions.append({target: sympy.nsimplify(root)})

    return solutions


def solve_mathematica_style(expr, *symbols):
    variables = _normalize_symbols(symbols, expr)
    if not variables:
        return tr("math_no_variables_found_to_solve")

    equations = _normalize_equations(expr)
    target = variables if len(variables) > 1 else variables[0]

    try:
        raw = sympy.solve(equations if len(equations) > 1 else equations[0], target, dict=True)
        solution_dicts = _coerce_solution_dicts(raw, variables)
        if solution_dicts:
            return SolutionResult(solution_dicts)
    except Exception:
        pass

    numeric = _numeric_solutions(expr, variables)
    if numeric:
        return SolutionResult(numeric)

    return tr("math_no_symbolic_solution")


def nsolve_mathematica_style(expr, *symbols):
    variables = _normalize_symbols(symbols, expr)
    if not variables:
        return tr("math_no_variables_found_to_solve")

    numeric = _numeric_solutions(expr, variables)
    if numeric:
        return SolutionResult(numeric)

    return solve_mathematica_style(expr, *variables)


def steps_mathematica_style(expr, *symbols, numeric=False):
    return _solve_with_steps(expr, *symbols, formal=False, numeric=numeric)


def nsteps_mathematica_style(expr, *symbols):
    return _solve_with_steps(expr, *symbols, formal=True, numeric=True)


def _solve_with_steps(expr, *symbols, formal=False, numeric=False):
    variables = _normalize_symbols(symbols, expr)
    if not variables:
        return tr("math_no_variables_found")

    equations = _normalize_equations(expr)
    if len(equations) > 1 or len(variables) > 1:
        return _system_steps(equations, variables, formal=formal, numeric=numeric)

    return _single_equation_steps(equations[0], variables[0], formal=formal, numeric=numeric)


def _system_steps(equations, variables, formal=False, numeric=False):
    lines = []
    system_latex = ", \\; ".join(_latex_or_text(eq) for eq in equations)
    vars_latex = ", ".join(_latex_or_text(var) for var in variables)

    if formal:
        lines.append(f"{tr('math_system')}: \\( \\{{ {system_latex} \\}} \\)")
        lines.append(f"{tr('math_unknowns')}: \\( {vars_latex} \\)")
    else:
        lines.append(f"{tr('math_system')}: \\( \\{{ {system_latex} \\}} \\), {tr('math_unknowns').lower()}: \\( {vars_latex} \\).")

    try:
        matrix, vector = sympy.linear_eq_to_matrix([eq.lhs - eq.rhs for eq in equations], variables)
        augmented = matrix.row_join(vector)
        rref_matrix, _ = augmented.rref()

        if formal:
            lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 15px;'>{step_heading(1, tr('math_step_augmented_matrix'))}:</div>")
            lines.append(f"\\( \\displaystyle [A|b] = {_latex_or_text(augmented)} \\)")
            lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 15px;'>{step_heading(2, tr('math_step_row_reduction_short'))}:</div>")
            lines.append(f"\\( \\displaystyle \\operatorname{{rref}}([A|b]) = {_latex_or_text(rref_matrix)} \\)")
        else:
            lines.append(tr("math_convert_augmented"))
            lines.append(f"\\( [A|b] = {_latex_or_text(augmented)} \\)")
            lines.append(tr("math_reduce_rref"))
            lines.append(f"\\( \\operatorname{{rref}}([A|b]) = {_latex_or_text(rref_matrix)} \\)")
    except Exception:
        if formal:
            lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 15px;'>{step_heading(1, tr('math_step_symbolic_system_solve'))}:</div>")
            lines.append(tr("math_symbolic_elimination"))
        else:
            lines.append(tr("math_symbolic_elimination"))

    raw = None
    try:
        target = variables if len(variables) > 1 else variables[0]
        raw = sympy.solve(equations if len(equations) > 1 else equations[0], target, dict=True)
    except Exception:
        if numeric:
            raw = _numeric_solutions(equations[0], variables)

    solution_dicts = _coerce_solution_dicts(raw, variables)
    if not solution_dicts:
        return _build_step_card(tr("title_system_solver"), lines, sympy.EmptySet)

    if formal:
        lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 15px;'>{step_heading(3, tr('math_step_read_solutions'))}:</div>")
    else:
        lines.append(tr("math_read_solutions"))

    for solution in solution_dicts:
        assignments = ", ".join(f"{_latex_or_text(var)} = {_latex_or_text(solution[var])}" for var in variables if var in solution)
        lines.append(f"\\( {assignments} \\)")

    return _build_step_card(tr("title_system_solver"), lines, _result_expression(solution_dicts, variables))


def _single_equation_steps(expr, var, formal=False, numeric=False):
    if isinstance(expr, Eq):
        lhs, rhs = expr.lhs, expr.rhs
    else:
        lhs, rhs = expr, sympy.Integer(0)
        expr = Eq(lhs, rhs)

    function = sympy.expand(lhs - rhs)
    lines = []

    if formal:
        lines.append(f"\\( \\displaystyle {_latex_or_text(lhs)} = {_latex_or_text(rhs)} \\)")
    else:
        lines.append(f"{tr('math_start_equation')} \\( {_latex_or_text(lhs)} = {_latex_or_text(rhs)} \\).")

    if sympy.simplify(rhs) != 0:
        if formal:
            lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 15px;'>{step_heading(1, tr('math_move_terms'))}:</div>")
            lines.append(f"\\( \\displaystyle {_latex_or_text(function)} = 0 \\)")
        else:
            lines.append(tr("math_move_terms"))
            lines.append(f"\\( {_latex_or_text(function)} = 0 \\)")

    try:
        poly = Poly(function, var)
        degree = poly.degree()
    except Exception:
        poly = None
        degree = None

    if degree == 1:
        a, b = poly.all_coeffs()
        if formal:
            lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 15px;'>{step_heading(2, tr('math_step_linear_isolation'))}:</div>")
            lines.append(f"\\( \\displaystyle {_latex_or_text(a)}{_latex_or_text(var)} = {_latex_or_text(-b)} \\)")
            lines.append(f"\\( \\displaystyle {_latex_or_text(var)} = \\frac{{{_latex_or_text(-b)}}}{{{_latex_or_text(a)}}} \\)")
        else:
            lines.append(tr("math_identify_linear"))
            lines.append(f"\\( {_latex_or_text(a)}{_latex_or_text(var)} = {_latex_or_text(-b)} \\)")
            lines.append(f"\\( {_latex_or_text(var)} = \\frac{{{_latex_or_text(-b)}}}{{{_latex_or_text(a)}}} \\)")
        result = sympy.simplify(-b / a)
        return _build_step_card(tr("title_linear_equation_solution"), lines, Eq(var, result))

    if degree == 2:
        a, b, c = poly.all_coeffs()
        disc = sympy.simplify(b ** 2 - 4 * a * c)
        if formal:
            lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 15px;'>{step_heading(2, tr('math_step_identify_coefficients'))}:</div>")
            lines.append(f"\\( a = {_latex_or_text(a)}, \\; b = {_latex_or_text(b)}, \\; c = {_latex_or_text(c)} \\)")
            lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 15px;'>{step_heading(3, tr('math_step_discriminant'))}:</div>")
            lines.append(f"\\( \\Delta = b^2 - 4ac = {_latex_or_text(disc)} \\)")
            lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 15px;'>{step_heading(4, tr('math_step_quadratic_formula'))}:</div>")
            lines.append(f"\\( \\displaystyle {_latex_or_text(var)} = \\frac{{-{_latex_or_text(b)} \\pm \\sqrt{{{_latex_or_text(disc)}}}}}{{{_latex_or_text(2 * a)}}} \\)")
        else:
            lines.append(tr("math_recognize_quadratic"))
            lines.append(f"\\( a = {_latex_or_text(a)}, \\; b = {_latex_or_text(b)}, \\; c = {_latex_or_text(c)} \\)")
            lines.append(tr("math_compute_discriminant"))
            lines.append(f"\\( \\Delta = {_latex_or_text(disc)} \\)")
            lines.append(f"\\( {_latex_or_text(var)} = \\frac{{-{_latex_or_text(b)} \\pm \\sqrt{{{_latex_or_text(disc)}}}}}{{{_latex_or_text(2 * a)}}} \\)")

        res1 = sympy.simplify((-b + sympy.sqrt(disc)) / (2 * a))
        res2 = sympy.simplify((-b - sympy.sqrt(disc)) / (2 * a))
        return _build_step_card(tr("title_quadratic_equation_solution"), lines, Eq(var, sympy.FiniteSet(res1, res2)))

    if degree is not None and degree > 2:
        factored = sympy.factor(function)
        if formal:
            lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 15px;'>{step_heading(2, tr('math_step_factor_polynomial'))}:</div>")
            lines.append(f"\\( \\displaystyle {_latex_or_text(factored)} = 0 \\)")
        else:
            lines.append(tr("math_factor_polynomial"))
            lines.append(f"\\( {_latex_or_text(factored)} = 0 \\)")

        try:
            factor_pairs = sympy.factor_list(function)[1]
        except Exception:
            factor_pairs = []

        if factor_pairs:
            if formal:
                lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 15px;'>{step_heading(3, tr('math_step_zero_product'))}:</div>")
            else:
                lines.append(tr("math_zero_product_desc"))

            for base, power in factor_pairs:
                if power == 1:
                    lines.append(f"\\( {_latex_or_text(base)} = 0 \\)")
                else:
                    lines.append(f"\\( {_latex_or_text(base)}^{{{power}}} = 0 \\Rightarrow {_latex_or_text(base)} = 0 \\)")

        try:
            solutions = _coerce_solution_dicts(sympy.solve(expr, var, dict=True), [var])
        except Exception:
            solutions = []
        if solutions:
            for solution in solutions:
                lines.append(f"\\( {_latex_or_text(var)} = {_latex_or_text(solution[var])} \\)")
            return _build_step_card(tr("title_polynomial_equation_solution"), lines, _result_expression(solutions, [var]))

    try:
        symbolic = _coerce_solution_dicts(sympy.solve(expr, var, dict=True), [var])
    except Exception:
        symbolic = []

    if symbolic:
        if formal:
            lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 15px;'>{step_heading(2, tr('math_step_symbolic_solve'))}:</div>")
        else:
            lines.append(tr("math_symbolic_solve"))
        for solution in symbolic:
            lines.append(f"\\( {_latex_or_text(var)} = {_latex_or_text(solution[var])} \\)")
        return _build_step_card(tr("title_equation_solution"), lines, _result_expression(symbolic, [var]))

    derivative = diff(function, var)
    guesses = _numeric_guesses()
    numeric_solutions = _numeric_solutions(expr, [var]) if numeric or not symbolic else []

    if formal:
        lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 15px;'>{step_heading(2, tr('math_step_numerical_iteration'))}:</div>")
        lines.append(f"\\( f({_latex_or_text(var)}) = {_latex_or_text(function)} \\)")
        lines.append(f"\\( f'({_latex_or_text(var)}) = {_latex_or_text(derivative)} \\)")
        lines.append(
            f"\\( \\displaystyle {_latex_or_text(var)}_{{n+1}} = {_latex_or_text(var)}_n - "
            f"\\frac{{f({_latex_or_text(var)}_n)}}{{f'({_latex_or_text(var)}_n)}} \\)"
        )
    else:
        lines.append(tr("math_newton_fallback"))
        lines.append(f"\\( f({_latex_or_text(var)}) = {_latex_or_text(function)} \\)")
        lines.append(f"\\( f'({_latex_or_text(var)}) = {_latex_or_text(derivative)} \\)")

    for guess in guesses[:4]:
        try:
            next_value = sympy.nsolve(function, var, guess)
        except Exception:
            continue
        lines.append(f"Initial guess \\( {_latex_or_text(var)}_0 = {_latex_or_text(sympy.nsimplify(guess))} \\Rightarrow {_latex_or_text(var)} \\approx {_latex_or_text(next_value.evalf(8))} \\)")

    if not numeric_solutions:
        return _build_step_card(tr("title_numerical_root_search"), lines, sympy.EmptySet)

    for solution in numeric_solutions:
        lines.append(f"\\( {_latex_or_text(var)} \\approx {_latex_or_text(solution[var].evalf(10))} \\)")

    return _build_step_card(tr("title_numerical_root_search"), lines, _result_expression(numeric_solutions, [var]))
