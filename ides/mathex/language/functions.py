"""
mathex.language.functions

A small function registry + loader used by the transpiler/executor to
register user-defined functions (from .m files) and call them later.
"""

from types import FunctionType
from typing import Dict, Optional, List
import textwrap

class FunctionEntry:
    def __init__(self, name: str, func: FunctionType, source: Optional[str]=None, filename: Optional[str]=None, source_file: Optional[str]=None):
        self.name = name
        self.func = func
        self.source = source
        # Compatibility: loader.py sends 'source_file', this class uses 'filename'
        self.filename = filename if filename else source_file

    def __repr__(self):
        return f"<FunctionEntry name={self.name} file={self.filename}>"

class FunctionRegistry:
    """
    Registry stores function objects.
    """
    def __init__(self):
        self._map: Dict[str, FunctionEntry] = {}

    def register(self, entry: FunctionEntry):
        """
        Directly register a FunctionEntry object.
        (Required by loader.py)
        """
        self._map[entry.name] = entry

    def register_from_source(self, name: str, py_source: str, global_scope: dict, filename: Optional[str]=None) -> FunctionEntry:
        """
        Compile python source and register.
        """
        # Defensive copy of globals
        exec_scope = dict(global_scope)
        try:
            exec(py_source, exec_scope)
        except Exception as e:
            raise RuntimeError(f"Failed to compile function source for '{name}': {e}")

        if name not in exec_scope:
            # Fallback search for the function object
            found = None
            for k, v in exec_scope.items():
                if isinstance(v, FunctionType) and v.__name__ == name:
                    found = v; break
            if found is None:
                # Try finding ANY function
                for k, v in exec_scope.items():
                    if isinstance(v, FunctionType):
                        found = v; break
            
            if found is None:
                raise RuntimeError(f"Function '{name}' not found in compiled source.")
            func_obj = found
        else:
            func_obj = exec_scope[name]

        entry = FunctionEntry(name=name, func=func_obj, source=py_source, filename=filename)
        self._map[name] = entry
        return entry

    def register_function_obj(self, name: str, func: FunctionType, filename: Optional[str]=None) -> FunctionEntry:
        entry = FunctionEntry(name=name, func=func, source=None, filename=filename)
        self._map[name] = entry
        return entry

    def get(self, name: str) -> Optional[FunctionEntry]:
        return self._map.get(name)

    def exists(self, name: str) -> bool:
        return name in self._map
    
    # [FIX] Added __contains__ so 'if name in registry' works
    def __contains__(self, name: str) -> bool:
        return name in self._map

    def unregister(self, name: str):
        if name in self._map:
            del self._map[name]

    def list_functions(self) -> List[str]:
        return sorted(list(self._map.keys()))

    def clear(self):
        self._map = {}

# Singleton default registry
registry = FunctionRegistry()