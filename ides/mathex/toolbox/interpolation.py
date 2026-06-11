import numpy as np
import scipy.interpolate
from shared.symbolic_core.arrays import MatlabArray

def interp1(x, y, xi, method='linear', extrap=None):
    x_d = np.asarray(x).flatten()
    y_d = np.asarray(y)
    xi_d = np.asarray(xi)

    if y_d.ndim == 2 and (y_d.shape[0] == 1 or y_d.shape[1] == 1) and y_d.size == x_d.size:
        y_d = y_d.flatten()

    fill_value = "extrapolate" if extrap is None else extrap
    
    if method in ('spline', 'cubic', 'pchip'):
        cs = scipy.interpolate.CubicSpline(x_d, y_d, extrapolate=True if extrap is None else False)
        return MatlabArray(cs(xi_d))
    
    f = scipy.interpolate.interp1d(x_d, y_d, kind=method, fill_value=fill_value, bounds_error=False)
    return MatlabArray(f(xi_d))

def interp2(X, Y, Z, Xi, Yi, method='linear'):
    x_edge = np.asarray(X)[0, :]
    y_edge = np.asarray(Y)[:, 0]
    z_data = np.asarray(Z)
    
    interp = scipy.interpolate.RegularGridInterpolator(
        (y_edge, x_edge), z_data, method=method, bounds_error=False, fill_value=None
    )
    
    Xi_d = np.asarray(Xi)
    Yi_d = np.asarray(Yi)
    pts = np.stack((Yi_d.flatten(), Xi_d.flatten()), axis=-1)
    
    vals = interp(pts)
    return MatlabArray(vals.reshape(Xi_d.shape))

def griddata(x, y, v, xq, yq, method='linear'):
    points = np.stack((np.asarray(x).flatten(), np.asarray(y).flatten()), axis=-1)
    values = np.asarray(v).flatten()
    xi = (np.asarray(xq), np.asarray(yq))
    res = scipy.interpolate.griddata(points, values, xi, method=method)
    return MatlabArray(res)