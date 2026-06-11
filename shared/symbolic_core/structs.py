from .arrays import MatlabArray
import numpy as np

class MatlabStruct:
    """
    MATLAB-compatible Structure.
    Behaves like a dictionary but allows dot-access (s.field).
    """
    def __init__(self, **kwargs):
        # We store data in self.__dict__ so that s.x works natively
        for k, v in kwargs.items():
            self.__dict__[k] = v

    def __repr__(self):
        # MATLAB-style display
        keys = sorted([k for k in self.__dict__.keys() if not k.startswith('_')])
        if not keys:
            return "struct with no fields."
        
        out = ["<struct with fields:>"]
        for k in keys:
            val = self.__dict__[k]
            # Format value summary
            if isinstance(val, MatlabArray):
                dims = "x".join(str(d) for d in val.shape)
                v_str = f"[{dims} double]"
            elif isinstance(val, (int, float, complex)):
                v_str = f"[{val}]"
            elif isinstance(val, str):
                v_str = f"'{val}'"
            else:
                v_str = str(type(val).__name__)
            
            out.append(f"    {k}: {v_str}")
            
        return "\n".join(out)

    # Allow dynamic field creation via s.field = value (Native Python does this, 
    # but we can add hooks here if needed later)