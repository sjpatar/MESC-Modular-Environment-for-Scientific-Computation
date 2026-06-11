import pytest
import numpy as np
import textwrap
from ides.mathex.kernel.session import KernelSession
from ides.mathex.kernel.executor import execute

# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def session():
    """Provides a fresh KernelSession for each test function."""
    return KernelSession()

def run_code(session, code):
    """Helper to execute code and strip indentation."""
    execute(textwrap.dedent(code), session)

def get_var(session, name):
    """Helper to retrieve a variable's raw data."""
    val = session.globals[name]
    # Unwrap MatlabArray if present
    if hasattr(val, '_data'):
        return val._data
    return val

# ==============================================================================
# 1. CORE LANGUAGE & SYNTAX
# ==============================================================================

def test_arithmetic_and_assignment(session):
    run_code(session, "x = 2 + 3;")
    assert get_var(session, "x") == 5

def test_matrix_construction(session):
    run_code(session, """
    A = [1 2; 3 4]; 
    y = A(2, 1);
    """)
    assert get_var(session, "y") == 3

def test_colon_indexing(session):
    run_code(session, """
    v = 1:10; 
    y = v(end);
    """)
    assert get_var(session, "y") == 10

def test_for_loop(session):
    run_code(session, """
    s = 0;
    for i = 1:5
        s = s + i;
    end
    """)
    assert get_var(session, "s") == 15

def test_switch_case(session):
    run_code(session, """
    val = 2;
    res = 0;
    switch val
        case 1
            res = 10;
        case 2
            res = 20;
        otherwise
            res = 30;
    end
    """)
    assert get_var(session, "res") == 20

def test_try_catch(session):
    run_code(session, """
    flag = 0;
    try
        error('Something bad');
    catch
        flag = 1;
    end
    """)
    assert get_var(session, "flag") == 1

# ==============================================================================
# 2. LINEAR ALGEBRA & SPARSE MATRICES
# ==============================================================================

def test_matrix_inverse(session):
    run_code(session, """
    A = [1 2; 3 4];
    I = inv(A) * A;
    chk = I(1,1);
    """)
    # Floating point comparison
    assert get_var(session, "chk") == pytest.approx(1.0)

def test_sparse_creation_and_arithmetic(session):
    run_code(session, """
    i = [1 2 3]; j = [1 2 3]; v = [10 20 30];
    S = sparse(i, j, v, 5, 5);
    
    % Test Arithmetic
    S2 = S * 2;
    val = S2(1,1);
    """)
    assert get_var(session, "val") == 20

def test_linear_solver(session):
    run_code(session, """
    A = [3 2; 2 6];
    b = [5; 8];
    x = A \\ b;  % Should be [1; 1]
    val = x(1);
    """)
    assert get_var(session, "val") == pytest.approx(1.0)

# ==============================================================================
# 3. PHD FEATURES: SOLVERS & OPTIMIZATION
# ==============================================================================

def test_fminsearch(session):
    # [FIX] Use float() to safely handle MatlabArray inputs
    session.globals['cost_fun'] = lambda x: (float(x) - 3)**2 + 5
    
    run_code(session, "x = fminsearch(@cost_fun, 0);")
    assert get_var(session, "x") == pytest.approx(3.0, abs=1e-4)

def test_fmincon_constrained(session):
    # Minimize x^2 + y^2 subject to x + y = 1
    # [FIX] Access ._data.flatten() because x comes in as a MatlabArray (2D row vector)
    def con_obj(x): 
        d = x._data.flatten()
        return float(d[0])**2 + float(d[1])**2
        
    session.globals['con_obj'] = con_obj
    
    run_code(session, """
    x0 = [0.5; 0.5];
    Aeq = [1 1]; beq = 1;
    x = fmincon(@con_obj, x0, [], [], Aeq, beq);
    val = x(1); % Expected 0.5
    """)
    
    # [FIX] Unwrap 'val' safely using .item() to avoid deprecation warning
    val_data = get_var(session, "val")
    res_val = val_data.item() if hasattr(val_data, 'item') else float(val_data)
    assert res_val == pytest.approx(0.5, abs=1e-3)

def test_ode45_solver(session):
    # Simple harmonic oscillator: y'' = -y
    # [FIX] Access ._data.flatten() to handle input vector correctly
    def osc(t, y): 
        d = y._data.flatten()
        return [d[1], -d[0]] 
        
    session.globals['osc'] = osc
    
    run_code(session, """
    tspan = [0 6.3]; % approx 2*pi
    y0 = [0; 1];
    [t, y] = ode45(@osc, tspan, y0);
    final = y(end, 1); % Should return to approx 0
    """)
    
    # [FIX] Unwrap 'final' safely
    final_data = get_var(session, "final")
    final_val = final_data.item() if hasattr(final_data, 'item') else float(final_data)
    assert final_val == pytest.approx(0.0, abs=0.2)

def test_pdepe_heat_equation(session):
    # Inject physics helpers
    # These simple lambdas work because scalar math on MatlabArrays is supported
    session.globals['pde_eqn'] = lambda x,t,u,dudx: (1.0, dudx, 0.0)
    session.globals['pde_ic'] = lambda x: 1.0
    session.globals['pde_bc'] = lambda xl,ul,xr,ur,t: (0,1,0,1)

    run_code(session, """
    m = 0;
    x = linspace(0, 1, 10);
    t = [0 0.1];
    sol = pdepe(m, @pde_eqn, @pde_ic, @pde_bc, x, t);
    temp = sol(end, 5); % Should remain ~1.0
    """)
    # [FIX] Unwrap
    temp_data = get_var(session, "temp")
    temp_val = temp_data.item() if hasattr(temp_data, 'item') else float(temp_data)
    assert temp_val == pytest.approx(1.0, abs=0.1)

# ==============================================================================
# 4. PHYSICS & ENGINEERING
# ==============================================================================

def test_physical_constants(session):
    run_code(session, "c = physconst('LightSpeed');")
    assert get_var(session, "c") == 299792458.0

def test_unit_conversion(session):
    run_code(session, """
    T_f = 212;
    T_c = convtemp(T_f, 'F', 'C');
    """)
    assert get_var(session, "T_c") == pytest.approx(100.0)

def test_vector_fields(session):
    run_code(session, """
    [X, Y] = meshgrid(-2:2, -2:2);
    U = -Y; V = X;
    q = quiver(X, Y, U, V);
    """)
    # Just check if the handle exists
    assert get_var(session, "q") is not None

# ==============================================================================
# 5. OOP SUPPORT
# ==============================================================================

def test_class_definition(session):
    run_code(session, """
    classdef Point
        properties
            X
            Y
        end
        methods
            function obj = Point(x, y)
                obj.X = x;
                obj.Y = y;
            end
            function r = norm(obj)
                r = sqrt(obj.X^2 + obj.Y^2);
            end
        end
    end
    
    p = Point(3, 4);
    d = p.norm();
    """)
    # [FIX] Unwrap
    d_data = get_var(session, "d")
    d_val = d_data.item() if hasattr(d_data, 'item') else float(d_data)
    assert d_val == pytest.approx(5.0)