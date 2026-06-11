import pytest
import numpy as np
import scipy.sparse
from shared.symbolic_core.arrays import MatlabArray, sparse, full
from shared.symbolic_core.linalg import inv, det

def test_sparse_creation():
    # sparse(i,j,v)
    i, j, v = [1, 2], [1, 2], [10, 20]
    S = sparse(i, j, v, 5, 5)
    
    assert S.is_sparse
    assert S.shape == (5, 5)
    assert S.nnz == 2
    # Check data (0-based internal check)
    assert S._data[0,0] == 10
    assert S._data[1,1] == 20

def test_sparse_to_full():
    S = sparse([1], [1], [5], 2, 2)
    F = full(S)
    
    assert not F.is_sparse
    assert isinstance(F._data, np.ndarray)
    assert F._data[0,0] == 5

def test_sparse_arithmetic():
    S = sparse([1], [1], [10], 2, 2)
    D = full(S)
    
    # Sparse + Dense -> Dense (usually)
    # Depending on your implementation, check result
    Res = S * 2
    assert Res.is_sparse
    assert Res._data[0,0] == 20

def test_linear_solve():
    # Identity matrix 2x2
    S = sparse([1, 2], [1, 2], [1, 1], 2, 2)
    b = MatlabArray([[2], [3]])
    
    # Solve S*x = b -> x = b
    x = S.mldivide(b)
    
    assert x._data[0,0] == 2
    assert x._data[1,0] == 3