import ast
import traceback
import sys
import threading
import builtins 

from ides.mathex.language.transpiler import transpile
from ides.mathex.kernel.session import KernelSession
from ides.mathex.kernel.loader import load_and_register
from ides.mathex.kernel.security import validate_user_ast
from ides.mathex.language.functions import registry
from ides.mathex.language.locale import tr

# ==========================================================
# DEBUGGER ARCHITECTURE
# ==========================================================
class DebugContext:
    def __init__(self, line_map, breakpoints):
        self.line_map = line_map          
        self.breakpoints = set(breakpoints) 
        self.paused = False
        self.condition = threading.Condition()
        self.current_locals = {}
        self.command = "continue" 
        self.current_ml_line = -1

    def wait_for_user(self):
        with self.condition:
            self.paused = True
            print(f"__DEBUG_PAUSED__:{self.current_ml_line}") 
            self.condition.wait()
            self.paused = False
            return self.command

    def resume(self, cmd="continue"):
        with self.condition:
            self.command = cmd
            self.condition.notify()

def _create_trace_func(debug_ctx: DebugContext):
    def trace_dispatch(frame, event, arg):
        if event != 'line':
            return trace_dispatch

        py_line = frame.f_lineno
        ml_line = debug_ctx.line_map.get(py_line)
        
        if ml_line is not None:
            debug_ctx.current_ml_line = ml_line
            should_stop = (ml_line in debug_ctx.breakpoints) or (debug_ctx.command == 'step')

            if should_stop:
                debug_ctx.current_locals = frame.f_locals.copy()
                if debug_ctx.command == 'step':
                    debug_ctx.command = 'continue' 
                
                cmd = debug_ctx.wait_for_user()
                if cmd == 'quit':
                    sys.exit(0)
                    
        return trace_dispatch
    return trace_dispatch

# ==========================================================
# CORE POLYFILLS (MATLAB -> PYTHON BRIDGE)
# ==========================================================
def _inject_matlab_polyfills():
    """
    Injects missing MATLAB constants and synchronizes 3D Plotly labels.
    By binding to `builtins`, these survive the user's `clear;` command!
    """
    import numpy as np
    import shared.plotting_engine as _plt_mod
    from shared.plotting_engine.state import plot_manager
    
    # 1. Constants & Core Builtins (Indestructible by 'clear')
    builtins.eps = np.finfo(float).eps
    builtins.pi = np.pi
    builtins.inf = np.inf
    builtins.NaN = np.nan
    builtins.nan = np.nan
    
    def _sprintf(fmt, *args):
        fmt = str(fmt).replace('%f', '%g') # Map MATLAB floats to Python %g
        try: return fmt % args if args else fmt
        except: return fmt
        
    builtins.sprintf = _sprintf
    builtins.disp = print
    builtins.numel = np.size

    # 2. Robust Plotting Bridge
    def _sync_plotly(key, val, is_3d=False):
        """Hunts for the active Plotly figure and safely applies the layout update."""
        try:
            fig = None
            for attr in ['active_figure', 'current_fig', 'fig', 'figure']:
                if hasattr(plot_manager, attr):
                    obj = getattr(plot_manager, attr)
                    if hasattr(obj, 'update_layout'):
                        fig = obj
                        break
            if fig:
                if is_3d: fig.update_layout(scene={key: str(val)})
                else: fig.update_layout({key: str(val)})
        except: pass

    def _title(label, *args, **kwargs):
        import matplotlib.pyplot as plt
        plt.title(label, *args, **kwargs)
        _sync_plotly('title', label)

    def _xlabel(label, *args, **kwargs):
        import matplotlib.pyplot as plt
        plt.xlabel(label, *args, **kwargs)
        _sync_plotly('xaxis_title', label, is_3d=True)

    def _ylabel(label, *args, **kwargs):
        import matplotlib.pyplot as plt
        plt.ylabel(label, *args, **kwargs)
        _sync_plotly('yaxis_title', label, is_3d=True)

    def _zlabel(label, *args, **kwargs):
        import matplotlib.pyplot as plt
        try: plt.gca().set_zlabel(label, *args, **kwargs)
        except: pass
        _sync_plotly('zaxis_title', label, is_3d=True)

    def _shading(*args): pass # Ignored in Python (Plotly handles this natively)
    def _colormap(*args):
        import matplotlib.pyplot as plt
        try: plt.set_cmap(args[0])
        except: pass

    # Bind plotting handlers to builtins
    builtins.title = _title
    builtins.xlabel = _xlabel
    builtins.ylabel = _ylabel
    builtins.zlabel = _zlabel
    builtins.shading = _shading
    builtins.colormap = _colormap
    builtins.brush = getattr(_plt_mod, "brush", lambda *args, **kwargs: None)

# -----------------------------------------------------------
# MAIN EXECUTOR 
# -----------------------------------------------------------
def execute(code: str, session: KernelSession, breakpoints: list = None):
    code = code.strip()
    if not code: return None

    suppress = code.endswith(";")
    if suppress: code = code[:-1].strip()

    tracer = None
    old_trace = sys.gettrace()

    try:
        py, line_map = transpile(code)
        
        if breakpoints:
            ctx = DebugContext(line_map, breakpoints)
            session.debug_context = ctx 
            tracer = _create_trace_func(ctx)
            sys.settrace(tracer)

        tree = ast.parse(py, mode="exec")
        if session.safe_mode:
            validate_user_ast(tree)

        # --- INJECT POLYFILLS HERE ---
        _inject_matlab_polyfills()

        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                var_name = node.id
                if var_name not in session.globals and var_name not in builtins.__dict__:
                    if load_and_register(
                        var_name,
                        builtins_scope=session.execution_builtins,
                        safe_mode=session.safe_mode,
                    ):
                        entry = registry.get(var_name)
                        if entry:
                            session.globals[var_name] = entry.func

        if tree.body and isinstance(tree.body[0], ast.FunctionDef):
            exec(py, session.globals)
            return None

        if tree.body and isinstance(tree.body[-1], ast.Expr):
            last = tree.body[-1]
            body = tree.body[:-1]

            if body:
                exec(compile(ast.Module(body=body, type_ignores=[]), "<ml>", "exec"), session.globals)

            value = eval(compile(ast.Expression(last.value), "<ml>", "eval"), session.globals)

            is_cmd = getattr(value, "__mathex_command__", False)
            if not is_cmd and callable(value) and isinstance(last.value, ast.Name):
                is_cmd = True

            if callable(value) and is_cmd:
                try:
                    if getattr(value, "__mathex_script__", False):
                        value(session.globals)
                    else:
                        try:
                            value()
                        except TypeError as e:
                            msg = str(e)
                            if "required" in msg or "missing" in msg or "argument" in msg:
                                print(f"{tr('err_prefix')}: {tr('err_not_enough_args')}")
                                return None
                            raise e
                    return None
                except Exception as e:
                    raise e

            if hasattr(value, "__class__") and value.__class__.__name__.endswith("Handle"):
                session.globals["ans"] = value
                return None

            if value is not None:
                session.globals["ans"] = value
                if not suppress:
                    if isinstance(value, bool):
                        print(f"ans =\n\n  logical\n\n     {1 if value else 0}")
                    elif isinstance(value, list):
                        from shared.symbolic_core.arrays import MatlabArray
                        print(f"ans =\n\n{MatlabArray(value)}")
                    elif hasattr(value, "_data"):
                        print(f"ans =\n\n{value}")
                    else:
                        print(f"ans =\n\n     {value}")
            return None

        exec(py, session.globals)

        if not suppress and len(tree.body) == 1 and isinstance(tree.body[0], ast.Assign):
            target = tree.body[0].targets[0]
            if isinstance(target, ast.Name):
                name = target.id
                val = session.globals.get(name)
                if isinstance(val, bool):
                    print(f"{name} =\n\n  logical\n\n     {1 if val else 0}")
                elif isinstance(val, list):
                    from shared.symbolic_core.arrays import MatlabArray
                    print(f"{name} =\n\n{MatlabArray(val)}")
                elif hasattr(val, "_data"):
                    print(f"{name} =\n\n{val}")
                else:
                    print(f"{name} =\n\n     {val}")

    except Exception as e:
        if tracer: sys.settrace(old_trace)
        traceback.print_exc(file=sys.stderr)
        l_map = locals().get('line_map', {})
        _handle_matlab_error(e, code, l_map)
        return e 
    
    finally:
        if 'tracer' in locals() and tracer:
            sys.settrace(old_trace)
            session.debug_context = None 
    
    return None

def _handle_matlab_error(e, code, line_map=None):
    if line_map is None: line_map = {}
    _, _, tb = sys.exc_info()
    py_line = -1
    
    if isinstance(e, SyntaxError) and e.lineno is not None:
        py_line = e.lineno
    else:
        for frame in traceback.extract_tb(tb):
            if frame.filename in ("<ml>", "<string>"):
                py_line = frame.lineno
    
    matlab_line_str = ""
    if py_line > 0:
        m_line = line_map.get(py_line, "?")
        if m_line != "?":
            matlab_line_str = f" ({tr('err_line_label')} {m_line})"

    msg = str(e).lower()
    exc_type = type(e).__name__
    prefix = f"{tr('err_prefix')}{matlab_line_str}:"

    if "SyntaxError" in exc_type:
        print(f"{prefix} {tr('err_invalid_syntax_near', code=code.strip())}")
        return
    if isinstance(e, NameError):
        try:
            var_name = str(e).split("'")[1]
            print(f"{prefix} {tr('err_undefined', name=var_name)}")
        except IndexError:
            print(f"{prefix} {tr('err_undefined', name='unknown')}")
        return
    if isinstance(e, IndexError):
        print(f"{prefix} {tr('err_index_bounds')}")
        return
    if isinstance(e, ValueError):
        if "broadcast" in msg or "shape" in msg or "mismatch" in msg:
            print(f"{prefix} {tr('err_dim_mismatch')}")
            return
    if isinstance(e, ZeroDivisionError) or "division by zero" in msg:
        print(f"{prefix} {tr('err_div_zero')}")
        return
    print(f"{prefix} {tr('err_generic', msg=str(e))}")
