"""
Kernel-level function runtime helpers.

Responsibilities:
- Manage a call-stack of frames for executing user functions.
- Provide call_function(name, args, kwargs, session) that:
    * pushes a frame
    * invokes the FunctionEntry.func with isolation and timeouts (no threads here)
    * pops the frame and returns result
- Provide utilities to create isolated local scopes for debugging.
"""

import time
import traceback
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from ides.mathex.language.functions import registry, FunctionEntry

@dataclass
class CallFrame:
    name: str
    entry: Optional[FunctionEntry] = None
    locals: Dict[str, Any] = field(default_factory=dict)
    globals: Dict[str, Any] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)

class FunctionRuntimeError(RuntimeError):
    pass

class CallStack:
    def __init__(self):
        self._frames: List[CallFrame] = []

    def push(self, frame: CallFrame):
        self._frames.append(frame)

    def pop(self) -> Optional[CallFrame]:
        if not self._frames:
            return None
        return self._frames.pop()

    def top(self) -> Optional[CallFrame]:
        if not self._frames: return None
        return self._frames[-1]

    def stack_trace(self) -> List[str]:
        return [f"{i}: {f.name}" for i, f in enumerate(self._frames)]

# Global (singleton) call stack used by the kernel
call_stack = CallStack()

def create_local_scope_from_session(session_globals: dict) -> Dict[str, Any]:
    """
    Create a fresh globals mapping for executing a user function.
    We copy the session_globals shallowly so the function has access to the same
    module-level names but modifications won't clobber the session unless they set globals directly.
    """
    # Shallow copy is intentional - functions will see current values but changes to mutable objects reflect back.
    g = dict(session_globals)
    # Ensure __builtins__ present for Python runtime functions
    if '__builtins__' not in g:
        import builtins
        g['__builtins__'] = builtins.__dict__
    return g

def call_function(name: str, args: Tuple[Any, ...], kwargs: Optional[Dict[str, Any]], session) -> Any:
    """
    Call a registered function by name.
    - name: function name registered in registry
    - args: positional arguments
    - kwargs: keyword arguments (optional)
    - session: KernelSession instance (gives access to session.globals)
    """
    if kwargs is None: kwargs = {}

    entry = registry.get(name)
    if entry is None:
        raise FunctionRuntimeError(f"Function '{name}' is not registered.")

    # Create a fresh execution globals mapping based on session
    exec_globals = create_local_scope_from_session(session.globals)

    # Update function's __globals__ if it was compiled with a different dict.
    # WARNING: changing a function's __globals__ affects closures; do this cautiously.
    func = entry.func

    # Create call frame and push
    frame = CallFrame(name=name, entry=entry, locals={}, globals=exec_globals)
    call_stack.push(frame)

    try:
        # Execute: if the function is a bound FunctionType, simply call it.
        # The function's globals were set at compile time (register_from_source used exec with a copy of session.globals).
        # This call will run using its own __globals__, but we ensure the session values are up-to-date by optionally re-binding names.
        # Optionally rebind common names:
        for k, v in session.globals.items():
            if k in func.__globals__:
                func.__globals__[k] = v

        result = func(*args, **kwargs)

        # update 'ans' in session
        try:
            session.set_variable('ans', result)
        except Exception:
            pass

        return result

    except Exception as e:
        tb = traceback.format_exc()
        raise FunctionRuntimeError(f"Error calling function '{name}': {e}\n{tb}") from e

    finally:
        call_stack.pop()
