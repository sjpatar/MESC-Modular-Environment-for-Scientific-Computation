import sympy
from sympy import latex, Integral, Derivative, Limit
from .common_types import StepResult
from .i18n import step_heading, tr
from .step_logic import StepDet, StepInv, StepEigenvals

def _build_formal_card(lines, result, suffix=""):
    """Creates a beautiful, strict mathematical exam-style UI."""
    html = "<div style='font-family: Consolas; margin: 10px; color: #d4d4d4; text-align: left;'>"
    
    for line in lines:
        html += f"<div style='margin-bottom: 12px;'>{line}</div>"
    
    html += f"""
    <div style='color: #98c379; margin-top: 15px; font-weight: bold; border-top: 1px solid #3e3e42; padding-top: 5px; text-align: left;'>
        {tr('math_result')}: \\( \\displaystyle {latex(result)} {suffix} \\)
    </div>
    </div>
    """
    return StepResult(html)

def generate_nsteps(expr):
    """Main router for purely mathematical NSteps[] formatting."""
    if isinstance(expr, Integral):
        return _generate_formal_integral_steps(expr)
    elif isinstance(expr, Derivative):
        return _generate_formal_derivative_steps(expr)
    elif isinstance(expr, Limit):
        return _generate_formal_limit_steps(expr)
    elif isinstance(expr, StepDet):
        return _generate_formal_det_steps(expr)
    elif isinstance(expr, StepInv):
        return _generate_formal_inv_steps(expr)
    elif isinstance(expr, StepEigenvals):
        return _generate_formal_eigenvals_steps(expr)
    else:
        return StepResult(f"<span style='color: #e06c75'>{tr('err_nsteps_not_available', type_name=type(expr).__name__)}</span>")

# --- FORMAL DERIVATIVES ---
def _generate_formal_derivative_steps(expr):
    try:
        current_expr = expr.expr
        symbols = expr.variables
        lines = []
        
        for i, symbol in enumerate(symbols):
            lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 15px;'>{step_heading(i+1)}:</div>")
            lines.append(f"\\( \\displaystyle \\frac{{\\partial}}{{\\partial {latex(symbol)}}} \\left[ {latex(current_expr)} \\right] \\)")
            
            if current_expr.is_Add:
                parts = [f"\\frac{{\\partial}}{{\\partial {latex(symbol)}}}\\left({latex(arg)}\\right)" for arg in current_expr.args]
                lines.append(f"\\( \\displaystyle = {' + '.join(parts)} \\)")
            elif current_expr.is_Mul:
                lines.append(f"\\( \\displaystyle \\text{{Product Rule: }} \\frac{{\\partial}}{{\\partial {latex(symbol)}}}(uv) = u\\frac{{\\partial v}}{{\\partial {latex(symbol)}}} + v\\frac{{\\partial u}}{{\\partial {latex(symbol)}}} \\)")
            elif hasattr(current_expr, 'args') and current_expr.args and current_expr.args[0] != symbol:
                lines.append(f"\\( \\displaystyle \\text{{Chain Rule: }} \\frac{{\\partial}}{{\\partial {latex(symbol)}}}f(g) = f'(g) \\cdot \\frac{{\\partial g}}{{\\partial {latex(symbol)}}} \\)")
                
            current_expr = sympy.diff(current_expr, symbol)
            lines.append(f"\\( \\displaystyle = {latex(current_expr)} \\)")
            
        return _build_formal_card(lines, current_expr)
    except Exception as e:
        return StepResult(f"<span style='color: #e06c75'>{tr('err_derivative_step')}: {str(e)}</span>")

# --- FORMAL LIMITS ---
def _generate_formal_limit_steps(expr):
    try:
        f = expr.args[0]
        x = expr.args[1]
        a = expr.args[2]
        lines = []
        
        lines.append(f"\\( \\displaystyle \\lim_{{{latex(x)} \\to {latex(a)}}} {latex(f)} \\)")
        num, den = f.as_numer_denom()
        
        if den == 1:
            val = f.subs(x, a)
            if val.is_finite:
                lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 15px;'>{step_heading(1, tr('math_step_direct_substitution'))}:</div>")
                lines.append(f"\\( \\displaystyle = {latex(val)} \\)")
                return _build_formal_card(lines, expr.doit())

        val_num = num.subs(x, a)
        val_den = den.subs(x, a)
        
        lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 15px;'>{step_heading(1, tr('math_step_test_substitution'))}:</div>")
        lines.append(f"\\( \\displaystyle \\implies \\frac{{{latex(val_num)}}}{{{latex(val_den)}}} \\)")
        
        if val_num == 0 and val_den == 0:
            lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 15px;'>{step_heading(2, tr('math_step_lhopital'))}:</div>")
            lines.append(f"\\( \\displaystyle \\text{{L'Hôpital's Rule: }} \\lim_{{{latex(x)} \\to {latex(a)}}} \\frac{{\\frac{{d}}{{d{latex(x)}}}[{latex(num)}]}}{{\\frac{{d}}{{d{latex(x)}}}[{latex(den)}]}} \\)")
            
            dnum = num.diff(x)
            dden = den.diff(x)
            lines.append(f"\\( \\displaystyle = \\lim_{{{latex(x)} \\to {latex(a)}}} \\frac{{{latex(dnum)}}}{{{latex(dden)}}} \\)")
            
            val2 = (dnum/dden).subs(x, a)
            lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 15px;'>{step_heading(3, tr('math_substitute'))}:</div>")
            lines.append(f"\\( \\displaystyle = {latex(val2)} \\)")
            
        return _build_formal_card(lines, expr.doit())
    except Exception as e:
        return StepResult(f"<span style='color: #e06c75'>{tr('err_limit_step')}: {str(e)}</span>")

# --- FORMAL MATRICES ---
def _generate_formal_det_steps(expr):
    try:
        mat = expr.mat
        lines = []
        if not hasattr(mat, 'is_square') or not mat.is_square:
            return StepResult(f"<span style='color:#e06c75'>{tr('math_square_matrix')}</span>")
            
        lines.append(f"\\( \\displaystyle A = {latex(mat)} \\)")
        
        if mat.shape == (2,2):
            lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 15px;'>{step_heading(1, tr('math_det_formula_2x2'))}:</div>")
            lines.append(f"\\( \\displaystyle \\det(A) = a_{{11}}a_{{22}} - a_{{12}}a_{{21}} \\)")
            lines.append(f"\\( \\displaystyle \\det(A) = ({latex(mat[0,0])})({latex(mat[1,1])}) - ({latex(mat[0,1])})({latex(mat[1,0])}) \\)")
        elif mat.shape == (3,3):
            lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 15px;'>{step_heading(1, tr('math_cofactor_row1'))}:</div>")
            lines.append(f"\\( \\displaystyle \\det(A) = {latex(mat[0,0])} \\begin{{vmatrix}} {latex(mat[1,1])} & {latex(mat[1,2])} \\\\ {latex(mat[2,1])} & {latex(mat[2,2])} \\end{{vmatrix}} " +
                         f"- {latex(mat[0,1])} \\begin{{vmatrix}} {latex(mat[1,0])} & {latex(mat[1,2])} \\\\ {latex(mat[2,0])} & {latex(mat[2,2])} \\end{{vmatrix}} " +
                         f"+ {latex(mat[0,2])} \\begin{{vmatrix}} {latex(mat[1,0])} & {latex(mat[1,1])} \\\\ {latex(mat[2,0])} & {latex(mat[2,1])} \\end{{vmatrix}} \\)")
            
            d1 = mat[1,1]*mat[2,2] - mat[1,2]*mat[2,1]
            d2 = mat[1,0]*mat[2,2] - mat[1,2]*mat[2,0]
            d3 = mat[1,0]*mat[2,1] - mat[1,1]*mat[2,0]
            
            lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 15px;'>{step_heading(2, tr('math_step_evaluate_determinant'))}:</div>")
            lines.append(f"\\( \\displaystyle \\det(A) = {latex(mat[0,0])}({latex(d1)}) - ({latex(mat[0,1])})({latex(d2)}) + ({latex(mat[0,2])})({latex(d3)}) \\)")
            
        return _build_formal_card(lines, mat.det())
    except Exception as e:
        return StepResult(f"<span style='color: #e06c75'>{tr('err_det_step')}: {str(e)}</span>")

def _generate_formal_inv_steps(expr):
    try:
        mat = expr.mat
        lines = []
        if not hasattr(mat, 'is_square') or not mat.is_square:
            return StepResult(f"<span style='color:#e06c75'>{tr('math_square_matrix')}</span>")
            
        det = mat.det()
        lines.append(f"\\( \\displaystyle A = {latex(mat)} \\)")
        lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 15px;'>{step_heading(1, tr('math_step_find_determinant'))}:</div>")
        lines.append(f"\\( \\displaystyle \\det(A) = {latex(det)} \\)")
        
        if det == 0:
            lines.append(f"\\( \\displaystyle \\det(A) = 0 \\implies A^{{-1}} \\text{{ does not exist.}} \\)")
            return _build_formal_card(lines, "Undefined")
            
        if mat.shape == (2,2):
            lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 15px;'>{step_heading(2, tr('math_step_adjugate_formula'))}:</div>")
            lines.append(f"\\( \\displaystyle A^{{-1}} = \\frac{{1}}{{\\det(A)}} \\begin{{pmatrix}} a_{{22}} & -a_{{12}} \\\\ -a_{{21}} & a_{{11}} \\end{{pmatrix}} \\)")
            adj = sympy.Matrix([[mat[1,1], -mat[0,1]], [-mat[1,0], mat[0,0]]])
            lines.append(f"\\( \\displaystyle A^{{-1}} = \\frac{{1}}{{{latex(det)}}} {latex(adj)} \\)")
        else:
            lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 15px;'>{step_heading(2, tr('math_step_row_reduction'))}:</div>")
            aug = mat.row_join(sympy.eye(mat.shape[0]))
            lines.append(f"\\( \\displaystyle [A | I] = {latex(aug)} \\)")
            lines.append(f"\\( \\displaystyle \\dots \\xrightarrow{{\\text{{RREF}}}} \\dots \\)")
            lines.append(f"\\( \\displaystyle [I | A^{{-1}}] = {latex(mat.inv().row_join(sympy.eye(mat.shape[0]))[:,mat.shape[0]:])} \\)")
            
        return _build_formal_card(lines, mat.inv())
    except Exception as e:
        return StepResult(f"<span style='color: #e06c75'>{tr('err_inverse_step')}: {str(e)}</span>")

def _generate_formal_eigenvals_steps(expr):
    try:
        mat = expr.mat
        lines = []
        if not hasattr(mat, 'is_square') or not mat.is_square:
            return StepResult(f"<span style='color:#e06c75'>{tr('math_square_matrix')}</span>")
            
        lam = sympy.Symbol('\\lambda')
        I = sympy.eye(mat.shape[0])
        char_mat = mat - lam * I
        
        lines.append(f"\\( \\displaystyle A = {latex(mat)} \\)")
        lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 15px;'>{step_heading(1, tr('math_step_characteristic_equation'))}:</div>")
        lines.append(f"\\( \\displaystyle \\det(A - \\lambda I) = 0 \\)")
        lines.append(f"\\( \\displaystyle A - \\lambda I = {latex(char_mat)} \\)")
        
        char_poly = char_mat.det()
        lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 15px;'>{step_heading(2, tr('math_step_evaluate_determinant'))}:</div>")
        lines.append(f"\\( \\displaystyle {latex(char_poly)} = 0 \\)")
        
        roots = sympy.solve(char_poly, lam)
        lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 15px;'>{step_heading(3, tr('math_step_solve_lambda'))}:</div>")
        lines.append(f"\\( \\displaystyle \\lambda \\in \\{{ {', '.join([latex(r) for r in roots])} \\}} \\)")
        
        res = sympy.Matrix(list(mat.eigenvals().keys()))
        return _build_formal_card(lines, res)
    except Exception as e:
        return StepResult(f"<span style='color: #e06c75'>{tr('err_eigenvalue_step')}: {str(e)}</span>")

# --- FORMAL INTEGRALS ---
def _generate_formal_integral_steps(expr):
    try:
        from sympy.integrals.manualintegrate import integral_steps
        integrand = expr.function
        symbol = expr.limits[0][0]
        rule = integral_steps(integrand, symbol)
        
        lines = []
        lines.append(f"\\( \\displaystyle \\int {latex(integrand)} \\, d{symbol} \\)")
        
        printer = FormalIntegralStepPrinter(symbol)
        step_lines = printer.print_steps(rule)
        lines.extend(step_lines)
        
        final_res = sympy.integrate(integrand, symbol)
        return _build_formal_card(lines, final_res, "+ C")
    except Exception as e:
        return StepResult(f"<span style='color: #e06c75'>{tr('err_integration_step')}: {str(e)}</span>")

class FormalIntegralStepPrinter:
    def __init__(self, symbol):
        self.symbol = symbol
        self.lines = []
        self.step_num = 1

    def print_steps(self, rule):
        self.lines = []
        self._walk(rule)
        return self.lines

    def _walk(self, rule):
        if not rule: return
        name = rule.__class__.__name__
        
        if name == 'PartsRule':
            u, dv = rule.u, rule.dv
            du = sympy.diff(u, self.symbol)
            v = sympy.integrate(dv, self.symbol)
            orig_int = sympy.Integral(u * dv, self.symbol)
            new_int = sympy.Integral(v * du, self.symbol)
            
            self.lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 20px;'>{step_heading(self.step_num, tr('math_integration_by_parts'))}:</div>")
            self.step_num += 1
            
            self.lines.append(f"\\( \\displaystyle \\int u \\, dv = uv - \\int v \\, du \\)")
            self.lines.append(f"\\( u = {latex(u)}, \\; dv = {latex(dv)} \\, d{self.symbol} \\)")
            self.lines.append(f"\\( du = {latex(du)} \\, d{self.symbol}, \\; v = {latex(v)} \\)")
            self.lines.append(f"\\( \\displaystyle {latex(orig_int)} = {latex(u*v)} - {latex(new_int)} \\)")
            
            if hasattr(rule, 'second_step'): self._walk(rule.second_step)
                
        elif name == 'URule':
            u_var = getattr(rule, 'u_var', sympy.Symbol('u'))
            u_func = rule.u_func
            du_dx = sympy.diff(u_func, self.symbol)
            
            self.lines.append(f"<div style='color: #61afef; font-weight: bold; margin-top: 20px;'>{step_heading(self.step_num, tr('math_substitution'))}:</div>")
            self.step_num += 1
            
            self.lines.append(f"\\( {latex(u_var)} = {latex(u_func)} \\)")
            self.lines.append(f"\\( d{latex(u_var)} = ({latex(du_dx)}) \\, d{self.symbol} \\)")
            
            if hasattr(rule, 'substep'): self._walk(rule.substep)
                
        elif name == 'AlternativeRule':
            if hasattr(rule, 'alternatives') and rule.alternatives:
                self._walk(rule.alternatives[0])
                
        elif name == 'ConstantTimesRule':
            if hasattr(rule, 'substep'): self._walk(rule.substep)
                
        elif name == 'AddRule':
            if hasattr(rule, 'substeps'):
                for sub in rule.substeps: self._walk(sub)
        else:
            if hasattr(rule, 'substep'): self._walk(rule.substep)
