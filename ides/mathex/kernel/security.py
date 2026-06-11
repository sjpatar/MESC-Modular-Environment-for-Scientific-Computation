import ast
import os
import builtins

# [FIX] SECURITY BUG: Force safe mode if running as a web service
os.environ["MESC_SAFE_MODE"] = "1" 

SAFE_MODE_ENV_VAR = "MESC_SAFE_MODE"
_SAFE_MODE_TRUE_VALUES = {"1", "true", "yes", "on", "web"}

_SAFE_BUILTINS = {
    "__build_class__": builtins.__build_class__, # Allow class construction
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "complex": complex,
    "dict": dict,
    "enumerate": enumerate,
    "Exception": Exception,
    "float": float,
    "int": int,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "pow": pow,
    "print": print,
    "range": range,
    "reversed": reversed,
    "round": round,
    "set": set,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}

_BLOCKED_CALLS = {
    "__import__",
    "breakpoint",
    "compile",
    "delattr",
    "eval",
    "exec",
    "getattr",
    "globals",
    "input",
    "locals",
    "open",
    "setattr",
    "vars",
}

_BLOCKED_ROOT_NAMES = {
    "builtins",
    "ctypes",
    "importlib",
    "os",
    "pathlib",
    "shutil",
    "socket",
    "subprocess",
    "sys",
}


def env_safe_mode_enabled():
    value = os.environ.get(SAFE_MODE_ENV_VAR, "")
    return value.strip().lower() in _SAFE_MODE_TRUE_VALUES


def build_execution_builtins(safe_mode=False):
    if safe_mode:
        return dict(_SAFE_BUILTINS)
    return __builtins__


def validate_user_ast(tree):
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise PermissionError("Import statements are disabled in MESC safe mode.")

        if isinstance(node, ast.Name) and node.id.startswith("__"):
            raise PermissionError("Dunder names are disabled in MESC safe mode.")

        if isinstance(node, ast.Attribute):
            if node.attr.startswith("__"):
                raise PermissionError("Dunder attribute access is disabled in MESC safe mode.")
            root_name = _attribute_root_name(node)
            if root_name in _BLOCKED_ROOT_NAMES:
                raise PermissionError(
                    f"Access to '{root_name}' is disabled in MESC safe mode."
                )

        if isinstance(node, ast.Call):
            called_name = _called_name(node.func)
            if called_name in _BLOCKED_CALLS:
                raise PermissionError(
                    f"Calling '{called_name}' is disabled in MESC safe mode."
                )


def _attribute_root_name(node):
    current = node
    while isinstance(current, ast.Attribute):
        current = current.value
    if isinstance(current, ast.Name):
        return current.id
    return None


def _called_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None
