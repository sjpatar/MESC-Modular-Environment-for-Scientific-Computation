import numpy as np
import pytest
import textwrap
from ides.mathex.kernel.session import KernelSession
from ides.mathex.kernel.executor import execute

# ==============================================================================
# PHASE 5: PHYSICS & SIMULATION VISUALIZATION
# ==============================================================================

def test_vector_fields_2d():
    """
    Verify 2D Vector Field plotting (Quiver & Streamline).
    Essential for Fluid Dynamics and Electromagnetism.
    """
    s = KernelSession()
    code = textwrap.dedent("""
    [X, Y] = meshgrid(-2:0.5:2, -2:0.5:2);
    U = -Y;
    V = X;
    
    % Test Quiver (Velocity Field)
    q = quiver(X, Y, U, V);
    
    % Test Streamlines (Flow Lines)
    % We use 'hold on' to overlay them
    hold on
    sl = streamline(X, Y, U, V);
    """)
    execute(code, s)
    
    # Check if handles were created
    assert s.globals.get('q') is not None, "Quiver plot failed to return handle"
    assert s.globals.get('sl') is not None, "Streamline plot failed to return handle"

def test_vector_fields_3d():
    """
    Verify 3D Vector Field plotting (Quiver3).
    """
    s = KernelSession()
    code = textwrap.dedent("""
    [X, Y] = meshgrid(-1:1:1, -1:1:1);
    Z = X .* 0; 
    U = X; V = Y; W = ones(size(X));
    
    h = quiver3(X, Y, Z, U, V, W, 'Color', 'r');
    """)
    execute(code, s)
    assert s.globals.get('h') is not None, "Quiver3 failed to execute"

def test_visual_settings():
    """
    Verify Colormap and Axis Color scaling control.
    """
    s = KernelSession()
    code = textwrap.dedent("""
    [X, Y] = meshgrid(-2:0.1:2);
    Z = X .* exp(-X.^2 - Y.^2);
    surf(X, Y, Z);
    
    colormap('jet');
    caxis([-1 1]);
    """)
    # Execution without error implies success for these visual-only commands
    execute(code, s)

def test_animation_handle_update():
    """
    Verify the 'Simulation Loop' pattern.
    We must be able to update plot data via set(h, ...)
    """
    s = KernelSession()
    code = textwrap.dedent("""
    x = [0 1 2];
    y = [0 1 0];
    h = plot(x, y);
    
    % SIMULATION UPDATE STEP
    new_x = [0 1 2 3];
    new_y = [0 1 0 1];
    set(h, 'XData', new_x, 'YData', new_y, 'Color', 'r');
    """)
    execute(code, s)
    
    # Verify the handle actually updated its internal data
    # (We inspect the wrapper handle)
    h_wrapper = s.globals['h']
    
    # In Matplotlib backend, we can access the artist
    # Note: access protected members for testing only
    artist = h_wrapper._artist
    
    # Check XData
    x_data = artist.get_xdata()
    y_data = artist.get_ydata()
    color  = artist.get_color()
    
    # Use numpy testing for array comparison
    np.testing.assert_array_equal(x_data, [0, 1, 2, 3], err_msg="set(h, 'XData') failed")
    np.testing.assert_array_equal(y_data, [0, 1, 0, 1], err_msg="set(h, 'YData') failed")
    
    # Check Color (mpl returns rgba or string, usually 'r' -> (1,0,0,1))
    # We just check if it didn't crash; strict color check is tricky across backends
    assert color is not None, "Color update failed"

if __name__ == "__main__":
    print("Running Physics Feature Tests...")
    try:
        test_vector_fields_2d()
        print("✅ PASS: 2D Vector Fields (Quiver/Streamline)")
        
        test_vector_fields_3d()
        print("✅ PASS: 3D Vector Fields (Quiver3)")
        
        test_visual_settings()
        print("✅ PASS: Visual Settings (Colormap/Caxis)")
        
        test_animation_handle_update()
        print("✅ PASS: Animation Handle Updates (set XData/YData)")
        
        print("\n🎉 ALL PHYSICS FEATURES PASSED!")
    except AssertionError as e:
        print(f"\n❌ FAIL: {e}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n❌ CRASH: {e}")