# verify_updates.py
import numpy as np
import scipy.sparse
from shared.symbolic_core.arrays import MatlabArray
from shared.symbolic_core.linalg import expm, eig, gmres, inv
from ides.mathex.language.builtins import size, length

def test_step1_builtins():
    print("--- Testing Step 1: Builtin Fixes ---")
    A = MatlabArray(np.zeros((10, 5)))
    
    # Test size() returns MatlabArray
    sz = size(A)
    print(f"size(A): {sz} (Type: {type(sz)})")
    
    if not isinstance(sz, MatlabArray):
        print("❌ FAIL: size() returned wrong type!")
    else:
        print("✅ PASS: size() returns MatlabArray")

    # Test compatibility (creating zeros from size)
    try:
        # If size() returns MatlabArray, we should be able to use its data
        dims = sz._data
        print(f"✅ PASS: Data accessible: {dims}")
    except Exception as e:
        print(f"❌ FAIL: checking data access: {e}")

def test_step2_physics():
    print("\n--- Testing Step 2: Physics Engine ---")
    
    # 1. Matrix Exponential (Quantum Mechanics Check)
    # Pauli X matrix
    sig_x = MatlabArray([[0, 1], [1, 0]])
    # e^(i * pi * sigma_x) should be -I
    U = expm(MatlabArray(1j * np.pi * sig_x._data))
    print(f"expm(i*pi*X) [Should be approx -I]:\n{U}")
    
    # 2. Sparse Eigenvalues (Ground State Check)
    print("\n[Testing Sparse Eig]")
    # Create large sparse diagonal matrix
    N = 100
    # [FIX] Added dtype=float to silence SciPy warning
    D = scipy.sparse.diags(np.arange(1, N+1), dtype=float) 
    S = MatlabArray(D)
    
    # Find 2 smallest eigenvalues (should be 1 and 2)
    # We use sigma=0 to find eigenvalues near 0
    try:
        V, D_eig = eig(S, k=2, sigma=0.01)
        print(f"✅ PASS: Found Sparse Eigenvalues near 0:\n{np.diag(D_eig._data)}")
    except Exception as e:
        print(f"❌ FAIL: Sparse eig crashed: {e}")

    # 3. GMRES (Iterative Solver Check)
    print("\n[Testing GMRES]")
    A = MatlabArray(np.array([[3, 2], [2, 6]]))
    b = MatlabArray(np.array([5, 8])) # Solution is [1, 1]
    x = gmres(A, b)
    print(f"GMRES Solution (Target [1; 1]):\n{x}")

if __name__ == "__main__":
    test_step1_builtins()
    test_step2_physics()

def test_step3_integration():
    print("\n--- Testing Step 3: Integration ---")
    # [FIX] Updated import path from 'mathex.math.toolbox' to 'mathex.toolbox'
    from ides.mathex.toolbox import integral, ode45
    
    # 1. Numerical Integration (Area under x^2 from 0 to 1 = 1/3)
    res = integral(lambda x: x**2, 0, 1)
    print(f"integral(x^2, 0, 1): {res} (Expected ~0.333)")
    
    # 2. ODE Event (Simple harmonic oscillator)
    # Stop when y=0 (going downwards)
    def osc(t, y): return [y[1], -y[0]] # y'' = -y
    
    def event_zero(t, y): return y[0]
    event_zero.terminal = True
    event_zero.direction = -1
    
    # Start at [0, 1], should complete half cycle and stop at pi
    sol = ode45(osc, [0, 10], [0, 1], events=[event_zero])
    print(f"ODE Event time: {sol.te} (Expected ~3.14)")