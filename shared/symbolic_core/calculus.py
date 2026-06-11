try:
    import sympy as sp
    HAS_SYMPY = True
except ImportError:
    HAS_SYMPY = False

def diff(expr_str: str, var_str: str = 'x', n: int = 1):
    if not HAS_SYMPY:
        return "Error: SymPy not installed."
    
    x = sp.symbols(var_str)
    # Parse string to sympy expression
    expr = sp.sympify(expr_str)
    return sp.diff(expr, x, n)

def int_func(expr_str: str, var_str: str = 'x'):
    if not HAS_SYMPY:
        return "Error: SymPy not installed."
        
    x = sp.symbols(var_str)
    expr = sp.sympify(expr_str)
    return sp.integrate(expr, x)