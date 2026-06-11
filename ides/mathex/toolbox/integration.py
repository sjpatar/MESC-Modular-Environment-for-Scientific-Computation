import numpy as np
import scipy.integrate
from shared.symbolic_core.arrays import MatlabArray

def trapz(y, x=None):
    y_data = y._data if isinstance(y, MatlabArray) else np.array(y)
    if x is None:
        return MatlabArray(scipy.integrate.trapezoid(y_data))
    x_data = x._data if isinstance(x, MatlabArray) else np.array(x)
    return MatlabArray(scipy.integrate.trapezoid(y_data, x_data))

def cumtrapz(y, x=None):
    y_data = y._data if isinstance(y, MatlabArray) else np.array(y)
    if x is None:
        res = scipy.integrate.cumulative_trapezoid(y_data, initial=0)
    else:
        x_data = x._data if isinstance(x, MatlabArray) else np.array(x)
        res = scipy.integrate.cumulative_trapezoid(y_data, x_data, initial=0)
    return MatlabArray(res)

def integral(fun, xmin, xmax):
    xmin = float(xmin._data) if isinstance(xmin, MatlabArray) else float(xmin)
    xmax = float(xmax._data) if isinstance(xmax, MatlabArray) else float(xmax)
    
    def wrapped(x):
        res = fun(x)
        return float(res._data) if isinstance(res, MatlabArray) else float(res)

    val, err = scipy.integrate.quad(wrapped, xmin, xmax)
    return MatlabArray(val)