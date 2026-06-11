import sympy
import re
from sympy.parsing.sympy_parser import (
    parse_expr, 
    standard_transformations, 
    implicit_multiplication_application, 
    convert_xor
)

def _preprocess_natural_syntax(command: str) -> str:
    """Translates natural math language into SymPy interpretable strings."""
    
    # 1. Limits: 'lim x->0 sin(x)/x' -> 'limit(sin(x)/x, x, 0)'
    command = re.sub(r'lim(?:it)?\s+([a-zA-Z_]\w*)\s*(?:->|to)\s*([^\s]+)\s+(.*)', r'limit(\3, \1, \2)', command)
    
    # 2. Derivatives: 'd/dx (x^2)' -> 'diff((x^2), x)'
    command = re.sub(r'd/d([a-zA-Z_]\w*)\s*(.*)', r'diff(\2, \1)', command)
    
    # 3. Definite Integrals: 'int_0^5 x^2 dx' -> 'integrate(x^2, (x, 0, 5))'
    command = re.sub(r'int(?:egral)?_([^\^]+)\^([^\s]+)\s+(.*?)d([a-zA-Z_]\w*)', r'integrate(\3, (\4, \1, \2))', command)
    
    # 4. Indefinite Integrals: 'int x^2 dx' -> 'integrate(x^2, x)'
    command = re.sub(r'int(?:egral)?\s+(.*?)d([a-zA-Z_]\w*)', r'integrate(\1, \2)', command)
    
    # 5. Summation: 'sum_n=1^10 n^2' -> 'summation(n^2, (n, 1, 10))'
    command = re.sub(r'sum_([a-zA-Z_]\w*)=([^\^]+)\^([^\s]+)\s+(.*)', r'summation(\4, (\1, \2, \3))', command)
    
    # 6. Binomial/Combinatorics (nCr -> binomial)
    command = command.replace('nCr', 'binomial')
    
    return command.strip()

def execute_simple_math(command: str, latex_formatter):
    """
    Evaluates math using standard human notation rather than rigorous Mathematica syntax.
    Mimics Wolfram Alpha's structured "Exact Form" and "Approximate Form" logic natively.
    """
    # Block Mathematica Syntax
    if re.search(r'[A-Z][a-zA-Z]*\[', command):
        return "<span style='color: #e06c75'><b>Syntax Error:</b> Please toggle Simple Mode OFF to use Mathematica syntax.</span>"

    try:
        # Preprocess natural human syntax into SymPy machine syntax
        command = _preprocess_natural_syntax(command)

        # Set up SymPy to understand human-written math (e.g. 2x -> 2*x, and x^2 -> x**2)
        transformations = standard_transformations + (implicit_multiplication_application, convert_xor)
        
        # --- PATH 1: Handle Equation Solving (e.g., x^3-x^2+56=21) ---
        if "=" in command and "==" not in command:
            lhs_str, rhs_str = command.split("=", 1)
            lhs = parse_expr(lhs_str.strip(), transformations=transformations)
            rhs = parse_expr(rhs_str.strip(), transformations=transformations)
            
            eq = sympy.Eq(lhs, rhs)
            symbols = list(eq.free_symbols)
            
            # If there are no variables (e.g., 5 = 5)
            if not symbols:
                return latex_formatter(lhs == rhs)
            
            var = symbols[0]
            
            # Use SymPy to solve it algebraically
            sols = sympy.solve(eq, var)
            
            if not sols:
                return "<span style='color: #e06c75'><b>Result:</b> No solutions found over the complex plane.</span>"
            
            # Categorize solutions into Real and Complex using numerical validation
            real_sols = []
            complex_sols = []
            for s in sols:
                approx = s.evalf(15)
                if approx.has(sympy.I) and abs(sympy.im(approx)) > 1e-9:
                    complex_sols.append(s)
                else:
                    real_sols.append(s)

            # Build Wolfram-Alpha style HTML output
            input_latex = sympy.latex(eq)
            html = f"<div style='margin-bottom: 15px; padding-bottom: 5px; border-bottom: 1px dashed #3e3e42;'><span style='color: #61afef; font-family: sans-serif; font-size: 12px;'>Input interpretation:</span><br>\\( {input_latex} \\)</div>"
            
            def format_roots(roots, title, color):
                section_html = f"<div style='margin-top: 10px; color: {color}; font-family: sans-serif; font-size: 13px; font-weight: bold;'>{title}:</div>"
                for s in roots:
                    approx = s.evalf(5)
                    
                    if approx.has(sympy.I):
                        approx = sympy.re(approx).round(5) + sympy.im(approx).round(5) * sympy.I
                    elif approx.is_real or not approx.has(sympy.I):
                        approx = sympy.re(approx).round(5)

                    exact_str = str(s)
                    
                    if len(exact_str) > 60:
                        section_html += latex_formatter(approx, prefix=f"{var} \\approx ")
                    else:
                        exact_latex = latex_formatter(s, prefix=f"{var} = ")
                        
                        if exact_str != str(approx) and not s.is_Integer:
                            approx_latex = latex_formatter(approx, prefix="\\approx ")
                            section_html += f"<div style='display: flex; align-items: center;'>{exact_latex} <span style='margin-left: 10px; margin-right: 10px; color: #5c6370;'>|</span> {approx_latex}</div>"
                        else:
                            section_html += exact_latex
                return section_html

            if real_sols:
                html += format_roots(real_sols, "Real solutions", "#98c379")
                
            if complex_sols:
                html += format_roots(complex_sols, "Complex solutions", "#e5c07b")
                
            return html
        
        # --- PATH 2: Handle Advanced Expressions (Limits, Derivatives, Integrals) ---
        else:
            expr = parse_expr(command, transformations=transformations)
            
            # Print Interpretation
            input_latex = sympy.latex(expr)
            html = f"<div style='margin-bottom: 15px; padding-bottom: 5px; border-bottom: 1px dashed #3e3e42;'><span style='color: #61afef; font-family: sans-serif; font-size: 12px;'>Input interpretation:</span><br>\\( {input_latex} \\)</div>"
            
            # Force evaluate Limit/Integral/Derivative objects if they are pending
            exact = expr.doit() if hasattr(expr, 'doit') else expr
            
            if not exact.free_symbols:
                exact = sympy.simplify(exact)
                approx = exact.evalf(5)
                # Show both exact and decimal form if it's a messy fraction/root
                if str(exact) != str(approx) and len(str(exact)) > 5:
                    approx_str = latex_formatter(approx, prefix='\\approx ')
                    exact_str = latex_formatter(exact, prefix='= ')
                    html += f"<div style='display: flex; align-items: center;'>{exact_str} <span style='margin: 0 10px; color: #5c6370;'>|</span> {approx_str}</div>"
                    return html
                
                html += latex_formatter(exact, prefix='= ')
                return html
            else:
                html += latex_formatter(sympy.simplify(exact), prefix='= ')
                return html
            
    except Exception as e:
        return f"<span style='color: #e06c75'><b>Simple Mode Error:</b> Could not parse or solve the equation. Check your syntax.</span><br><span style='color: #666; font-size: 12px;'>Details: {str(e)}</span>"