import numpy as np
from shared.symbolic_core.arrays import MatlabArray

def roots(p):
    coeffs = p._data.flatten() if isinstance(p, MatlabArray) else np.array(p).flatten()
    return MatlabArray(np.roots(coeffs))

def polyval(p, x):
    coeffs = p._data.flatten() if isinstance(p, MatlabArray) else np.array(p).flatten()
    val_x = x._data if isinstance(x, MatlabArray) else x
    return MatlabArray(np.polyval(coeffs, val_x))