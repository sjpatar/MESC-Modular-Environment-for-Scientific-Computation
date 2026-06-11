import numpy as np
import scipy.linalg
import scipy.sparse
import scipy.sparse.linalg
from .arrays import MatlabArray
from ides.mathex.language.locale import tr

def _to_data(a):
    return a._data if isinstance(a, MatlabArray) else a

def _to_numpy(a):
    d = _to_data(a)
    if scipy.sparse.issparse(d):
        return d.toarray()
    return np.asarray(d)

# -----------------------------------------------------------------------------
# EIGENVALUES & DECOMPOSITIONS
# -----------------------------------------------------------------------------

def eigs(A, k=6, sigma=None, which='LM'):
    """
    d = eigs(A, k)
    [V, D] = eigs(A, k)
    
    Sparse eigenvalue solver with automatic dense fallback for robustness.
    """
    # 1. Prepare A
    if isinstance(A, MatlabArray):
        mat = A._data
    else:
        mat = A

    # 2. Check k
    k = int(k)
    N = mat.shape[0]
    if k >= N:
        k = N - 1  # ARPACK restriction

    # 3. Solve with Fallback
    try:
        # ARPACK solver
        vals, vecs = scipy.sparse.linalg.eigs(mat, k=k, sigma=sigma, which=which)
        
        # Sort output (ARPACK output is not guaranteed to be sorted)
        # Default behavior: Sort by Magnitude (Largest First) for consistency
        idx = np.argsort(np.abs(vals))[::-1]
        vals = vals[idx]
        vecs = vecs[:, idx]

    except Exception as e:
        # Fallback for "Starting vector is zero" or convergence failures
        print(f"{tr('console_warning_prefix')}: {tr('warning_sparse_eigs_fallback', msg=str(e))}")
        
        # Convert to dense
        if scipy.sparse.issparse(mat):
            d_mat = mat.toarray()
        else:
            d_mat = mat
            
        # Dense solve (returns all N eigenvalues)
        vals_all, vecs_all = scipy.linalg.eig(d_mat)
        
        # 4. SORTING & SLICING (Critical to match 'eigs' semantics)
        if sigma is not None:
            # Mode: Find closest to sigma (Shift-Invert equivalent)
            # Sort by distance to sigma (Smallest distance first)
            dist = np.abs(vals_all - sigma)
            idx = np.argsort(dist) 
        else:
            # Mode: Magnitude (LM = Largest Magnitude, SM = Smallest Magnitude)
            mag = np.abs(vals_all)
            if which == 'SM':
                idx = np.argsort(mag)      # Smallest first
            else:
                idx = np.argsort(mag)[::-1] # Largest first ('LM')
        
        # Select top k
        vals = vals_all[idx[:k]]
        vecs = vecs_all[:, idx[:k]]

    # 5. Return
    D = np.diag(vals)
    return MatlabArray(vecs), MatlabArray(D)

def eig(a: MatlabArray, k=None, sigma=None):
    """
    Eigenvalues and eigenvectors.
    
    Usage:
        [V, D] = eig(A)      -> Returns ALL eigenvalues (Standard behavior)
        [V, D] = eig(A, k)   -> Returns k subset (Delegates to eigs)
    """
    # [FIX] Smart delegation: If k is provided, use eigs (subset).
    if k is not None:
        return eigs(a, k=k, sigma=sigma)
    
    # Standard Behavior: Return ALL eigenvalues (Dense)
    data = _to_data(a)
    
    # Ensure dense
    if scipy.sparse.issparse(data):
        data = data.toarray()
        
    vals, vecs = scipy.linalg.eig(data)
    # Standard LAPACK returns unsorted. We leave it as is or sort if preferred.
    return MatlabArray(vecs), MatlabArray(np.diag(vals))

# -----------------------------------------------------------------------------
# BASIC MATRIX OPS
# -----------------------------------------------------------------------------

def inv(a: MatlabArray) -> MatlabArray:
    data = _to_data(a)
    if scipy.sparse.issparse(data):
        return MatlabArray(scipy.sparse.linalg.inv(data))
    return MatlabArray(scipy.linalg.inv(data))

def pinv(a: MatlabArray) -> MatlabArray:
    data = _to_data(a)
    if scipy.sparse.issparse(data):
        data = data.toarray()
    return MatlabArray(scipy.linalg.pinv(data))

def det(a: MatlabArray) -> float:
    data = _to_data(a)
    if scipy.sparse.issparse(data):
        return float(scipy.linalg.det(data.toarray()))
    return float(scipy.linalg.det(data))

def rank(a: MatlabArray) -> int:
    data = _to_data(a)
    if scipy.sparse.issparse(data):
        data = data.toarray()
    return np.linalg.matrix_rank(data)

def norm(a: MatlabArray, ord=None) -> float:
    data = _to_data(a)
    if scipy.sparse.issparse(data):
        return scipy.sparse.linalg.norm(data, ord)
    return scipy.linalg.norm(data, ord)

def cond(a: MatlabArray, p=None):
    data = _to_numpy(a)
    return np.linalg.cond(data, p)

def svd(a: MatlabArray):
    data = _to_data(a)
    if scipy.sparse.issparse(data):
        k = min(6, min(data.shape)-1)
        if k < 1:
            u, s, vt = scipy.linalg.svd(data.toarray())
        else:
            u, s, vt = scipy.sparse.linalg.svds(data, k=k)
            idx = np.argsort(s)[::-1]
            u = u[:, idx]
            s = s[idx]
            vt = vt[idx, :]
        S = np.diag(s)
        return MatlabArray(u), MatlabArray(S), MatlabArray(vt.conj().T)

    u, s, vt = scipy.linalg.svd(data)
    S = scipy.linalg.diagsvd(s, *data.shape)
    return MatlabArray(u), MatlabArray(S), MatlabArray(vt.conj().T)

def qr(a: MatlabArray):
    data = _to_data(a)
    if scipy.sparse.issparse(data):
         if data.shape[0] * data.shape[1] > 100_000_000:
             print(f"{tr('console_warning_prefix')}: {tr('warning_dense_qr_large_sparse')}")
         data = data.toarray() 
    q, r = scipy.linalg.qr(data)
    return MatlabArray(q), MatlabArray(r)

def lu(a: MatlabArray):
    data = _to_data(a)
    if scipy.sparse.issparse(data):
        data = data.toarray()
    p, l, u = scipy.linalg.lu(data)
    return MatlabArray(l), MatlabArray(u), MatlabArray(p)

def chol(a: MatlabArray, lower=False):
    data = _to_numpy(a)
    try:
        return MatlabArray(scipy.linalg.cholesky(data, lower=lower))
    except scipy.linalg.LinAlgError:
        raise ValueError("Matrix must be positive definite.")

def hess(a: MatlabArray):
    data = _to_numpy(a)
    H, Q = scipy.linalg.hessenberg(data, calc_q=True)
    return MatlabArray(Q), MatlabArray(H)

def schur(a: MatlabArray, output='real'):
    data = _to_numpy(a)
    T, Z = scipy.linalg.schur(data, output=output)
    return MatlabArray(Z), MatlabArray(T)

# -----------------------------------------------------------------------------
# MATRIX FUNCTIONS
# -----------------------------------------------------------------------------

def expm(a: MatlabArray) -> MatlabArray:
    data = _to_data(a)
    if scipy.sparse.issparse(data):
        return MatlabArray(scipy.sparse.linalg.expm(data))
    return MatlabArray(scipy.linalg.expm(data))

def sqrtm(a: MatlabArray) -> MatlabArray:
    data = _to_numpy(a)
    return MatlabArray(scipy.linalg.sqrtm(data))

# -----------------------------------------------------------------------------
# ITERATIVE SOLVERS
# -----------------------------------------------------------------------------

def gmres(A, b, x0=None, tol=1e-5, maxiter=None):
    A_data = _to_data(A)
    b_data = _to_data(b).flatten()
    x0_data = _to_data(x0).flatten() if x0 is not None else None
    
    x, info = scipy.sparse.linalg.gmres(A_data, b_data, x0=x0_data, rtol=tol, maxiter=maxiter)
    
    if info > 0:
        print(f"{tr('console_warning_prefix')}: {tr('warning_gmres_no_converge', info=info)}")
    return MatlabArray(x.reshape(-1, 1))

def pcg(A, b, x0=None, tol=1e-5, maxiter=None):
    A_data = _to_data(A)
    b_data = _to_data(b).flatten()
    x0_data = _to_data(x0).flatten() if x0 is not None else None
    
    x, info = scipy.sparse.linalg.cg(A_data, b_data, x0=x0_data, rtol=tol, maxiter=maxiter)
    
    if info > 0:
        print(f"{tr('console_warning_prefix')}: {tr('warning_pcg_no_converge', info=info)}")
    return MatlabArray(x.reshape(-1, 1))

def null(a: MatlabArray):
    data = _to_numpy(a)
    u, s, vh = scipy.linalg.svd(data)
    tol = max(data.shape) * np.finfo(float).eps * np.max(s)
    r = np.sum(s > tol)
    return MatlabArray(vh[r:,:].conj().T)

def orth(a: MatlabArray):
    data = _to_numpy(a)
    u, s, vh = scipy.linalg.svd(data)
    tol = max(data.shape) * np.finfo(float).eps * np.max(s)
    r = np.sum(s > tol)
    return MatlabArray(u[:,:r])
