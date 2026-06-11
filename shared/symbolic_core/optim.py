# Mathex/mathex/math/optim.py
import numpy as np
import scipy.optimize
from .arrays import MatlabArray

def fminsearch(fun, x0, options=None):
    """
    x = fminsearch(fun, x0)
    Uses Nelder-Mead simplex algorithm.
    """
    x0 = np.asarray(x0).flatten()
    
    def wrapped_fun(x):
        res = fun(MatlabArray(x))
        return float(res)

    res = scipy.optimize.minimize(wrapped_fun, x0, method='Nelder-Mead')
    return MatlabArray(res.x)

def fzero(fun, x0):
    """
    x = fzero(fun, x0)
    Find root of single variable function.
    """
    def wrapped_fun(x):
        return float(fun(x))
    
    x0_val = float(x0)
    root = scipy.optimize.fsolve(wrapped_fun, x0_val)
    return MatlabArray(root)

def lsqcurvefit(fun, x0, xdata, ydata, lb=None, ub=None):
    """
    x = lsqcurvefit(fun, x0, xdata, ydata)
    """
    x0 = np.asarray(x0).flatten()
    xdata = np.asarray(xdata)
    ydata = np.asarray(ydata)

    def wrapped_fun(x, x_input):
        # fun(x, xdata) -> y_model
        # SciPy expects (f(xdata, *params))
        res = fun(MatlabArray(x), MatlabArray(x_input))
        return np.asarray(res).flatten()

    # Handle bounds
    if lb is None and ub is None:
        bounds = (-np.inf, np.inf)
    else:
        l = np.asarray(lb) if lb is not None else -np.inf
        u = np.asarray(ub) if ub is not None else np.inf
        bounds = (l, u)

    popt, _ = scipy.optimize.curve_fit(lambda xd, *p: wrapped_fun(p, xd), xdata, ydata, p0=x0, bounds=bounds)
    return MatlabArray(popt)

def fmincon(fun, x0, A=None, b=None, Aeq=None, beq=None, lb=None, ub=None, nonlcon=None):
    """
    x = fmincon(fun, x0, A, b, Aeq, beq, lb, ub, nonlcon)
    Constrained nonlinear minimization.
    """
    x0 = np.asarray(x0).flatten()
    
    def wrapped_fun(x):
        return float(fun(MatlabArray(x)))

    constraints = []
    
    # 1. Linear Inequality: A*x <= b
    # Check for None and also empty arrays (size > 0)
    if A is not None and b is not None:
        A_np = np.asarray(A)
        b_np = np.asarray(b)
        if A_np.size > 0 and b_np.size > 0:
            constraints.append(scipy.optimize.LinearConstraint(A_np, -np.inf, b_np))

    # 2. Linear Equality: Aeq*x == beq
    if Aeq is not None and beq is not None:
        Aeq_np = np.asarray(Aeq)
        beq_np = np.asarray(beq)
        if Aeq_np.size > 0 and beq_np.size > 0:
            constraints.append(scipy.optimize.LinearConstraint(Aeq_np, beq_np, beq_np))

    # 3. Nonlinear constraints (nonlcon)
    # MATLAB: [c, ceq] = nonlcon(x) where c(x) <= 0 and ceq(x) == 0
    if nonlcon is not None:
        # Wrapper to handle MatlabArray inputs/outputs
        def nlc_wrapper(x):
            # Returns tuple (c, ceq)
            res = nonlcon(MatlabArray(x))
            # If function returns multiple outputs, Python receives tuple
            if isinstance(res, (list, tuple)) and len(res) == 2:
                c, ceq = res
            else:
                c, ceq = res, None
            
            # Convert to numpy
            c_val = np.asarray(c._data).flatten() if isinstance(c, MatlabArray) else np.asarray(c).flatten()
            ceq_val = np.asarray(ceq._data).flatten() if isinstance(ceq, MatlabArray) and ceq is not None else (np.asarray(ceq).flatten() if ceq is not None else np.array([]))
            return c_val, ceq_val

        # SLSQP requires 'ineq' (c >= 0) and 'eq' (c == 0)
        # MATLAB c <= 0 implies -c >= 0
        constraints.append({
            'type': 'ineq', 
            'fun': lambda x: -1.0 * nlc_wrapper(x)[0]
        })
        constraints.append({
            'type': 'eq',
            'fun': lambda x: nlc_wrapper(x)[1]
        })

    # 4. Bounds
    # Fix: explicitly handle empty lists [] passed from MATLAB
    l = -np.inf
    u = np.inf
    
    has_bounds = False
    
    if lb is not None:
        lb_np = np.asarray(lb)
        if lb_np.size > 0:
            l = lb_np
            has_bounds = True
            
    if ub is not None:
        ub_np = np.asarray(ub)
        if ub_np.size > 0:
            u = ub_np
            has_bounds = True

    bounds = None
    if has_bounds:
        bounds = scipy.optimize.Bounds(l, u)

    res = scipy.optimize.minimize(
        wrapped_fun, x0, 
        method='SLSQP', # Good general purpose constrained solver
        bounds=bounds,
        constraints=constraints
    )
    return MatlabArray(res.x)

def linprog(f, A=None, b=None, Aeq=None, beq=None, lb=None, ub=None):
    """
    x = linprog(f, A, b, Aeq, beq, lb, ub)
    Minimizes f'*x subject to A*x <= b, Aeq*x = beq, lb <= x <= ub
    """
    c = np.asarray(f).flatten()
    
    # Handle empty inputs gracefully
    A_ub = np.asarray(A) if (A is not None and len(A) > 0) else None
    b_ub = np.asarray(b) if (b is not None and len(b) > 0) else None
    
    A_eq = np.asarray(Aeq) if (Aeq is not None and len(Aeq) > 0) else None
    b_eq = np.asarray(beq) if (beq is not None and len(beq) > 0) else None
    
    # Bounds logic
    bounds = None
    if lb is not None or ub is not None:
        # Convert to numpy and check for empty
        l_arr = np.asarray(lb).flatten() if lb is not None else np.array([])
        u_arr = np.asarray(ub).flatten() if ub is not None else np.array([])
        
        if l_arr.size > 0 or u_arr.size > 0:
            bounds = []
            for i in range(len(c)):
                lower = l_arr[i] if (l_arr.size > i) else None
                upper = u_arr[i] if (u_arr.size > i) else None
                bounds.append((lower, upper))
            
    res = scipy.optimize.linprog(
        c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs'
    )
    return MatlabArray(res.x)