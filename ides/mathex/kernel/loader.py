import os
import ast
from ides.mathex.io.mfile import read_mfile
from ides.mathex.language.transpiler import transpile
from ides.mathex.kernel.path_manager import path_manager
from ides.mathex.kernel.security import build_execution_builtins, validate_user_ast
from ides.mathex.language.functions import registry, FunctionEntry

def load_and_register(name: str, builtins_scope=None, safe_mode: bool = False):
    """
    Attempts to find, transpile, and register a function named 'name'.
    Strictly handles .m files only.
    """
    # 1. Resolve File Path (Strict .m lookup via PathManager)
    filepath = path_manager.resolve(name)
    if not filepath:
        return False

    try:
        # 2. Read & Transpile
        code = read_mfile(filepath)
        if code is None: 
            return False

        # Unpack the tuple returned by transpile
        py_code, _ = transpile(code)
        
        # 3. Detect Type (Function vs Script) WITHOUT Executing
        try:
            tree = ast.parse(py_code)
        except SyntaxError as e:
            print(f"Syntax Error in {os.path.basename(filepath)}: {e}")
            return False

        if safe_mode:
            validate_user_ast(tree)

        exec_builtins = builtins_scope or build_execution_builtins(safe_mode)

        is_function = False
        func_name_in_code = name

        if tree.body and isinstance(tree.body[0], ast.FunctionDef):
            is_function = True
            func_name_in_code = tree.body[0].name

        # -------------------------------------------------------
        # CASE A: FUNCTION (function y = f(x))
        # -------------------------------------------------------
        if is_function:
            scope = {"__builtins__": exec_builtins}
            # Execute definition into a temporary scope to create the function object
            exec(py_code, scope)
            
            # Retrieve the function object 
            # Note: We look for the name DEFINED in the file, not necessarily the filename
            func_obj = scope.get(func_name_in_code)
            
            if func_obj and callable(func_obj):
                # Register under the REQUESTED name 'name' so executor can find it
                entry = FunctionEntry(name=name, func=func_obj, source=py_code, source_file=filepath)
                registry.register(entry)
                return True

        # -------------------------------------------------------
        # CASE B: SCRIPT (Commands that modify the workspace)
        # -------------------------------------------------------
        # We create a runner that executes the RAW python code 
        # inside the USER'S globals (the Console Workspace).
        
        def script_runner(globals_dict=None):
            if globals_dict is None:
                # Should not happen in Executor, but failsafe
                globals_dict = {}
            globals_dict.setdefault("__builtins__", exec_builtins)
            
            # [CRITICAL FIX] Execute code DIRECTLY into the session globals
            # This ensures 'x=1' sticks in the workspace.
            exec(py_code, globals_dict)

        # Flags for Executor
        script_runner.__mathex_command__ = True
        script_runner.__mathex_script__ = True 
        
        entry = FunctionEntry(name=name, func=script_runner, source=py_code, source_file=filepath)
        registry.register(entry)
        return True

    except Exception as e:
        print(f"Error loading {name}: {e}")
        return False
        
    return False
