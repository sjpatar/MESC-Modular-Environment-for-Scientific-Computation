# Mathex/mathex/math/statistics.py
import numpy as np
import scipy.stats
import scipy.optimize
from .arrays import MatlabArray

# ==========================================================
# BASIC STATISTICS
# ==========================================================

def mean(x, dim=None):
    """
    Mean value.
    mean(x) or mean(x, dim)
    """
    d = x._data if isinstance(x, MatlabArray) else x
    
    # MATLAB behavior: if dim not specified, work along first non-singleton dimension
    # For vectors (1xN or Nx1), it just takes the mean.
    if dim is None:
        if d.ndim == 2 and (d.shape[0] == 1 or d.shape[1] == 1):
             return MatlabArray(np.mean(d))
        axis = 0
    else:
        axis = int(dim) - 1
        
    return MatlabArray(np.mean(d, axis=axis))

def std(x, w=0, dim=None):
    """
    Standard deviation.
    std(x) -> Normalized by N-1 (w=0)
    std(x, 1) -> Normalized by N (w=1)
    """
    d = x._data if isinstance(x, MatlabArray) else x
    
    if dim is None:
        if d.ndim == 2 and (d.shape[0] == 1 or d.shape[1] == 1):
             ddof = 1 if w==0 else 0
             return MatlabArray(np.std(d, ddof=ddof))
        axis = 0
    else:
        axis = int(dim) - 1
        
    ddof = 1 if w==0 else 0
    return MatlabArray(np.std(d, axis=axis, ddof=ddof))

def min_func(a):
    """
    Minimum elements.
    min(x)
    """
    # Note: MATLAB min(A) returns row vector of mins for matrices
    d = a._data if isinstance(a, MatlabArray) else a
    if d.ndim == 2 and (d.shape[0] == 1 or d.shape[1] == 1):
        return MatlabArray(np.min(d))
    return MatlabArray(np.min(d, axis=0))

def max_func(a):
    """
    Maximum elements.
    max(x)
    """
    d = a._data if isinstance(a, MatlabArray) else a
    if d.ndim == 2 and (d.shape[0] == 1 or d.shape[1] == 1):
        return MatlabArray(np.max(d))
    return MatlabArray(np.max(d, axis=0))

def sum_func(a):
    """
    Sum of elements.
    sum(x)
    """
    d = a._data if isinstance(a, MatlabArray) else a
    if d.ndim == 2 and (d.shape[0] == 1 or d.shape[1] == 1):
        return MatlabArray(np.sum(d))
    return MatlabArray(np.sum(d, axis=0))

# ==========================================================
# ADVANCED STATISTICS (PHD FEATURES)
# ==========================================================

def corrcoef(*args):
    """
    Correlation coefficients.
    R = corrcoef(A)
    R = corrcoef(x, y)
    """
    arrays = []
    for a in args:
        if isinstance(a, MatlabArray):
            arrays.append(a._data)
        else:
            arrays.append(np.asarray(a))

    if len(arrays) == 1:
        # If matrix, MATLAB treats columns as variables
        mat = arrays[0]
        if mat.ndim == 2:
            return MatlabArray(np.corrcoef(mat, rowvar=False))
        return MatlabArray(1.0) # Scalar case
        
    # Two inputs: corrcoef(x, y)
    x = arrays[0].flatten()
    y = arrays[1].flatten()
    return MatlabArray(np.corrcoef(x, y))

def cov(x, y=None):
    """
    Covariance matrix.
    cov(x)
    cov(x, y)
    """
    x_data = x._data if isinstance(x, MatlabArray) else np.asarray(x)
    
    if y is None:
        # If matrix, MATLAB treats columns as variables
        if x_data.ndim == 2 and x_data.shape[0] > 1 and x_data.shape[1] > 1:
            return MatlabArray(np.cov(x_data, rowvar=False))
        # Vector case
        return MatlabArray(np.cov(x_data.flatten()))
    
    y_data = y._data if isinstance(y, MatlabArray) else np.asarray(y)
    return MatlabArray(np.cov(x_data.flatten(), y_data.flatten()))

def histcounts(x, bins=10):
    """
    Histogram bin counts.
    [N, edges] = histcounts(x, bins)
    """
    x_data = x._data.flatten() if isinstance(x, MatlabArray) else np.asarray(x).flatten()
    
    # MATLAB 'bins' can be a scalar number of bins or edge vector
    # SciPy/Numpy handles scalar int or array_like edges
    b = int(bins) if isinstance(bins, (int, float)) else np.asarray(bins)
    
    count, edges = np.histogram(x_data, bins=b)
    return MatlabArray(count), MatlabArray(edges)

def nlinfit(X, y, modelfun, beta0):
    """
    Non-linear regression.
    beta = nlinfit(X, y, modelfun, beta0)
    """
    X_data = X._data if isinstance(X, MatlabArray) else np.asarray(X)
    y_data = y._data.flatten() if isinstance(y, MatlabArray) else np.asarray(y).flatten()
    b0 = beta0._data.flatten() if isinstance(beta0, MatlabArray) else np.asarray(beta0).flatten()
    
    # modelfun in MATLAB: y = f(b, X)
    # curve_fit expects: y = f(X, *b)
    
    def wrapped(x_input, *params):
        # Convert params back to MatlabArray for the user function
        p_arr = MatlabArray(list(params))
        # Call model: f(beta, X)
        res = modelfun(p_arr, MatlabArray(x_input))
        
        if isinstance(res, MatlabArray):
            return res._data.flatten()
        return np.asarray(res).flatten()
    
    try:
        popt, pcov = scipy.optimize.curve_fit(wrapped, X_data, y_data, p0=b0)
        return MatlabArray(popt)
    except Exception as e:
        print(f"nlinfit warning: {e}")
        return MatlabArray(b0) # Return guess on failure