import types
import json
import os
import base64
import tempfile
import re

# We keep this global as it is lightweight
from shared.config import AppConfig

class _HtmlResult:
    """Internal wrapper to safely pass raw HTML (like plots) through the formatting pipeline."""
    def __init__(self, html):
        self.html = html

class MathematicaBackend:
    """
    Organizational-Level Backend.
    Features: Smart Syntax Sanitizer, Steps Engine, Wolfram Parity, Inline Plotting, Manipulate.
    """
    def __init__(self):
        self.session_vars = {}
        self.command_mapping = {} 
        self.simple_mode = False
        self._is_loaded = False  # Track if the heavy engine has initialized

    def _ensure_loaded(self):
        """Lazy loads heavy libraries and local modules to guarantee instant UI startup."""
        if self._is_loaded:
            return

        # --- HEAVY EXTERNAL IMPORTS ---
        import sympy
        from sympy.parsing.mathematica import parse_mathematica
        from sympy import pretty, latex
        import matplotlib as mpl

        # --- HEAVY MODULAR IMPORTS ---
        from .common_types import StepResult, SolutionResult
        from .solver_logic import solve_mathematica_style, nsolve_mathematica_style, nsteps_mathematica_style
        from .ast_evaluator import evaluate_ast
        from .simple_logic import execute_simple_math
        from .dual_syntax import normalize_dual_syntax, COMMAND_HEAD_ALIASES

        # Cache references for use throughout the class
        self.sympy = sympy
        self.parse_mathematica = parse_mathematica
        self.latex = latex
        self.mpl = mpl
        self.StepResult = StepResult
        self.SolutionResult = SolutionResult
        self.evaluate_ast = evaluate_ast
        self.execute_simple_math = execute_simple_math
        self.normalize_dual_syntax = normalize_dual_syntax

        # 1. Standard Constants
        var_names = 'x y z t a b c k m n theta phi omega'
        self.session_vars.update(dict(zip(var_names.split(), self.sympy.symbols(var_names))))
        self.session_vars['i'] = self.sympy.I
        self.session_vars['e'] = self.sympy.E
        self.session_vars['Pi'] = self.sympy.pi
        self.session_vars['Infinity'] = self.sympy.oo
        
        # 2. Load SymPy Globals
        self.command_mapping.update(self.sympy.__dict__)
        
        # 3. Register Wolfram-like Commands
        self.command_mapping.update({
            # Solvers
            'Solve': solve_mathematica_style, 
            'solve': solve_mathematica_style,
            'NSolve': nsolve_mathematica_style,
            'NSteps': nsteps_mathematica_style,
            
            # Calculus
            'D': self.sympy.diff, 'Diff': self.sympy.diff,
            'Integrate': self.sympy.integrate,
            'Limit': self.sympy.limit,
            'Sum': self.sympy.summation,
            'Product': self.sympy.product,
            
            # Algebra
            'Simplify': self.sympy.simplify,
            'FullSimplify': self.sympy.simplify,
            'Expand': self.sympy.expand,
            'Factor': self.sympy.factor,
            'Apart': self.sympy.apart, 
            'Together': self.sympy.together,
            
            # Matrix
            'Matrix': self._smart_matrix,
            'IdentityMatrix': self.sympy.eye,
            'Inverse': lambda m: m.inv(),
            'Det': self.sympy.det,
            'Eigenvalues': lambda m: m.eigenvals(),
            'Eigenvectors': lambda m: m.eigenvects(),
            
            # Plotting (2D is Matplotlib, 3D is Interactive Plotly)
            'Plot': self._plot_wrapper,
            'Plot3D': self._plot3d_wrapper,
            
            # Macro Placeholder
            'Steps': None,
            'NSteps': None,
        })

        self.command_mapping.update({
            key: self.command_mapping.get(value, value)
            for key, value in COMMAND_HEAD_ALIASES.items()
            if value in self.command_mapping
        })
        
        self.command_mapping.update(self.session_vars)
        self._is_loaded = True

    # --- PLOTTING WRAPPERS ---
    def _plot_wrapper(self, *args, **kwargs):
        """2D Plotting remains Matplotlib for crisp, compact, static rendering"""
        self._ensure_loaded()
        kwargs['show'] = False
        p = self.sympy.plotting.plot(*args, **kwargs)
        return self._generate_plot_html(p)

    def _plot3d_wrapper(self, *args, **kwargs):
        """3D Plotting is routed to Plotly for full mouse interactivity"""
        self._ensure_loaded()
        try:
            import plotly.graph_objects as go
            import numpy as np
            
            # Let SymPy handle the parsing of the math expression and ranges safely
            kwargs['show'] = False
            p = self.sympy.plotting.plot3d(*args, **kwargs)
            
            fig = go.Figure()
            
            # Loop through series (in case the user plotted multiple functions at once)
            for series in p:
                expr = series.expr
                var_x, var_y = series.var_x, series.var_y
                
                # Use Numpy Lambdify for blazing fast coordinate generation
                f = self.sympy.lambdify((var_x, var_y), expr, "numpy")
                
                # Create a 60x60 grid
                X_vals = np.linspace(float(series.start_x), float(series.end_x), 60)
                Y_vals = np.linspace(float(series.start_y), float(series.end_y), 60)
                X, Y = np.meshgrid(X_vals, Y_vals)
                Z = f(X, Y)
                
                # Guarantee a 2D array if the mathematical expression evaluated to a scalar constant
                if np.isscalar(Z) or (isinstance(Z, np.ndarray) and Z.ndim == 0):
                    Z = np.full_like(X, Z, dtype=float)
                
                fig.add_trace(go.Surface(
                    z=Z, x=X, y=Y, 
                    colorscale='Viridis',
                    name=str(expr),
                    showscale=False
                ))
            
            # Match our IDE's Dark Theme
            fig.update_layout(
                template='plotly_dark',
                paper_bgcolor='#1e1e1e',
                plot_bgcolor='#1e1e1e',
                margin=dict(l=0, r=0, t=30, b=0),
                scene=dict(
                    xaxis=dict(gridcolor='#3e3e42', backgroundcolor='#252526', title=str(var_x)),
                    yaxis=dict(gridcolor='#3e3e42', backgroundcolor='#252526', title=str(var_y)),
                    zaxis=dict(gridcolor='#3e3e42', backgroundcolor='#252526', title='z')
                )
            )
            
            # Convert to standalone HTML and encode as Base64 Data URI
            raw_html = fig.to_html(full_html=False, include_plotlyjs=False)
            b64_html = base64.b64encode(raw_html.encode('utf-8')).decode('utf-8')
            
            html = f"""
            <div style='
                margin-top: 10px; 
                resize: both; 
                overflow: hidden; 
                width: 600px; 
                height: 500px; 
                min-width: 300px; 
                min-height: 300px;
                border: 1px solid #3e3e42; 
                border-radius: 4px; 
                background-color: #1e1e1e;
            '>
                <iframe src='data:text/html;base64,{b64_html}' style='width: 100%; height: 100%; border: none;'></iframe>
            </div>
            """
            return _HtmlResult(html)
            
        except ImportError:
            return _HtmlResult("<span style='color:#e06c75'>Please run `pip install plotly` to use interactive 3D plots.</span>")
        except Exception as e:
            return _HtmlResult(f"<span style='color: #e06c75'><b>Plotly 3D Error:</b> {str(e)}</span>")

    def _generate_plot_html(self, plot_obj):
        """Renders a SymPy 2D plot into a Base64 dark-themed Matplotlib image"""
        self._ensure_loaded()
        try:
            if AppConfig.get_language() == "as":
                font_stack = ['Nirmala UI', 'Noto Sans Bengali', 'Vrinda', 'DejaVu Sans']
            else:
                font_stack = ['DejaVu Sans', 'Arial', 'Helvetica']
            with self.mpl.rc_context({
                'figure.figsize': (5.0, 3.5),
                'figure.dpi': 100,
                'font.family': 'sans-serif',
                'font.sans-serif': font_stack,
                'figure.facecolor': '#1e1e1e',
                'axes.facecolor': '#1e1e1e',
                'axes.edgecolor': '#3e3e42',
                'axes.labelcolor': '#d4d4d4',
                'text.color': '#d4d4d4',
                'xtick.color': '#d4d4d4',
                'ytick.color': '#d4d4d4',
                'grid.color': '#3e3e42',
                'grid.alpha': 0.5,
                'legend.facecolor': '#252526',
                'legend.edgecolor': '#3e3e42',
                'legend.labelcolor': '#d4d4d4'
            }):
                tmp_fd, tmp_path = tempfile.mkstemp(suffix=".png")
                os.close(tmp_fd)
                
                try:
                    plot_obj.save(tmp_path)
                    with open(tmp_path, "rb") as f:
                        b64_img = base64.b64encode(f.read()).decode('utf-8')
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                    self.mpl.pyplot.close('all')
            
            html = f"""
            <div style='
                margin-top: 10px; resize: both; overflow: hidden; width: 500px; 
                min-width: 200px; max-width: 100%; border: 1px solid #3e3e42; 
                border-radius: 4px; background-color: #1e1e1e; padding: 5px;
            '>
                <img src='data:image/png;base64,{b64_img}' style='width: 100%; height: 100%; object-fit: contain; pointer-events: none;'>
            </div>
            """
            return _HtmlResult(html)
        except Exception as e:
            return _HtmlResult(f"<span style='color: #e06c75'><b>Plot Rendering Error:</b> {str(e)}</span>")

    # --- UTILS & EXECUTION ---
    def _smart_matrix(self, *args):
        self._ensure_loaded()
        if len(args) == 1: return self.sympy.Matrix(args[0])
        return self.sympy.Matrix(list(args))

    def _sanitize_syntax(self, code):
        self._ensure_loaded()
        code = self.normalize_dual_syntax(code)

        if "Matrix[[" in code:
            code = re.sub(
                r"Matrix\[\[(.*?)\]\]",
                lambda m: "Matrix[{" + m.group(1).replace("[", "{").replace("]", "}") + "}]",
                code,
                flags=re.DOTALL,
            )
        if "->" in code:
            # Safely replace '->' with ',' only OUTSIDE of string literals
            parts = code.split('"')
            for i in range(0, len(parts), 2):  # Even indices are outside double quotes
                parts[i] = parts[i].replace("->", ",")
            code = '"'.join(parts)
            
        return code

    def get_user_variables(self):
        self._ensure_loaded()
        user_vars = {}
        # Remove self.session_vars.keys() from the ignore list!
        ignore_keys = set(self.sympy.__dict__.keys()).union({
            'Solve', 'solve', 'NSolve', 'NSteps', 'D', 'Diff', 'Integrate', 'Limit', 'Sum', 'Product',
            'Simplify', 'FullSimplify', 'Expand', 'Factor', 'Apart', 'Together',
            'Matrix', 'IdentityMatrix', 'Inverse', 'Det', 'Eigenvalues', 'Eigenvectors',
            'Plot', 'Plot3D', 'Steps'
        })
        for k, v in self.command_mapping.items():
            if k not in ignore_keys and not isinstance(v, (types.FunctionType, types.MethodType, types.ModuleType)):
                # FIX: Only ignore x, y, z if they haven't been assigned a value
                if k in self.session_vars and isinstance(v, self.sympy.Symbol) and v.name == k:
                    continue
                user_vars[k] = v
        return user_vars

    # --- MANIPULATE ENGINE ---
    def _handle_manipulate(self, command, cell_id):
        # Parse Manipulate[expr, {var, min, max, (step)}]
        inner = command[11:-1].strip()
        last_brace_idx = inner.rfind("{")
        comma_idx = inner.rfind(",", 0, last_brace_idx)
        
        if last_brace_idx == -1 or comma_idx == -1:
            return _HtmlResult("<span style='color: #e06c75'><b>Manipulate Error:</b> Invalid syntax. Expected Manipulate[expr, {var, min, max, (step)}]</span>")
            
        expr_str = inner[:comma_idx].strip()
        var_str = inner[last_brace_idx+1 : inner.rfind("}")].strip()
        parts = [p.strip() for p in var_str.split(',')]
        
        var_name = parts[0]
        min_val = float(parts[1])
        max_val = float(parts[2])
        step_val = float(parts[3]) if len(parts) > 3 else (max_val - min_val) / 100.0
        
       # Temporarily inject the minimum value to evaluate the initial plot
        old_val = self.command_mapping.get(var_name, None)
        self.command_mapping[var_name] = min_val
        
        try:
            res_html = self.execute(expr_str, cell_id)
        finally:
            # Cleanup variable injection safely, even if execution fails
            if old_val is not None: 
                self.command_mapping[var_name] = old_val
            else: 
                del self.command_mapping[var_name]
            
        b64_expr = base64.b64encode(expr_str.encode('utf-8')).decode('utf-8')
        
        html = f"""
        <div class="manipulate-container" style="border: 1px solid #3e3e42; border-radius: 6px; padding: 15px; background-color: #252526; margin-top: 10px;">
            <div id="manipulate-display-{cell_id}" style="min-height: 100px;">
                {res_html}
            </div>
            <div style="margin-top: 20px; display: flex; align-items: center; gap: 15px; background: #1e1e1e; padding: 10px; border-radius: 4px; border: 1px solid #333;">
                <label style="font-family: Consolas; color: #c678dd; font-weight: bold; min-width: 80px;">{var_name} = <span id="val-{var_name}-{cell_id}">{min_val}</span></label>
                <input type="range" min="{min_val}" max="{max_val}" step="{step_val}" value="{min_val}" 
                       style="flex-grow: 1; cursor: pointer; accent-color: #007acc;"
                       oninput="updateManipulate(this.value, {cell_id}, '{var_name}', '{b64_expr}')">
            </div>
        </div>
        """
        return _HtmlResult(html)

    def execute(self, command: str, cell_id: int = 0):
        self._ensure_loaded()
        
        command = command.strip()
        if not command: return ""
        
        # Route to Simple Mode Logic if toggled
        if getattr(self, 'simple_mode', False):
            return self.execute_simple_math(command, self._format_as_latex)

        command = self._sanitize_syntax(command)

        try:
            # 1. Handle Manipulate Command
            if command.startswith("Manipulate[") and command.endswith("]"):
                res = self._handle_manipulate(command, cell_id)
                return self._format_result(res)

            # 2. Handle Assignments
            if (
                "=" in command
                and "==" not in command
                and not command.startswith("Solve")
                and not command.startswith("NSolve")
                and not command.startswith("Steps")
                and not command.startswith("NSteps")
            ):
                lhs, rhs_str = command.split("=", 1)
                lhs = lhs.strip()
                rhs_node = self.parse_mathematica(rhs_str)
                rhs_val = self.evaluate_ast(rhs_node, self.command_mapping)
                self.command_mapping[lhs] = rhs_val
                return self._format_as_latex(rhs_val, prefix=f"{lhs} = ")

            # 3. Standard Execution
            expr_tree = self.parse_mathematica(command)
            result = self.evaluate_ast(expr_tree, self.command_mapping)
            return self._format_result(result)

        except Exception as e:
            return f"<span style='color: #e06c75'><b>Kernel Error:</b> {str(e)}</span>"

    def _format_result(self, result):
        self._ensure_loaded()
        if result is None: return ""
        if isinstance(result, (self.StepResult, self.SolutionResult)): return result.to_html()
        if isinstance(result, _HtmlResult): return result.html
        return self._format_as_latex(result)

    def _format_as_latex(self, obj, prefix=""):
        self._ensure_loaded()
        try:
            latex_code = self.latex(obj)
            return f"""
            <div style='margin-top: 8px; margin-bottom: 8px; padding-left: 4px; text-align: left;'>
                <span style='color: #7f8c8d; font-family: Consolas; font-size: 14px;'>{prefix}</span>
                <div style='font-size: 115%; color: #dcdcaa; margin-top: 4px; display: inline-block;'>
                    \\( \\displaystyle {latex_code} \\)
                </div>
            </div>
            """
        except Exception:
            return f"<div style='color: #d4d4d4;'>{str(obj)}</div>"
            
    # --- PERSISTENCE ---
    def save_session(self, filepath):
        try:
            user_vars = self.get_user_variables()
            data = {k: str(v) for k, v in user_vars.items()}
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            return True, f"Saved {len(data)} variables safely."
        except Exception as e: 
            return False, f"Save Error: {str(e)}"

    def load_session(self, filepath):
        self._ensure_loaded()
        if not os.path.exists(filepath): 
            return False, "File not found."
        try:
            with open(filepath, 'r', encoding='utf-8') as f: 
                data = json.load(f)
            count = 0
            for k, v_str in data.items():
                self.command_mapping[k] = self.sympy.sympify(v_str)
                count += 1
            return True, f"Safely loaded {count} variables."
        except Exception as e: 
            return False, f"Load Error: {str(e)}"