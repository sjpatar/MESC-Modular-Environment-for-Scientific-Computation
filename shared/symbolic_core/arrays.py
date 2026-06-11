from __future__ import annotations
import sys
import numpy as np
import scipy.linalg
import scipy.sparse
import scipy.sparse.linalg
import warnings  # [CRITICAL] Required for error suppression
from typing import Union

# Update types to include SciPy sparse matrices
ArrayLike = Union[
    np.ndarray, 
    scipy.sparse.spmatrix, 
    list, tuple, int, float, complex, 
    "MatlabArray"
]


# Dummy colon marker for runtime (true MATLAB : )
class ColonType:
    pass
colon = ColonType()


def _to_data(x):
    """
    Helper to extract underlying data (Dense or Sparse).
    Does NOT force conversion to dense numpy array.
    """
    if isinstance(x, MatlabArray):
        return x._data
    return x


def _to_numpy(x):
    """
    Helper to force data into a dense Numpy array.
    Used for indices or incompatible operations.
    """
    d = _to_data(x)
    if scipy.sparse.issparse(d):
        return d.toarray()
    return np.asarray(d)


class MatlabArray:
    """
    MATLAB-like numerical array with Copy-on-Write (CoW) optimization.
    """

    # -----------------------------------------------------
    # CONSTRUCTOR
    # -----------------------------------------------------
    def __init__(self, data: ArrayLike, copy: bool = True):
        """
        Initialize a MatlabArray.
        :param data: Input data (list, numpy array, sparse matrix, or MatlabArray)
        :param copy: If True, forces a deep copy. If False, allows shared memory (Copy-on-Write).
        """
        if isinstance(data, MatlabArray):
            if copy:
                self._data = data._data.copy()
            else:
                self._data = data._data  # Shared view for CoW
        elif scipy.sparse.issparse(data):
            self._data = data
        elif isinstance(data, (list, tuple)):
            # [FIX] Check for strings to avoid np.block/scipy.sparse error
            has_str = any(isinstance(x, str) for x in data)
            if has_str:
                self._data = np.array(data)
            else:
                try:
                    def unwrap_rec(x):
                        if isinstance(x, MatlabArray):
                            return x._data
                        if isinstance(x, (list, tuple)):
                            return [unwrap_rec(i) for i in x]
                        return x
                    
                    unwrapped = unwrap_rec(data)
                    self._data = np.block(unwrapped)
                except Exception:
                    self._data = np.array(data)
        else:
            self._data = np.array(data)

        # [FIX] Only cast to complex if explicit string type, otherwise respect input
        if hasattr(self._data, 'dtype') and self._data.dtype.kind in ('U', 'S'):
            try:
                # Try casting to float first
                self._data = self._data.astype(float)
            except ValueError:
                try:
                    self._data = self._data.astype(complex)
                except Exception:
                    pass

        if not scipy.sparse.issparse(self._data):
            if self._data.ndim == 0:
                self._data = self._data.reshape(1, 1)
            elif self._data.ndim == 1:
                self._data = self._data.reshape(1, -1)

    # -----------------------------------------------------
    # COPY-ON-WRITE LOGIC
    # -----------------------------------------------------
    def _ensure_unique(self):
        """
        CoW Logic: If the underlying numpy array is shared by multiple 
        MatlabArray instances, copy it before mutation.
        """
        # Refcount is usually 2 for a unique object (1 for variable, 1 for getrefcount argument)
        # If > 2, someone else holds a reference to this data.
        if hasattr(self._data, 'copy') and sys.getrefcount(self._data) > 2:
            self._data = self._data.copy()

    # -----------------------------------------------------
    # PYTHON INTEROPERABILITY
    # -----------------------------------------------------
    def __array__(self, dtype=None):
        if self.is_sparse:
            return self._data.toarray()
        return np.asarray(self._data, dtype=dtype)
    
    def __float__(self):
        val = self._data.item()
        if isinstance(val, complex):
            return float(val.real)
        return float(val)

    def __int__(self):
        return int(self._data.item())
    
    def __bool__(self):
        if self.size == 0:
            return False
        if self.size == 1:
            return bool(self._data.item())
        # MATLAB behavior: True only if ALL elements are non-zero
        if self.is_sparse:
             return self.nnz == self.size 
        return np.all(self._data).item()
    
    def __iter__(self):
        rows, cols = self.shape
        for c in range(cols):
            col_slice = self._data[:, c:c+1]
            yield MatlabArray(col_slice)

    # Attribute Access (for Structs)
    def __getattr__(self, name):
        if not self.is_sparse and self.size == 1 and self._data.dtype == object:
            item = self._data.flat[0]
            if hasattr(item, name):
                return getattr(item, name)
            if isinstance(item, dict) and name in item:
                return item[name]
        raise AttributeError(f"'MatlabArray' object has no attribute '{name}'")

    # -----------------------------------------------------
    # PROPERTIES
    # -----------------------------------------------------
    @property
    def is_sparse(self):
        return scipy.sparse.issparse(self._data)

    @property
    def shape(self):
        return self._data.shape

    @property
    def size(self):
        return self._data.size

    @property
    def nnz(self):
        if self.is_sparse:
            return self._data.nnz
        return np.count_nonzero(self._data)

    @property
    def T(self):
        return MatlabArray(self._data.T)

    @property
    def H(self):
        if self.is_sparse:
            return MatlabArray(self._data.conj().T)
        return MatlabArray(self._data.conj().T)

    def __len__(self):
        return max(self.shape)

    # -----------------------------------------------------
    # REPRESENTATION
    # -----------------------------------------------------
    def __repr__(self):
        if self.is_sparse:
            d = self._data.tocoo()
            if d.nnz == 0: return f"All zero sparse: {self.shape[0]}x{self.shape[1]}"
            limit = 20
            lines = [f"<Sparse {self.shape} with {d.nnz} stored elements>"]
            for i in range(min(d.nnz, limit)):
                lines.append(f"  ({d.row[i]+1}, {d.col[i]+1})\t{d.data[i]}")
            if d.nnz > limit: lines.append(f"  ... and {d.nnz - limit} more")
            return "\n".join(lines)

        if self.size == 0:
            return "     []"

        data = self._data
        # MATLAB prints booleans as 1/0 logicals, not True/False
        if data.dtype == bool:
            data = data.astype(int)

        # Suppress Python brackets and emulate MATLAB spacing
        s = np.array2string(
            data,
            separator="    ", 
            formatter={
                'float_kind': lambda x: f"{x:.4f}".rstrip('0').rstrip('.') if x % 1 != 0 else f"{int(x)}",
                'int': lambda x: f"{x}"
            }
        )
        s = s.replace('[', '').replace(']', '')
        
        # Add MATLAB's signature indentation
        lines = s.split('\n')
        return "\n".join("     " + line.strip() for line in lines)

    # -----------------------------------------------------
    # INDEXING: MATLAB Style ()
    # -----------------------------------------------------
    def __call__(self, *args):
        if not args:
            return self

        # CASE 1: Linear Indexing (A(k) or A(:))
        if len(args) == 1:
            arg = args[0]
            
            if arg is colon:
                if self.is_sparse:
                    return MatlabArray(self._data.reshape((-1, 1)))
                return MatlabArray(self._data.flatten(order='F').reshape(-1, 1))
            
            if isinstance(arg, str) and arg == 'end':
                if self.is_sparse:
                    return MatlabArray(self._data.reshape((-1,1))[self.size-1, 0])
                return MatlabArray(self._data.flatten(order='F')[self.size - 1])
                
            val = _to_numpy(arg)
            
            if np.isscalar(val) or (isinstance(val, np.ndarray) and val.ndim == 0):
                idx = int(val) - 1
                if self.is_sparse:
                     d = self._data.reshape((-1, 1))
                     return MatlabArray(d[idx, 0])
                return MatlabArray(self._data.flatten(order='F')[idx])

            arr = np.asarray(val)
            if arr.dtype == bool:
                idx = arr.flatten(order='F')
                if self.is_sparse:
                     d = self._data.reshape((-1, 1))
                     return MatlabArray(d[idx])
                return MatlabArray(self._data.flatten(order='F')[idx].reshape(-1, 1))
            else:
                idx = arr.astype(int) - 1
                if self.is_sparse:
                     d = self._data.reshape((-1, 1))
                     return MatlabArray(d[idx, 0])
                return MatlabArray(self._data.flatten(order='F')[idx].reshape(arr.shape))

        # CASE 2: N-Dimensional Indexing (A(i, j))
        grid_indices = []
        for i, arg in enumerate(args):
            dim_len = self.shape[i] if i < len(self.shape) else 1
            
            if arg is colon:
                grid_indices.append(np.arange(dim_len))
                continue
                
            if isinstance(arg, str) and arg == 'end':
                grid_indices.append(np.array([dim_len - 1]))
                continue
                
            val = _to_numpy(arg)
            if np.isscalar(val) or (isinstance(val, np.ndarray) and val.ndim == 0):
                grid_indices.append(np.array([int(val) - 1]))
                continue
                
            arr = np.asarray(val)
            if arr.dtype == bool:
                grid_indices.append(np.nonzero(arr)[0])
            else:
                grid_indices.append(arr.astype(int) - 1)

        try:
            ix_args = [x.flatten() for x in grid_indices]
            mesh = np.ix_(*ix_args)
            return MatlabArray(self._data[mesh])
        except IndexError:
            raise IndexError("Index out of bounds.")
        except Exception as e:
            raise ValueError(f"Indexing failed: {str(e)}")

    # -----------------------------------------------------
    # INDEXED ASSIGNMENT SUPPORT (With Auto-Expansion)
    # -----------------------------------------------------
    def set_val(self, value, *args):
        """
        Supports 1-based indexed assignment: A(i) = v
        """
        self._ensure_unique()  # <--- CoW Trigger

        py_indices = []
        required_shape = [] 
        is_linear = len(args) == 1
        
        # 1. Parse Arguments
        for i, arg in enumerate(args):
            if arg is colon:
                py_indices.append(slice(None))
                curr_dim = self.shape[i] if i < len(self.shape) else 1
                required_shape.append(curr_dim)
                continue
            
            if isinstance(arg, str) and arg == 'end':
                if is_linear: idx = self.size - 1
                else: idx = self.shape[i] - 1 if i < len(self.shape) else 0
                py_indices.append(idx)
                required_shape.append(idx + 1)
                continue

            val = _to_numpy(arg)
            if isinstance(val, np.ndarray) and val.dtype == bool:
                py_indices.append(val)
                required_shape.append(0) 
                continue

            if np.isscalar(val):
                idx = int(val) - 1
                if idx < 0: raise IndexError("Index must be positive.")
                py_indices.append(idx)
                required_shape.append(idx + 1)
                continue
                
            if isinstance(val, (list, tuple, np.ndarray)):
                arr = np.asarray(val)
                if arr.dtype == bool:
                     py_indices.append(arr)
                     required_shape.append(0)
                else:
                    int_idxs = arr.astype(int) - 1
                    if np.any(int_idxs < 0): raise IndexError("Index must be positive.")
                    py_indices.append(int_idxs)
                    if int_idxs.size > 0:
                        required_shape.append(int_idxs.max() + 1)
                    else:
                        required_shape.append(0)
                continue
            raise TypeError(f"Invalid index type: {type(arg)}")

        val_data = _to_numpy(value)
        if isinstance(val_data, np.ndarray) and val_data.size == 1:
            val_data = val_data.item()

        # [CRITICAL FIX] Auto-Promote to Complex
        # Prevents "ComplexWarning: Casting complex values to real discards the imaginary part"
        if np.iscomplexobj(val_data) and not np.iscomplexobj(self._data):
            self._data = self._data.astype(complex)

        # 2. Try Standard Assignment
        try:
            if len(py_indices) == 1 and not self.is_sparse and self._data.ndim == 2:
                idx = py_indices[0]
                if isinstance(idx, np.ndarray): idx = idx.flatten(order='F')
                if isinstance(val_data, np.ndarray): val_data = val_data.flatten()
                
                flat = self._data.flatten(order='F')
                flat[idx] = val_data
                self._data = flat.reshape(self.shape, order='F')
                return

            self._data[tuple(py_indices)] = val_data

        except IndexError as e:
            # 3. DYNAMIC EXPANSION LOGIC
            if self.is_sparse: raise IndexError("Sparse matrix dynamic expansion not yet supported.")
            
            # Capture current state to prevent infinite recursion
            current_shape_tuple = self._data.shape
            current_size = self.size
            
            if is_linear:
                 req_size = required_shape[0]
                 if req_size > current_size:
                     flat_old = self._data.flatten(order='F')
                     flat_new = np.zeros(req_size, dtype=self._data.dtype)
                     flat_new[:current_size] = flat_old
                     if self.shape[1] == 1 and self.shape[0] > 0:
                         self._data = flat_new.reshape(-1, 1, order='F')
                     else:
                         self._data = flat_new.reshape(1, -1, order='F')
                     
                     if self._data.shape != current_shape_tuple or self._data.size != current_size:
                        self.set_val(value, *args)
                        return
            
            new_shape = list(self.shape)
            while len(new_shape) < len(args): new_shape.append(1)

            for dim, req_max in enumerate(required_shape):
                if req_max > 0: 
                    if dim < len(new_shape): new_shape[dim] = max(new_shape[dim], req_max)
                    else: new_shape.append(req_max)
            
            # RECURSION GUARD: If dimensions didn't grow, we can't fix this via expansion.
            if tuple(new_shape) == current_shape_tuple:
                raise e
            
            expanded = np.zeros(new_shape, dtype=self._data.dtype)
            source_slices = tuple(slice(0, s) for s in current_shape_tuple)
            expanded[source_slices] = self._data
            self._data = expanded
            self.set_val(value, *args)

    # -----------------------------------------------------
    # PYTHON INTERFACE
    # -----------------------------------------------------
    def __getitem__(self, key):
        if isinstance(key, MatlabArray):
            key = key._data
            if isinstance(key, np.ndarray) and key.ndim == 0:
                key = key.item()
        try:
            val = self._data[key]
        except IndexError:
            if np.isscalar(key) and self.size > key:
                return self._data.flatten()[key]
            raise
        if np.isscalar(val): return val
        return MatlabArray(val)

    def __setitem__(self, key, value):
        self._ensure_unique()  # <--- CoW Trigger
        val = _to_numpy(value)
        if isinstance(key, MatlabArray):
            key = key._data
        self._data[key] = val

    # -----------------------------------------------------
    # ARITHMETIC (WARNINGS SUPPRESSED)
    # -----------------------------------------------------
    def __abs__(self):
        if self.is_sparse: return MatlabArray(abs(self._data))
        return MatlabArray(np.abs(self._data))

    def __add__(self, o): return MatlabArray(self._data + _to_data(o))
    def __radd__(self, o): return MatlabArray(_to_data(o) + self._data)
    def __sub__(self, o): return MatlabArray(self._data - _to_data(o))
    def __rsub__(self, o): return MatlabArray(_to_data(o) - self._data)
    def __neg__(self): return MatlabArray(-self._data)
    def __invert__(self): 
        if self.is_sparse: return MatlabArray((self._data != 0).toarray() == False)
        return MatlabArray(~self._data.astype(bool))

    def __mul__(self, o):
        with np.errstate(all='ignore'):
            A = self._data
            B = _to_data(o)
            dimA = A.ndim if hasattr(A, 'ndim') else 0
            dimB = B.ndim if hasattr(B, 'ndim') else 0
            is_scalar_A = (dimA == 0) or (hasattr(A, 'size') and A.size == 1)
            is_scalar_B = (dimB == 0) or (hasattr(B, 'size') and B.size == 1)
            if is_scalar_A or is_scalar_B:
                return MatlabArray(A * B)
            if dimA == 2 and dimB == 2:
                return MatlabArray(A @ B)
            return MatlabArray(A * B)
    __rmul__ = __mul__

    def __truediv__(self, o):
        with np.errstate(all='ignore'):
            B = _to_data(o)
            A = self._data
            if np.isscalar(B) or (hasattr(B, 'size') and B.size == 1):
                return MatlabArray(A / B)
            if hasattr(A, 'ndim') and A.ndim == 2 and hasattr(B, 'ndim') and B.ndim == 2:
                B_dense = B.toarray() if scipy.sparse.issparse(B) else B
                return MatlabArray(A @ scipy.linalg.pinv(B_dense))
            return MatlabArray(A / B)
    
    def __rtruediv__(self, o):
        with np.errstate(all='ignore'):
            return MatlabArray(_to_data(o) / self._data)

    def mldivide(self, o):
        with np.errstate(all='ignore'):
            b = _to_data(o)
            A = self._data
            if hasattr(A, 'ndim') and A.ndim == 2:
                try:
                    if scipy.sparse.issparse(A):
                        x = scipy.sparse.linalg.spsolve(A, b)
                        if isinstance(x, np.ndarray) and x.ndim == 1:
                            if hasattr(b, 'shape') and len(b.shape) >= 2 and b.shape[1] == 1:
                                x = x.reshape(-1, 1)
                        return MatlabArray(x)
                    return MatlabArray(scipy.linalg.solve(A, b))
                except Exception:
                    if scipy.sparse.issparse(A):
                        A_dense = A.toarray()
                        x, _, _, _ = scipy.linalg.lstsq(A_dense, b)
                        return MatlabArray(x)
                    else:
                        x, _, _, _ = scipy.linalg.lstsq(A, b)
                        return MatlabArray(x)
            return MatlabArray(b / A)

    def emul(self, o): 
        with np.errstate(all='ignore'):
            return MatlabArray(self._data.multiply(_to_data(o))) if self.is_sparse else MatlabArray(self._data * _to_data(o))
    
    def ediv(self, o): 
        with np.errstate(all='ignore'):
            return MatlabArray(self._data / _to_data(o))
    
    def epow(self, o): 
        # [FIX] Use np.power to strictly enforce error suppression
        with np.errstate(all='ignore'):
            if self.is_sparse:
                 return MatlabArray(self._data.power(_to_data(o)))
            return MatlabArray(np.power(self._data, _to_data(o)))

    def __pow__(self, p):
        with np.errstate(all='ignore'):
            p = int(p)
            if self.is_sparse:
                return MatlabArray(self._data ** p) 
            return MatlabArray(np.linalg.matrix_power(self._data, p))

    def __lt__(self, o): return MatlabArray(self._data < _to_data(o))
    def __gt__(self, o): return MatlabArray(self._data > _to_data(o))
    def __eq__(self, o): return MatlabArray(self._data == _to_data(o))
    def __le__(self, o): return MatlabArray(self._data <= _to_data(o))
    def __ge__(self, o): return MatlabArray(self._data >= _to_data(o))
    def __ne__(self, o): return MatlabArray(self._data != _to_data(o))


# -----------------------------------------------------
# CONSTRUCTORS
# -----------------------------------------------------
def mat(data): return MatlabArray(data)
def zeros(*args): return MatlabArray(np.zeros(_shape(args)))
def ones(*args): return MatlabArray(np.ones(_shape(args)))
def eye(n): return MatlabArray(np.eye(int(n)))
def linspace(s, e, n=100): return MatlabArray(np.linspace(s, e, int(n)))

def arange(start, stop=None, step=1):
    if stop is None: stop, start = start, 0
    try:
        start_val, stop_val, step_val = float(start), float(stop), float(step)
    except Exception:
        start_val, stop_val, step_val = start, stop, step

    if (float(start_val).is_integer() and float(stop_val).is_integer() and float(step_val).is_integer()):
        start_val, stop_val, step_val = int(start_val), int(stop_val), int(step_val)
        if step_val > 0: return MatlabArray(np.arange(start_val, stop_val + 1, step_val))
        else: return MatlabArray(np.arange(start_val, stop_val - 1, step_val))
    return MatlabArray(np.arange(start_val, stop_val + 1e-12, step_val))

def cell(*args):
    if len(args) == 1 and isinstance(args[0], (list, tuple)):
        return MatlabArray(np.array(args[0], dtype=object))
    shape = _shape(args)
    return MatlabArray(np.empty(shape, dtype=object))

def sparse(i, j=None, v=None, m=None, n=None):
    if j is None and v is None:
        val = _to_data(i)
        if scipy.sparse.issparse(val): return MatlabArray(val)
        return MatlabArray(scipy.sparse.csr_matrix(val))

    idx_i = _to_numpy(i).flatten() - 1
    idx_j = _to_numpy(j).flatten() - 1
    vals  = _to_numpy(v).flatten()

    if m is None: m = int(idx_i.max()) + 1
    if n is None: n = int(idx_j.max()) + 1

    mat_data = scipy.sparse.csr_matrix((vals, (idx_i, idx_j)), shape=(int(m), int(n)))
    return MatlabArray(mat_data)

def full(A: MatlabArray):
    if not isinstance(A, MatlabArray): return MatlabArray(np.array(A))
    if not A.is_sparse: return A
    return MatlabArray(A._data.toarray())

def _shape(args):
    if len(args) == 1:
        arg = args[0]
        if hasattr(arg, '_data'): arg = arg._data
        arg_arr = np.array(arg)
        if arg_arr.size == 1:
            val = int(arg_arr.item())
            return (val, val)
        return tuple(int(x) for x in arg_arr.flatten())
    return tuple(int(a) for a in args)