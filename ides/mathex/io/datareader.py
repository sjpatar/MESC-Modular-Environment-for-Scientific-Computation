# MESC/ides/mathex/io/datareader.py
import scipy.io as sio
import numpy as np
import os
from shared.symbolic_core.arrays import MatlabArray
from shared.symbolic_core.structs import MatlabStruct

# =====================================================================
# Workspace Deserialization (.mat)
# =====================================================================
def load_workspace(session, filepath: str):
    """
    Deserializes a .mat file back into the KernelSession.
    Wraps raw NumPy arrays back into the MESC MatlabArray paradigm.
    """
    if not filepath.endswith('.mat'):
        filepath += '.mat'

    # mat_dtype=True preserves the MATLAB matrix semantics
    # struct_as_record=False unwraps structs predictably
    data = sio.loadmat(filepath, mat_dtype=True, struct_as_record=False, squeeze_me=False)

    for name, val in data.items():
        # Ignore scipy.io metadata keys (__header__, __version__, __globals__)
        if name.startswith("__"):
            continue

        # 1. Re-wrap Ndarrays back into the MESC architecture
        if isinstance(val, np.ndarray):
            # Check if it's actually a serialized struct masquerading as an array
            if type(val).__name__ == 'mat_struct':
                struct_data = {}
                for field in val._fieldnames:
                    struct_data[field] = getattr(val, field)
                session.globals[name] = MatlabStruct(**struct_data)
            else:
                session.globals[name] = MatlabArray(val)
                
        # 2. Re-wrap Primitives
        elif isinstance(val, (int, float, complex)):
            session.globals[name] = val
            
        # 3. Re-wrap Strings
        elif isinstance(val, str) or isinstance(val, np.str_):
            session.globals[name] = str(val)


# =====================================================================
# Tabular & CSV Data Reading 
# =====================================================================
def readmatrix(filepath: str) -> MatlabArray:
    """Reads a CSV or text file into a standard MatlabArray matrix."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: '{filepath}'")
        
    try:
        # Try comma separated first
        data = np.loadtxt(filepath, delimiter=',')
    except Exception:
        try:
            # Fallback to whitespace separated
            data = np.loadtxt(filepath)
        except Exception as e:
            raise RuntimeError(f"Could not read matrix from {filepath}: {e}")
            
    # MATLAB matrices are inherently 2D
    if data.ndim == 1:
        data = data.reshape(1, -1)
        
    return MatlabArray(data)


def csvread(filepath: str) -> MatlabArray:
    """Legacy alias for readmatrix."""
    return readmatrix(filepath)


def readtable(filepath: str) -> MatlabStruct:
    """
    Reads a CSV file with headers into a MatlabStruct, 
    making column data accessible via dot notation (e.g., table.Age).
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: '{filepath}'")
        
    try:
        import pandas as pd
        df = pd.read_csv(filepath)
        
        struct_data = {}
        for col in df.columns:
            # Convert each column into a MatlabArray column vector
            col_data = df[col].to_numpy()
            if col_data.ndim == 1:
                col_data = col_data.reshape(-1, 1) 
            struct_data[str(col)] = MatlabArray(col_data)
            
        return MatlabStruct(**struct_data)
        
    except ImportError:
        # Robust fallback using NumPy if Pandas is missing
        data = np.genfromtxt(filepath, delimiter=',', names=True, dtype=None, encoding=None)
        
        if data.dtype.names:
            struct_data = {}
            for name in data.dtype.names:
                col_data = np.array(data[name])
                if col_data.ndim == 1:
                    col_data = col_data.reshape(-1, 1)
                struct_data[str(name)] = MatlabArray(col_data)
            return MatlabStruct(**struct_data)
            
        # If no headers found, fallback to standard matrix
        return readmatrix(filepath)