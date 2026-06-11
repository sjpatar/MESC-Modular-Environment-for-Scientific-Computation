import pytest
import numpy as np
from shared.symbolic_core.arrays import MatlabArray
from ides.mathex.toolbox.signals import fft2, ifft2, filter

# =================================================================
# TEST 1: 2D FFT & Inverse (Roundtrip)
# =================================================================
def test_fft2_ifft2_roundtrip():
    """
    Verify that ifft2(fft2(X)) returns the original X.
    """
    # Create a random 10x10 matrix
    data = np.random.rand(10, 10)
    X = MatlabArray(data)
    
    # Forward Transform
    Y = fft2(X)
    assert isinstance(Y, MatlabArray)
    assert Y.shape == (10, 10)
    
    # Inverse Transform
    X_recovered = ifft2(Y)
    
    # Check correctness (Real parts should match, Imag should be near 0)
    diff = np.abs(X_recovered._data - data)
    assert np.all(diff < 1e-9), f"Roundtrip failed, max error: {np.max(diff)}"

def test_fft2_constant():
    """
    FFT2 of a constant matrix should only have a DC component at (0,0).
    """
    # 4x4 matrix of ones
    data = np.ones((4, 4))
    X = MatlabArray(data)
    
    Y = fft2(X)
    Y_data = Y._data
    
    # DC component (0,0) should be Sum(data) = 16
    assert np.isclose(Y_data[0, 0], 16.0)
    
    # All other components should be 0
    Y_data[0, 0] = 0
    assert np.all(np.abs(Y_data) < 1e-9)

# =================================================================
# TEST 2: Digital Filter (1D)
# =================================================================
def test_filter_moving_average():
    """
    Test a simple moving average filter: y[n] = 0.5*x[n] + 0.5*x[n-1]
    b = [0.5, 0.5], a = 1
    """
    x = MatlabArray([1.0, 1.0, 1.0, 1.0, 0.0])
    b = [0.5, 0.5]
    a = 1.0
    
    # Expected Output: 
    # n=0: 0.5*1 + 0 = 0.5
    # n=1: 0.5*1 + 0.5*1 = 1.0
    # ...
    # n=4: 0.5*0 + 0.5*1 = 0.5
    expected = np.array([0.5, 1.0, 1.0, 1.0, 0.5])
    
    y = filter(b, a, x)
    
    assert isinstance(y, MatlabArray)
    assert np.allclose(y._data.flatten(), expected)

def test_filter_impulse_response():
    """
    Filtering an impulse [1, 0, 0...] should yield coefficients 'b'.
    """
    x = np.zeros(5)
    x[0] = 1  # Impulse
    
    b = [0.1, 0.2, 0.3]
    a = 1
    
    y = filter(b, a, x)
    
    # The first 3 elements should match b
    res = y._data.flatten()[:3]
    assert np.allclose(res, b)

# =================================================================
# TEST 3: Type Compatibility
# =================================================================
def test_filter_inputs_as_matlab_arrays():
    """
    Ensure filter() accepts MatlabArrays for coefficients 'b' and 'a'.
    """
    b = MatlabArray([0.5, 0.5])
    a = MatlabArray([1.0])
    x = MatlabArray([10, 20, 30])
    
    y = filter(b, a, x)
    assert y.size == 3