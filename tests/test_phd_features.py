import numpy as np
import pytest
import textwrap
from ides.mathex.kernel.session import KernelSession
from ides.mathex.kernel.executor import execute

# ==============================================================================
# PHASE 1: LANGUAGE TESTS (Control Flow)
# ==============================================================================

def test_try_catch():
    """Verify try/catch blocks catch errors and execute the recovery block."""
    s = KernelSession()
    code = textwrap.dedent("""
    x = 0;
    try
        % This function does not exist, so it should throw an error
        this_function_fails(); 
    catch
        x = 100;
    end
    """)
    execute(code, s)
    assert s.globals["x"] == 100, "Failed to enter catch block on error"

def test_switch_case():
    """Verify switch/case/otherwise logic."""
    s = KernelSession()
    code = textwrap.dedent("""
    val = 2;
    result = 0;
    switch val
        case 1
            result = 10;
        case 2
            result = 20;
        otherwise
            result = 30;
    end
    """)
    execute(code, s)
    assert s.globals["result"] == 20, "Switch/Case failed to match case 2"

def test_switch_otherwise():
    """Verify switch falls through to otherwise."""
    s = KernelSession()
    code = textwrap.dedent("""
    val = 99;
    result = 0;
    switch val
        case 1
            result = 10;
        otherwise
            result = 30;
    end
    """)
    execute(code, s)
    assert s.globals["result"] == 30, "Switch failed to hit otherwise block"

# ==============================================================================
# PHASE 2: MATH & PHYSICS TESTS (Solvers)
# ==============================================================================

def test_interpolation():
    """Verify interp1 and griddata."""
    s = KernelSession()
    
    # 1D Interpolation (Linear)
    # Points: (1,1), (2,4), (3,9) -> x=1.5 should be 2.5
    code1 = "y = interp1([1 2 3], [1 4 9], 1.5, 'linear');"
    execute(code1, s)
    # Now that MatlabArray has __abs__, this works
    assert abs(s.globals["y"] - 2.5) < 1e-9, "interp1 linear failed"

    # 1D Interpolation (Spline/Cubic)
    code2 = "y2 = interp1([1 2 3], [1 4 9], 1.5, 'spline');"
    execute(code2, s)
    # 1.5^2 = 2.25
    assert abs(s.globals["y2"] - 2.25) < 0.1, "interp1 spline accuracy failed"

def test_optimization_fminsearch():
    """Verify fminsearch (Nelder-Mead)."""
    s = KernelSession()
    # Minimize (x-3)^2 + 5. Minimum is at x=3.
    code = "x = fminsearch(@(x) (x-3)^2 + 5, 0);"
    execute(code, s)
    assert abs(s.globals["x"] - 3.0) < 1e-4, "fminsearch failed to find minimum"

def test_pdepe_heat_equation():
    """
    Verify pdepe (Partial Differential Equation Solver).
    Solving Heat Equation: du/dt = d2u/dx2
    """
    s = KernelSession()
    
    # We define the physics functions in Python and inject them
    def pdefun(x, t, u, dudx):
        return 1.0, dudx, 0.0

    def icfun(x):
        return 1.0

    def bcfun(xl, ul, xr, ur, t):
        return 0, 1, 0, 1

    s.globals['my_pde'] = pdefun
    s.globals['my_ic']  = icfun
    s.globals['my_bc']  = bcfun
    
    code = textwrap.dedent("""
    m = 0;
    x = linspace(0, 1, 20);
    t = linspace(0, 0.1, 5);
    sol = pdepe(m, my_pde, my_ic, my_bc, x, t);
    final_temp = mean(sol(end, :));
    """)
    execute(code, s)
    
    final_temp = float(s.globals['final_temp'])
    assert abs(final_temp - 1.0) < 1e-2, f"PDE Heat conservation failed. Temp: {final_temp}"

def test_sparse_eigs():
    """Verify finding sparse eigenvalues."""
    s = KernelSession()
    code = textwrap.dedent("""
    % Create a sparse diagonal matrix with values 1 to 100
    N = 100;
    i = 1:N;
    A = sparse(i, i, i);
    
    % Find smallest magnitude eigenvalue (should be 1)
    [V, D] = eigs(A, 1, 0); 
    """)
    execute(code, s)
    
    # D should contain the eigenvalue 1.0 (approx)
    D = s.globals['D']
    if D.shape == (1, 1):
        val = float(D)
    else:
        # If it returns a matrix, grab the first element
        val = float(D[0,0])
        
    assert abs(val - 1.0) < 1e-5, f"eigs failed. Expected 1.0, got {val}"

def test_signal_processing():
    """Verify FFT shift."""
    s = KernelSession()
    code = textwrap.dedent("""
    x = [1 2 3 4];
    y = fftshift(x);
    """)
    execute(code, s)
    # [1 2 3 4] -> fftshift -> [3 4 1 2]
    res = list(s.globals['y']._data.flatten())
    assert res == [3, 4, 1, 2], "fftshift logic failed"

# ==============================================================================
# PHASE 3: NEW PHD FEATURES (Multi-case, Struct Arrays, Advanced Physics)
# ==============================================================================

def test_switch_multicase():
    """Verify switch supports cell arrays: case {1, 2}."""
    s = KernelSession()
    code = textwrap.dedent("""
    val = 2;
    res = 0;
    switch val
        case {1, 2}
            res = 100;
        case {3, 4}
            res = 200;
        otherwise
            res = 300;
    end
    """)
    execute(code, s)
    assert s.globals["res"] == 100, "Switch Multi-Case ({1, 2}) failed to match 2"

def test_struct_array():
    """Verify struct arrays created via cell distribution."""
    s = KernelSession()
    code = textwrap.dedent("""
    % Create a 1x2 struct array
    s = struct('id', {101, 102}, 'val', 5);
    
    v1 = s(1).id;
    v2 = s(2).id;
    
    % Check scalar distribution (val=5 should be in both)
    v3 = s(1).val;
    v4 = s(2).val;
    """)
    execute(code, s)
    
    assert s.globals["v1"] == 101, "Struct Array s(1).id incorrect"
    assert s.globals["v2"] == 102, "Struct Array s(2).id incorrect"
    assert s.globals["v3"] == 5,   "Struct Array scalar replication failed"

def test_pdepe_geometry():
    """
    Verify pdepe with m=2 (Spherical Coordinates).
    Just verifies execution and basic output shape/validity.
    """
    s = KernelSession()
    
    # Inject physics
    s.globals['my_pde'] = lambda x,t,u,dudx: (1.0, dudx, 0.0) # Diffusion
    s.globals['my_ic']  = lambda x: 1.0 if x < 0.5 else 0.0
    s.globals['my_bc']  = lambda xl,ul,xr,ur,t: (0,1,0,1) # Zero flux
    
    code = textwrap.dedent("""
    m = 2; % Spherical
    x = linspace(0, 1, 20);
    t = linspace(0, 0.05, 5);
    sol = pdepe(m, my_pde, my_ic, my_bc, x, t);
    val = sol(end, 1);
    """)
    execute(code, s)
    # Check if we got a result
    assert s.globals['val'] is not None, "pdepe Spherical failed to run"

def test_fmincon_constrained():
    """
    Verify fmincon with nonlinear constraints.
    Minimize (x-1)^2 + (y-2)^2 s.t. x^2 + y^2 <= 1
    Minimum should be on the boundary of the unit circle closest to (1,2).
    """
    s = KernelSession()
    
    # Objective: Distance to (1, 2)
    def obj(x):
        # x is MatlabArray
        x_val = x._data.flatten()
        return (x_val[0]-1)**2 + (x_val[1]-2)**2
        
    # Constraints: Unit Circle
    def nlc(x):
        x_val = x._data.flatten()
        c = x_val[0]**2 + x_val[1]**2 - 1.0 # c <= 0
        ceq = []
        return c, ceq

    s.globals['obj'] = obj
    s.globals['nlc'] = nlc
    
    code = textwrap.dedent("""
    x0 = [0; 0];
    x = fmincon(@obj, x0, [], [], [], [], [], [], @nlc);
    """)
    execute(code, s)
    
    res = s.globals['x']._data.flatten()
    # Expected: 1/sqrt(5), 2/sqrt(5) approx (0.447, 0.894)
    # Norm should be close to 1
    norm_res = np.linalg.norm(res)
    assert abs(norm_res - 1.0) < 1e-3, f"fmincon Constraint Violation: norm={norm_res}"
    assert res[0] > 0 and res[1] > 0, "fmincon found wrong quadrant"

# ==============================================================================
# PHASE 4: OOP & CLASSES (New for Physics Simulation Engines)
# ==============================================================================

def test_oop_basic():
    """Verify classdef, properties, constructor, and methods."""
    s = KernelSession()
    
    # Define a 'Particle' class typical for physics engines
    code = textwrap.dedent("""
    classdef Particle
        properties
            Mass
            X
            V
        end
        methods
            function obj = Particle(m, x, v)
                obj.Mass = m;
                obj.X = x;
                obj.V = v;
            end
            
            function K = kineticEnergy(obj)
                K = 0.5 * obj.Mass * obj.V^2;
            end
            
            function update(obj, dt)
                % Simple Euler integration
                obj.X = obj.X + obj.V * dt;
            end
        end
    end

    p = Particle(10, 0, 5);
    
    % Test Method Call
    E = p.kineticEnergy();
    
    % Test State Update (mutability check)
    p.update(2);
    pos = p.X;
    """)
    execute(code, s)
    
    assert s.globals["E"] == 125.0, "OOP Method call (kineticEnergy) failed"
    assert s.globals["pos"] == 10.0, "OOP State update (X = 0 + 5*2) failed"

def test_oop_property_access():
    """Verify direct property read/write access."""
    s = KernelSession()
    code = textwrap.dedent("""
    classdef DataContainer
        properties
            Value
        end
        methods
            function obj = DataContainer(v)
                obj.Value = v;
            end
        end
    end
    
    d = DataContainer(42);
    
    % Read
    v1 = d.Value;
    
    % Write
    d.Value = 100;
    v2 = d.Value;
    """)
    execute(code, s)
    
    assert s.globals["v1"] == 42, "OOP Property Read failed"
    assert s.globals["v2"] == 100, "OOP Property Write failed"


if __name__ == "__main__":
    print("Running Mathex PhD Feature Tests...")
    try:
        # Phase 1
        test_try_catch()
        print("✅ PASS: Try/Catch")
        test_switch_case()
        test_switch_otherwise()
        print("✅ PASS: Switch/Case")
        
        # Phase 2
        test_interpolation()
        print("✅ PASS: Interpolation")
        test_optimization_fminsearch()
        print("✅ PASS: Optimization (Unconstrained)")
        test_pdepe_heat_equation()
        print("✅ PASS: PDE Solver (Slab)")
        test_sparse_eigs()
        print("✅ PASS: Sparse Eigenvalues (eigs)")
        test_signal_processing()
        print("✅ PASS: Signal Processing")
        
        # Phase 3
        test_switch_multicase()
        print("✅ PASS: Switch Multi-Case")
        test_struct_array()
        print("✅ PASS: Struct Arrays")
        test_pdepe_geometry()
        print("✅ PASS: PDE Solver (Spherical)")
        test_fmincon_constrained()
        print("✅ PASS: Optimization (Constrained fmincon)")
        
        # Phase 4 (NEW)
        test_oop_basic()
        print("✅ PASS: OOP Class Definition & Methods")
        test_oop_property_access()
        print("✅ PASS: OOP Property Read/Write")
        
        print("\n🎉 ALL PHD FEATURES PASSED (PHASE 1-4)!")
    except AssertionError as e:
        print(f"\n❌ FAIL: {e}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n❌ CRASH: {e}")