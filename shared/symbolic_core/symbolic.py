import sympy
import inspect
from .arrays import MatlabArray
import numpy as np

# Use SymPy's printing for pretty output
sympy.init_printing()

def syms(*args):
    """
    MATLAB-style 'syms' command.
    syms x y z  -> Creates symbolic variables x, y, z in the WORKSPACE.
    """
    # 1. Get the caller's frame (the KernelSession execution scope)
    frame = inspect.currentframe().f_back
    
    # 2. Identify the globals dictionary where variables live
    #    (In Mathex, exec() uses a specific dict, which is frame.f_globals)
    ns = frame.f_globals
    
    created = []
    
    # 3. Handle cases: syms('x', 'y') or syms('x y')
    names = []
    for a in args:
        # User might pass "x y z" as a single string if parsed strictly
        parts = a.split() if isinstance(a, str) else [str(a)]
        names.extend(parts)
        
    # 4. Create and Inject
    for name in names:
        # Check if valid identifier
        if not name.isidentifier():
            continue
            
        # Create symbol
        s = sympy.symbols(name)
        
        # INJECT into workspace
        ns[name] = s
        created.append(name)
        
    return

# -------------------------------------------------------------------
# SYMBOLIC WRAPPERS
# -------------------------------------------------------------------

def _to_sympy(x):
    """Unwrap MatlabArray wrappers to raw SymPy/NumPy objects."""
    if isinstance(x, MatlabArray):
        # If it's a 1x1 array holding a symbol, extract it
        if x.size == 1:
            item = x._data.item()
            return item
        # If it's a matrix of symbols, return the numpy array
        return x._data
    return x

def _wrap_sympy(x):
    """Wrap SymPy result back to MatlabArray or scalar."""
    if isinstance(x, (list, tuple, np.ndarray)):
        return MatlabArray(x)
    # SymPy expression -> return as is (Python object) or wrap if you want strict typing
    # For now, let's return the raw SymPy object so it prints prettily
    return x

def diff(f, var=None, n=1):
    """
    Symbolic or Numerical differentiation.
    diff(x^2) -> 2*x
    diff([1 2 3]) -> [1 1] (Numerical difference)
    """
    f_val = _to_sympy(f)
    
    # CASE 1: Symbolic Expression
    if isinstance(f_val, (sympy.Expr, sympy.Symbol)):
        if var is None:
            # Guess variable (SymPy default)
            res = sympy.diff(f_val, n=int(n))
        else:
            res = sympy.diff(f_val, _to_sympy(var), int(n))
        return _wrap_sympy(res)

    # CASE 2: Numerical Array (MatlabArray)
    # Fallback to standard numerical diff (numpy.diff)
    if isinstance(f_val, (np.ndarray, list)):
        # MATLAB diff(A) calculates difference between elements
        return MatlabArray(np.diff(f_val, n=int(n), axis=0))
        
    return sympy.diff(f_val)

def int_func(f, var=None, a=None, b=None):
    """
    Symbolic Integration.
    int(x) -> x^2/2
    int(x, 0, 1) -> 1/2
    """
    f_val = _to_sympy(f)
    var_val = _to_sympy(var) if var is not None else None
    
    # Indefinite: int(f) or int(f, x)
    if a is None and b is None:
        if var_val is None:
            return _wrap_sympy(sympy.integrate(f_val))
        return _wrap_sympy(sympy.integrate(f_val, var_val))
        
    # Definite: int(f, a, b) or int(f, x, a, b)
    # Mapping arguments can be tricky. 
    # MATLAB: int(expr, var, a, b) OR int(expr, a, b)
    
    # If 4 arguments: int(f, x, a, b)
    if b is not None: 
        limit_a = _to_sympy(a)
        limit_b = _to_sympy(b)
        return _wrap_sympy(sympy.integrate(f_val, (var_val, limit_a, limit_b)))
        
    # If 3 arguments: int(f, a, b) -> infer variable
    # Here, 'var' acts as 'a', and 'a' acts as 'b' from the signature above
    limit_a = var_val
    limit_b = _to_sympy(a)
    
    # Find free symbol
    free = list(f_val.free_symbols)
    if not free:
        raise ValueError("Cannot determine integration variable.")
    x = free[0]
    
    return _wrap_sympy(sympy.integrate(f_val, (x, limit_a, limit_b)))

def expand(expr):
    return _wrap_sympy(sympy.expand(_to_sympy(expr)))

def simplify(expr):
    return _wrap_sympy(sympy.simplify(_to_sympy(expr)))

def factor(expr):
    return _wrap_sympy(sympy.factor(_to_sympy(expr)))

def solve(eq, var=None):
    """
    solve(eq) -> solves eq = 0
    """
    eq_val = _to_sympy(eq)
    if var:
        return _wrap_sympy(sympy.solve(eq_val, _to_sympy(var)))
    return _wrap_sympy(sympy.solve(eq_val))

def subs(expr, old, new):
    """
    subs(expr, old, new)
    """
    expr_val = _to_sympy(expr)
    return _wrap_sympy(expr_val.subs(_to_sympy(old), _to_sympy(new)))

def limit(expr, var, target, dir='+'):
    """
    limit(expr, x, 0)
    """
    return _wrap_sympy(sympy.limit(_to_sympy(expr), _to_sympy(var), _to_sympy(target), dir=dir))