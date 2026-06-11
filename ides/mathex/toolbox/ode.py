import numpy as np
import scipy.integrate
from shared.symbolic_core.arrays import MatlabArray

# ==========================================================
# HELPER: ODE Solution Struct
# ==========================================================
class ODESolution:
    """Emulates a MATLAB struct for ODE results (sol.x, sol.y, sol.te, sol.ye, sol.ie)."""
    def __init__(self, t, y, te=None, ye=None, ie=None):
        self.x = MatlabArray(t)   # Independent var (Stored as Row Vector 1xN)
        self.y = MatlabArray(y)   # Solution (Stored as Vars x N)
        self.t = self.x 
        
        # Events support
        self.te = MatlabArray(te) if te is not None else MatlabArray([])
        self.ye = MatlabArray(ye) if ye is not None else MatlabArray([])
        self.ie = MatlabArray(ie) if ie is not None else MatlabArray([])
    
    def __repr__(self):
        base = f"<Structure with fields: x {self.x.shape}, y {self.y.shape}"
        if self.te.size > 0:
            base += f", te {self.te.shape}"
        return base + ">"
    
    def __iter__(self):
        # [FIX] Yield transposed versions to match MATLAB [t, y] = ode45(...) behavior
        # Struct stores x: (1,N), y: (Vars, N)
        # Unpacking expects t: (N,1), y: (N, Vars)
        yield self.x.T
        yield self.y.T

    def __getitem__(self, key):
        if isinstance(key, int):
            if key == 0: return self.x
            if key == 1: return self.y
            if key == 2: return self.te
            if key == 3: return self.ye
            if key == 4: return self.ie
            raise IndexError(f"ODESolution index {key} out of range")

        if key in ('x', 't'): return self.x
        if key == 'y': return self.y
        if key == 'te': return self.te
        if key == 'ye': return self.ye
        if key == 'ie': return self.ie
        raise KeyError(f"Field '{key}' not found in solution structure.")

def _wrap_ode_func(fun):
    """Wraps a Mathex function @(t,y) to work with SciPy."""
    def wrapper(t, y):
        y_col = y.reshape(-1, 1) 
        res = fun(t, MatlabArray(y_col))
        
        if isinstance(res, MatlabArray):
            return res._data.flatten()
            
        if isinstance(res, (list, tuple)):
            return np.array([float(x) for x in res])
            
        return np.asarray(res).flatten()
    return wrapper

def _solve_ivp_generic(fun, tspan, y0, method, events=None):
    if isinstance(tspan, MatlabArray):
        ts = tspan._data
    else:
        ts = np.array(tspan)
    ts = ts.flatten()
    t_start, t_end = float(ts[0]), float(ts[-1])

    t_eval = None
    if ts.size > 2:
        t_eval = ts

    if isinstance(y0, MatlabArray):
        y0_val = y0._data.flatten()
    else:
        y0_val = np.asarray(y0).flatten()
    
    sol = scipy.integrate.solve_ivp(
        _wrap_ode_func(fun), 
        (t_start, t_end), 
        y0_val, 
        method=method,
        events=events,
        t_eval=t_eval
    )
    
    te, ye, ie = None, None, None
    if sol.t_events is not None and len(sol.t_events) > 0:
        flat_te = []
        flat_ye = []
        flat_ie = []
        for i, (t_ev, y_ev) in enumerate(zip(sol.t_events, sol.y_events)):
            if t_ev.size > 0:
                flat_te.append(t_ev)
                flat_ye.append(y_ev)
                flat_ie.append(np.full(t_ev.shape, i+1))
        
        if flat_te:
            te = np.concatenate(flat_te)
            ye = np.concatenate(flat_ye)
            ie = np.concatenate(flat_ie)
            
            idx = np.argsort(te)
            te = te[idx]
            ye = ye[idx]
            ie = ie[idx]

    # [FIX] Reshape to match MATLAB Struct: x is row (1,N), y is (Vars,N)
    t_out = sol.t.reshape(1, -1)
    y_out = sol.y # solve_ivp returns (Vars, N) by default

    return ODESolution(t_out, y_out, te, ye, ie)

def ode45(fun, tspan, y0, events=None):
    return _solve_ivp_generic(fun, tspan, y0, method='RK45', events=events)

def ode23(fun, tspan, y0, events=None):
    return _solve_ivp_generic(fun, tspan, y0, method='RK23', events=events)

def ode15s(fun, tspan, y0, events=None):
    return _solve_ivp_generic(fun, tspan, y0, method='BDF', events=events)

def bvp4c(ode_fun, bc_fun, solinit):
    x_mesh = solinit.x._data if isinstance(solinit.x, MatlabArray) else solinit.x
    y_guess = solinit.y._data if isinstance(solinit.y, MatlabArray) else solinit.y
    
    def wrapped_ode(x, y):
        res = ode_fun(MatlabArray(x), MatlabArray(y))
        return res._data if isinstance(res, MatlabArray) else np.asarray(res)

    def wrapped_bc(ya, yb):
        res = bc_fun(MatlabArray(ya), MatlabArray(yb))
        return res._data.flatten() if isinstance(res, MatlabArray) else np.asarray(res).flatten()

    res = scipy.integrate.solve_bvp(wrapped_ode, wrapped_bc, x_mesh, y_guess)
    return ODESolution(res.x, res.y)