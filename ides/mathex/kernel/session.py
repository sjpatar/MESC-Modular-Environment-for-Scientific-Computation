import time
import os
import traceback
import threading
import numpy as np
from ides.mathex.language import builtins
from ides.mathex.kernel.path_manager import path_manager
from ides.mathex.kernel.loader import load_and_register
from ides.mathex.kernel.security import build_execution_builtins, env_safe_mode_enabled
from ides.mathex.language.functions import registry
from ides.mathex.language.locale import tr

# Explicitly import constants to ensure they exist in session
from shared.symbolic_core.physics import (
    physconst, constants_struct, PhysicalConstants,
    convtemp, convlength, convmass, convforce, convpres, convenergy,
    c, G, h, k, g  
)
try:
    from PySide6.QtWidgets import QApplication
except Exception:
    QApplication = None

# ------------------------------------------------------------
# Core Math Engine
# ------------------------------------------------------------
from shared.symbolic_core import functions as _mlfun
from shared.symbolic_core.arrays import (
    MatlabArray, mat, zeros, ones, eye, linspace, arange,
    sparse, full, colon, cell, _shape
)

# ------------------------------------------------------------
# Linear Algebra
# ------------------------------------------------------------
from shared.symbolic_core.linalg import (
    inv, det, eig, rank, norm, lu,
    svd, qr, pinv, null, orth,
    expm, sqrtm, hess, schur, chol,
    gmres, pcg, cond, eigs
)

# ------------------------------------------------------------
# Statistics & Calculus
# ------------------------------------------------------------
from shared.symbolic_core.statistics import (
    mean, std, max_func, min_func, sum_func,
    corrcoef, cov, histcounts, nlinfit
)

# ------------------------------------------------------------
# Optimization
# ------------------------------------------------------------
try:
    from shared.symbolic_core.optim import (
        fminsearch, fzero, lsqcurvefit,
        fmincon, linprog
    )
except ImportError:
    fminsearch = fzero = lsqcurvefit = fmincon = linprog = None

# ------------------------------------------------------------
# Advanced Toolbox
# ------------------------------------------------------------
from ides.mathex.toolbox import (
    meshgrid, sphere, cylinder,
    gradient, cross, dot,
    ode45, ode23, ode15s, bvp4c,
    fft, ifft,
    roots, polyval, trapz, cumtrapz, integral,
    interp1, interp2, griddata,
    fftshift, ifftshift, spectrogram,
    pdepe,
    fft2, ifft2, filter
)

# Image Processing Toolbox (Robust Import)
try:
    import ides.mathex.toolbox.images as images
except ImportError:
    images = None

# ------------------------------------------------------------
# Plotting
# ------------------------------------------------------------
import shared.plotting_engine as _plt_mod
from shared.plotting_engine.state import plot_manager
from shared.plotting_engine.engine import PlotEngine

# ------------------------------------------------------------
# I/O & Structs
# ------------------------------------------------------------
from ides.mathex.io import (
    save_workspace, load_workspace, writematrix, saveas,
    readtable, readmatrix, csvread
)
from shared.symbolic_core.structs import MatlabStruct

# ------------------------------------------------------------
# Symbolic Math
# ------------------------------------------------------------
from shared.symbolic_core.symbolic import (
    syms, diff, int_func, expand, simplify, factor, solve, subs, limit
)

# ============================================================
# Helpers & Commands
# ============================================================

def rand(*args):
    shape = _shape(args)
    return MatlabArray(np.random.rand(*shape))

def randn(*args):
    shape = _shape(args)
    return MatlabArray(np.random.randn(*shape))

_tic_timer = 0.0

def tic():
    global _tic_timer
    _tic_timer = time.time()

def toc():
    global _tic_timer
    val = time.time() - _tic_timer
    print(f"Elapsed time is {val:.6f} seconds.")
    return val

def addpath(p):
    path_manager.add_path(p)

def rmpath(p):
    path_manager.remove_path(p)

def cd(p=None):
    if p is None:
        print(os.getcwd())
        return
    try:
        os.chdir(str(p))
        print(os.getcwd())
    except Exception as e:
        print(f"Error: {str(e)}")

def pwd():
    cwd = os.getcwd()
    print(cwd)
    return cwd

def ls(p='.'):
    try:
        items = os.listdir(str(p))
        print("\n".join(sorted(items)))
    except Exception as e:
        print(str(e))

cd.__mathex_command__ = True
pwd.__mathex_command__ = True
ls.__mathex_command__ = True

# ============================================================
# Kernel Session
# ============================================================

class KernelSession:
    """
    MATLAB-style execution kernel.
    """

    def __init__(self, safe_mode=None):
        self.safe_mode = env_safe_mode_enabled() if safe_mode is None else bool(safe_mode)
        self.execution_builtins = build_execution_builtins(self.safe_mode)
        self.globals = {}
        self._builtins_set = set() 
        self.reset()

    def reset(self):
        self.globals = {"__builtins__": self.execution_builtins, "__name__": "__main__"}
        

        if getattr(plot_manager, "widget", None):
            try:
                plot_manager.set_widget(plot_manager.widget)
            except Exception:
                pass

        # Constants
        self.globals.update({
            "pi": np.pi,
            "e": np.e,
            "i": 1j,
            "j": 1j,
            "nan": np.nan,
            "inf": np.inf,
            "ans": 0,
        })

        # Arrays
        self.globals.update({
            "MatlabArray": MatlabArray,
            "mat": mat,
            "zeros": zeros,
            "ones": ones,
            "eye": eye,
            "linspace": linspace,
            "arange": arange,
            "rand": rand,
            "randn": randn,
            "sparse": sparse,
            "full": full,
            "colon": colon,
            "cell": cell,
        })

        # Helpers
        self.globals.update({
            "size": builtins.size,
            "length": builtins.length,
            "numel": builtins.numel,
            "tic": tic,
            "toc": toc,
            "struct": builtins.struct,
            "MatlabStruct": MatlabStruct,
            "deal": builtins.deal,
            "num2str": builtins.num2str,
            "sprintf": builtins.sprintf, 
            
            # [LOCALE FIX] Assamese Aliases for Array/Data details
            "আকাৰ": builtins.size,
            "দৈৰ্ঘ্য": builtins.length,
        })

        # Path & File System
        self.globals.update({
            "addpath": self._restrict_io("addpath", addpath),
            "rmpath": self._restrict_io("rmpath", rmpath),
            "cd": self._restrict_io("cd", cd),
            "pwd": self._restrict_io("pwd", pwd),
            "ls": self._restrict_io("ls", ls),
            "dir": self._restrict_io("dir", ls),
        })

        # Linear Algebra
        self.globals.update({
            "inv": inv, "det": det, "eig": eig, "rank": rank, "norm": norm,
            "lu": lu, "svd": svd, "qr": qr, "pinv": pinv, "null": null, "orth": orth,
            "expm": expm, "sqrtm": sqrtm, "hess": hess, "schur": schur, "chol": chol,
            "gmres": gmres, "pcg": pcg, "cond": cond, 
            "eigs": eigs,
        })

        # Statistics
        self.globals.update({
            "mean": mean, "std": std, "max": max_func, "min": min_func, "sum": sum_func,
            "corrcoef": corrcoef, "cov": cov, "histcounts": histcounts, 
            "nlinfit": nlinfit,
        })

        # Symbolic & Calculus
        self.globals.update({
            "syms": syms,
            "diff": diff,
            "int": int_func,
            "expand": expand,
            "simplify": simplify,
            "factor": factor,
            "solve": solve,
            "subs": subs,
            "limit": limit,
        })
        
        # Physics Constants & Converters
        hbar_val = getattr(constants_struct, 'hbar', None)
        if hbar_val is None:
             hbar_val = constants_struct.h / (2 * np.pi)

        self.globals.update({
            "physconst": physconst,
            "PhysicalConstants": constants_struct,
            "c": c,       
            "G": G,       
            "h": h,       
            "hbar": hbar_val,
            "k": k,       
            "g": g,       
            "convtemp": convtemp,
            "convlength": convlength,
            "convmass": convmass,
            "convforce": convforce,
            "convpres": convpres,
            "convenergy": convenergy,
        })

        # Optimization
        if fminsearch:
            self.globals.update({
                "fminsearch": fminsearch,
                "fzero": fzero,
                "lsqcurvefit": lsqcurvefit,
                "fmincon": fmincon,
                "linprog": linprog,
            })

        # Toolbox
        self.globals.update({
            "meshgrid": meshgrid, "sphere": sphere, "cylinder": cylinder,
            "gradient": gradient, "cross": cross, "dot": dot,
            "ode45": ode45, "ode23": ode23, "ode15s": ode15s, "bvp4c": bvp4c,
            "fft": fft, "ifft": ifft, "roots": roots, "polyval": polyval,
            "trapz": trapz, "cumtrapz": cumtrapz, "integral": integral,
            "interp1": interp1, "interp2": interp2, "griddata": griddata,
            "fftshift": fftshift, "ifftshift": ifftshift, "spectrogram": spectrogram,
            "pdepe": pdepe,
            "fft2": fft2,
            "ifft2": ifft2,
            "filter": filter,
        })

        if images:
            self.globals.update({
                "imread": images.imread,
                "imshow": images.imshow,
                "rgb2gray": images.rgb2gray,
                "imresize": images.imresize,
                "imfilter": images.imfilter, 
            })

        self.globals.update({
            "sin": _mlfun.sin, "cos": _mlfun.cos, "tan": _mlfun.tan,
            "asin": _mlfun.asin, "acos": _mlfun.acos, "atan": _mlfun.atan, "atan2": _mlfun.atan2,
            "sinh": _mlfun.sinh, "cosh": _mlfun.cosh, "tanh": _mlfun.tanh,
            "exp": _mlfun.exp, "log": _mlfun.log, "log10": _mlfun.log10, "sqrt": _mlfun.sqrt,
            "abs": _mlfun.abs, "sign": _mlfun.sign,
            "floor": _mlfun.floor, "ceil": _mlfun.ceil, "round": _mlfun.round, "fix": _mlfun.fix,
            "mod": _mlfun.mod, "rem": _mlfun.rem,
            
            "angle": _mlfun.angle,
            "real": _mlfun.real,
            "imag": _mlfun.imag,
            "conj": _mlfun.conj,
            "diag": _mlfun.diag,
        })

        try:
            for name in dir(_mlfun):
                if not name.startswith("_") and name not in self.globals and name not in ("MatlabArray", "scipy", "np", "sympy"):
                    self.globals[name] = getattr(_mlfun, name)
        except Exception:
            pass

        for name in dir(_plt_mod):
            if not name.startswith("_"):
                try:
                    self.globals[name] = getattr(_plt_mod, name)
                except Exception:
                    pass

        self.globals.update({
            "clf": lambda: plot_manager.clf(),
            "cla": self._cla,
            "hold": lambda mode=True: plot_manager.hold(mode),
        })

        # I/O & Core Built-ins
        self.globals.update({
            "save": self._restrict_io("save", lambda f="workspace.mat": save_workspace(self, f)),
            "load": self._restrict_io("load", lambda f="workspace.mat": load_workspace(self, f)),
            "writematrix": self._restrict_io("writematrix", writematrix),
            "readmatrix": self._restrict_io("readmatrix", readmatrix),
            "readtable": self._restrict_io("readtable", readtable),
            "csvread": self._restrict_io("csvread", csvread),
            "saveas": self._restrict_io("saveas", saveas),
            "disp": builtins.disp,
            "clear": self._clear_user,
            "clc": builtins.clc,
            "pause": time.sleep,
            "who": lambda: builtins.who(self.globals),
            "whos": lambda: builtins.whos(self.globals),
            "exist": lambda n, k=None: builtins.exist(n, k, self.globals),
            
            # --- NEW: Inject Custom Help ---
            "help": builtins.mathex_help,
            "সহায়": builtins.mathex_help,
            
            # [LOCALE FIX] Plotting & UI Actions Exposed to Kernel Environment
            "দেখুওৱা": builtins.disp,
            "মচিদিয়া": builtins.clc,
            "ৰৈযোৱা": getattr(builtins, "pause", time.sleep),
            "আকা": getattr(_plt_mod, "plot", None), 
            "শিৰোনামা": getattr(_plt_mod, "title", None),
            "xলেবেল": getattr(_plt_mod, "xlabel", None),
            "yলেবেল": getattr(_plt_mod, "ylabel", None),
            "সংকেত": getattr(_plt_mod, "legend", None),
            "গ্ৰিড": getattr(plot_manager, "grid", None),
        })
        
        # Control Toolbox
        try:
            from ides.mathex.toolbox.control import (
                tf, step, impulse, bode, series, parallel, feedback,
                rlocus 
            )
            self.globals.update({
                "tf": tf, "step": step, "impulse": impulse,
                "bode": bode, "series": series, "parallel": parallel,
                "feedback": feedback, "rlocus": rlocus,
            })
        except ImportError:
            pass
        
        self._builtins_set = set(self.globals.keys())

    def _restrict_io(self, name, func):
        if not self.safe_mode:
            return func

        def blocked(*args, **kwargs):
            raise PermissionError(
                f"{name} is disabled in MESC safe mode for web-facing deployments."
            )

        blocked.__name__ = getattr(func, "__name__", name)
        return blocked

    def execute(self, code: str, breakpoints: list = None):
        from ides.mathex.kernel.executor import execute as _exec
        try:
            _exec(code, self, breakpoints=breakpoints)
        except Exception as e:
            self._handle_runtime_error(e)
        finally:
            self._after_execute()

    def _handle_runtime_error(self, e: Exception):
        """Intercepts raw Python/NumPy errors and translates them."""
        err_msg = str(e).lower()
        
        if "shapes not aligned" in err_msg or "mismatch" in err_msg or "broadcast" in err_msg:
            print(tr("err_dim_mismatch"))
        elif "division by zero" in err_msg:
            print(tr("err_div_zero"))
        elif "not defined" in err_msg or "name" in err_msg:
            name = "unknown"
            if "'" in str(e):
                name = str(e).split("'")[1]
            print(tr("err_undefined", name=name))
        else:
            print(tr("err_generic", msg=str(e)))

    def _after_execute(self):
        try:
            # Qt event pumping must stay on the UI thread. Calling it from the
            # kernel worker can terminate the whole app during plotting/text render.
            if QApplication and threading.current_thread() is threading.main_thread():
                QApplication.processEvents()
        except Exception:
            pass

    def _drawnow(self):
        self._after_execute()

    def _cla(self):
        ax = plot_manager.gca()
        if ax:
            ax.clear()

    def _clear_user(self, *args):
        should_clear_all = False
        vars_to_clear = []

        if not args:
            should_clear_all = True
        else:
            for a in args:
                s = str(a)
                if s == 'all':
                    should_clear_all = True
                    break
                if s not in ('classes', 'functions', 'import'):
                    vars_to_clear.append(s)

        if should_clear_all:
            for k in list(self.globals.keys()):
                if k in self._builtins_set:
                    continue
                if k == "ans": 
                    self.globals[k] = 0
                    continue
                try:
                    del self.globals[k]
                except Exception:
                    pass
            return

        for name in vars_to_clear:
             if name in self.globals and name not in self._builtins_set:
                 try: del self.globals[name]
                 except: pass
