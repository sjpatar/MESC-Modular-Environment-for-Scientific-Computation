# MESC/ides/mathex/io/saver.py
import scipy.io as sio
import numpy as np
from shared.symbolic_core.arrays import MatlabArray
from shared.symbolic_core.structs import MatlabStruct

def save_workspace(session, filepath: str):
    """
    Serializes the current KernelSession globals into a .mat file.
    Safely unwraps MatlabArray and filters out functions/built-ins.
    """
    export_dict = {}
    
    for name, val in session.globals.items():
        # Ignore private variables, dunder methods, and kernel built-ins
        if name.startswith("_") or name in session._builtins_set:
            continue
            
        # Ignore functions, modules, and un-serializable callables
        if callable(val) or type(val).__name__ == "module":
            continue
            
        # 1. Handle MatlabArrays -> Extract raw NumPy data
        if isinstance(val, MatlabArray):
            export_dict[name] = val._data
            
        # 2. Handle MatlabStructs -> Convert to dict for scipy.io
        elif isinstance(val, MatlabStruct):
            struct_dict = {}
            for k in dir(val):
                if not k.startswith("_"):
                    v = getattr(val, k)
                    if isinstance(v, MatlabArray):
                        struct_dict[k] = v._data
                    else:
                        struct_dict[k] = v
            export_dict[name] = struct_dict
            
        # 3. Handle standard Python primitive types
        elif isinstance(val, (int, float, str, complex, np.ndarray)):
            export_dict[name] = val

    if not filepath.endswith('.mat'):
        filepath += '.mat'

    # Write to disk. do_compression ensures optimal file sizes for large matrices.
    sio.savemat(filepath, export_dict, do_compression=True)