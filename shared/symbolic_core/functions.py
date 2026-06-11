# mathex/math/functions.py
import numpy as np
import scipy.special
import sympy 
from .arrays import MatlabArray

def _unwrap(x):
    """Extract data from MatlabArray or return as-is."""
    return x._data if isinstance(x, MatlabArray) else x

def _is_symbolic(x):
    """Check if x is a SymPy object (symbol, expression) or contains them."""
    if isinstance(x, (sympy.Basic, sympy.Symbol)):
        return True
    if isinstance(x, np.ndarray) and x.dtype == object:
        return x.size > 0 and isinstance(x.flat[0], (sympy.Basic, sympy.Symbol))
    return False

# ===========================================================
# Trigonometry
# ===========================================================

def sin(x):
    val = _unwrap(x)
    if _is_symbolic(val): return sympy.sin(val)
    return MatlabArray(np.sin(val))

def cos(x):
    val = _unwrap(x)
    if _is_symbolic(val): return sympy.cos(val)
    return MatlabArray(np.cos(val))

def tan(x):
    val = _unwrap(x)
    if _is_symbolic(val): return sympy.tan(val)
    return MatlabArray(np.tan(val))

def asin(x):
    val = _unwrap(x)
    if _is_symbolic(val): return sympy.asin(val)
    return MatlabArray(np.arcsin(val))

def acos(x):
    val = _unwrap(x)
    if _is_symbolic(val): return sympy.acos(val)
    return MatlabArray(np.arccos(val))

def atan(x):
    val = _unwrap(x)
    if _is_symbolic(val): return sympy.atan(val)
    return MatlabArray(np.arctan(val))

def atan2(y, x):
    val_y, val_x = _unwrap(y), _unwrap(x)
    if _is_symbolic(val_y) or _is_symbolic(val_x):
        return sympy.atan2(val_y, val_x)
    return MatlabArray(np.arctan2(val_y, val_x))

def sinh(x):
    val = _unwrap(x)
    if _is_symbolic(val): return sympy.sinh(val)
    return MatlabArray(np.sinh(val))

def cosh(x):
    val = _unwrap(x)
    if _is_symbolic(val): return sympy.cosh(val)
    return MatlabArray(np.cosh(val))

def tanh(x):
    val = _unwrap(x)
    if _is_symbolic(val): return sympy.tanh(val)
    return MatlabArray(np.tanh(val))

def deg2rad(x):
    val = _unwrap(x)
    if _is_symbolic(val): return val * sympy.pi / 180
    return MatlabArray(np.deg2rad(val))

def rad2deg(x):
    val = _unwrap(x)
    if _is_symbolic(val): return val * 180 / sympy.pi
    return MatlabArray(np.rad2deg(val))

# ===========================================================
# Exponential / Log / Power
# ===========================================================

def exp(x):
    val = _unwrap(x)
    if _is_symbolic(val): return sympy.exp(val)
    return MatlabArray(np.exp(val))

def log(x):
    val = _unwrap(x)
    if _is_symbolic(val): return sympy.log(val)
    # [FIX] Automatic complex domain handling for log(-1)
    with np.errstate(divide='ignore', invalid='ignore'):
        res = np.lib.scimath.log(val)
    return MatlabArray(res)

def log10(x):
    val = _unwrap(x)
    if _is_symbolic(val): return sympy.log(val, 10)
    with np.errstate(divide='ignore', invalid='ignore'):
        res = np.lib.scimath.log10(val)
    return MatlabArray(res)

def sqrt(x):
    val = _unwrap(x)
    if _is_symbolic(val): return sympy.sqrt(val)
    # [FIX] Automatic complex domain handling for sqrt(-1)
    with np.errstate(invalid='ignore'):
        res = np.lib.scimath.sqrt(val)
    return MatlabArray(res)

def abs(x):
    val = _unwrap(x)
    if _is_symbolic(val): return sympy.Abs(val)
    return MatlabArray(np.abs(val))

def sign(x):
    val = _unwrap(x)
    if _is_symbolic(val): return sympy.sign(val)
    return MatlabArray(np.sign(val))

# ===========================================================
# Complex Numbers [NEW - FIXES THE CRASH]
# ===========================================================

def angle(x):
    """Phase angle of complex number."""
    val = _unwrap(x)
    if _is_symbolic(val): return sympy.arg(val)
    return MatlabArray(np.angle(val))

def real(x):
    """Real part of complex number."""
    val = _unwrap(x)
    if _is_symbolic(val): return sympy.re(val)
    return MatlabArray(np.real(val))

def imag(x):
    """Imaginary part of complex number."""
    val = _unwrap(x)
    if _is_symbolic(val): return sympy.im(val)
    return MatlabArray(np.imag(val))

def conj(x):
    """Complex conjugate."""
    val = _unwrap(x)
    if _is_symbolic(val): return sympy.conjugate(val)
    return MatlabArray(np.conjugate(val))

# ===========================================================
# Matrix / Vector Ops
# ===========================================================
def diag(v, k=0):
    val = _unwrap(v)
    k_val = int(_unwrap(k))
    if _is_symbolic(val): pass 
    
    if hasattr(val, 'ndim') and val.ndim == 2 and (val.shape[0] == 1 or val.shape[1] == 1) and val.size > 0:
        val = val.flatten()
        return MatlabArray(np.diag(val, k_val))
    
    if hasattr(val, 'ndim') and val.ndim == 0:
        return MatlabArray(np.diag([val], k_val))
        
    try:
        res = np.diag(val, k_val)
        return MatlabArray(res.reshape(-1, 1))
    except Exception:
        val = np.array(val)
        return MatlabArray(np.diag(val, k_val))

# ===========================================================
# Rounding
# ===========================================================
def floor(x):
    val = _unwrap(x)
    if _is_symbolic(val): return sympy.floor(val)
    return MatlabArray(np.floor(val))

def ceil(x):
    val = _unwrap(x)
    if _is_symbolic(val): return sympy.ceiling(val)
    return MatlabArray(np.ceil(val))

def round(x):
    val = _unwrap(x)
    if _is_symbolic(val): return round(val) 
    return MatlabArray(np.round(val))

def fix(x):
    val = _unwrap(x)
    if _is_symbolic(val): return sympy.integer_nthroot(val, 1)[0]
    return MatlabArray(np.fix(val))

def rem(x, y):
    val_x, val_y = _unwrap(x), _unwrap(y)
    if _is_symbolic(val_x) or _is_symbolic(val_y): return val_x % val_y
    return MatlabArray(np.remainder(val_x, val_y))

def mod(x, y):
    val_x, val_y = _unwrap(x), _unwrap(y)
    if _is_symbolic(val_x) or _is_symbolic(val_y): return val_x % val_y
    return MatlabArray(np.mod(val_x, val_y))

# ===========================================================
# SPECIAL FUNCTIONS
# ===========================================================
def besselj(nu, z):
    val_nu, val_z = _unwrap(nu), _unwrap(z)
    if _is_symbolic(val_z): return sympy.besselj(val_nu, val_z)
    return MatlabArray(scipy.special.jv(val_nu, val_z))

def bessely(nu, z):
    val_nu, val_z = _unwrap(nu), _unwrap(z)
    if _is_symbolic(val_z): return sympy.bessely(val_nu, val_z)
    return MatlabArray(scipy.special.yv(val_nu, val_z))

def gamma(x):
    val = _unwrap(x)
    if _is_symbolic(val): return sympy.gamma(val)
    return MatlabArray(scipy.special.gamma(val))

def gammaln(x):
    val = _unwrap(x)
    if _is_symbolic(val): return sympy.loggamma(val)
    return MatlabArray(scipy.special.gammaln(val))

def erf(x):
    val = _unwrap(x)
    if _is_symbolic(val): return sympy.erf(val)
    return MatlabArray(scipy.special.erf(val))

def erfc(x):
    val = _unwrap(x)
    if _is_symbolic(val): return sympy.erfc(val)
    return MatlabArray(scipy.special.erfc(val))

def legendre(n, x):
    val_n, val_x = int(_unwrap(n)), _unwrap(x)
    if _is_symbolic(val_x): return sympy.legendre(val_n, val_x)
    P = scipy.special.legendre(val_n)
    return MatlabArray(P(val_x))