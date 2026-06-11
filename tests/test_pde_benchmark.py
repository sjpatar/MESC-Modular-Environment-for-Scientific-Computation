import pytest
import time
import numpy as np
import sys
import os

# Import the solver directly
from ides.mathex.toolbox.pde import pdepe

# ==========================================================
# TEST FIXTURES: Heat Equation Definition
# ==========================================================

def heat_pde(x, t, u, dudx):
    # Heat Eq: du/dt = d^2u/dx^2 => c=1, f=dudx, s=0
    # Note: Returns (c, f, s)
    # This function must be vector-safe (accept arrays for x, u, dudx)
    return 1.0, dudx, 0.0

def heat_ic(x):
    # Step function: 1 if x < 0.5 else 0
    if x < 0.5:
        return 1.0
    return 0.0

def heat_bc(xl, ul, xr, ur, t):
    # Left: Insulated (f=0) -> p=0, q=1
    # Right: Fixed Temp (u=0) -> p=ur, q=0
    return 0.0, 1.0, ur, 0.0

# ==========================================================
# PERFORMANCE TESTS
# ==========================================================

def test_pde_solver_speed():
    """
    Stress test for pdepe solver.
    Requires Numba optimization to pass within strict time limits.
    Target: N=1000 grid points should take < 2.0 seconds (excluding compilation).
    """
    # 1. Setup Heavy Grid
    N_points = 1000
    x = np.linspace(0, 1, N_points)
    t = np.linspace(0, 0.1, 20) # 20 time steps
    m = 0

    print(f"\n[Benchmark] Warming up JIT compiler (tiny run)...")
    # --- WARMUP PHASE ---
    # We run a tiny problem to force Numba to compile the functions.
    # This ensures the measured time below is purely execution time.
    pdepe(0, heat_pde, heat_ic, heat_bc, np.linspace(0,1,10), [0, 0.01])
    print("[Benchmark] Warmup complete. Starting Stress Test (N=1000)...")

    # 2. Measure Execution Time
    start_time = time.perf_counter()
    
    # Run Solver (Compiled & Ready)
    sol = pdepe(m, heat_pde, heat_ic, heat_bc, x, t)
    
    duration = time.perf_counter() - start_time
    
    # 3. Validation (Sanity Check)
    u_final = sol._data[-1, :]
    assert abs(u_final[-1]) < 1e-3, "Solver failed to satisfy boundary condition u(1)=0"
    
    # 4. Performance Assertion
    print(f"[Benchmark] Execution Time: {duration:.4f}s")
    
    # STRICT THRESHOLD:
    # Pure Python:   ~10-15s
    # Numba (Cold):  ~4-7s (Compilation + Exec)
    # Numba (Warm):  ~0.5-1.5s (Exec only)
    failure_message = (
        f"Too Slow! took {duration:.2f}s (Limit: 2.0s). "
        "Numba JIT vectorization is likely not active or efficient."
    )
    assert duration < 2.0, failure_message

if __name__ == "__main__":
    pytest.main(["-s", __file__])