import sympy
from sympy import Atom

from .i18n import tr
from .step_workflows import generate_command_steps, generate_expression_steps
from .solver_logic import nsteps_mathematica_style, steps_mathematica_style

def evaluate_ast(node, context):
    """Recursively evaluates a SymPy AST within a given context."""
    
    # 1. MACRO DETECTION: Steps[...] and NSteps[...]
    if hasattr(node, 'func'):
        if node.func.__name__ == 'Steps':
            return _handle_steps_macro(node.args, context)
        if node.func.__name__ == 'NSteps':
            return _handle_nsteps_macro(node.args, context)

    # 2. SAFETY TRAP: Prevent nesting UI macros inside mathematical equations
    if hasattr(node, 'func') and node.func.__name__ == 'Manipulate':
        raise ValueError("Manipulate[...] must be the outermost command in the cell. It cannot be nested.")

    # 3. Variable Lookup
    if isinstance(node, sympy.Symbol):
        if node.name in context: return context[node.name]
        return node
        
    # 4. ATOM CHECK
    if isinstance(node, Atom): return node

    # 5. Standard Recursion
    if hasattr(node, 'func') and hasattr(node, 'args'):
        evaluated_args = [evaluate_ast(arg, context) for arg in node.args]
        func_name = node.func.__name__
        
        # Context Dispatch
        if func_name in context:
            return context[func_name](*evaluated_args)
        
        return node.func(*evaluated_args)
        
    return node

def _handle_steps_macro(args, context):
    """Macro handler for Steps[...] (English Instructional format)."""
    if not args: return tr("usage_steps")
    
    target_node = args[0]
    func_name = target_node.func.__name__ if hasattr(target_node, 'func') else ""
    
    try:
        if isinstance(target_node, sympy.Rel):
            return steps_mathematica_style(evaluate_ast(target_node, context))

        eval_args = [evaluate_ast(a, context) for a in getattr(target_node, 'args', [])]
        routed = generate_command_steps(func_name, eval_args, formal=False)
        if routed is not None:
            return routed

        evaluated_target = evaluate_ast(target_node, context)
        return generate_expression_steps(evaluated_target, formal=False)
    except Exception as e:
        return f"<span style='color: #e06c75'><b>{tr('err_step_gen')}:</b> {str(e)}</span>"


def _handle_nsteps_macro(args, context):
    """Macro handler for NSteps[...] (Formal Mathematical LaTeX format)."""
    if not args: return tr("usage_nsteps")
    
    target_node = args[0]
    func_name = target_node.func.__name__ if hasattr(target_node, 'func') else ""
    
    try:
        if isinstance(target_node, sympy.Rel):
            return nsteps_mathematica_style(evaluate_ast(target_node, context))

        eval_args = [evaluate_ast(a, context) for a in getattr(target_node, 'args', [])]
        routed = generate_command_steps(func_name, eval_args, formal=True)
        if routed is not None:
            return routed

        evaluated_target = evaluate_ast(target_node, context)
        return generate_expression_steps(evaluated_target, formal=True)
    except Exception as e:
        return f"<span style='color: #e06c75'><b>{tr('err_nstep_gen')}:</b> {str(e)}</span>"
