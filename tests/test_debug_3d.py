"""
Debug Test for 3D Plotting Issues.
Run this with: pytest tests/test_debug_3d.py -s
"""
import sys
import pytest
import matplotlib.pyplot as plt
from matplotlib.axes import Axes

# 1. Test Environment Dependencies
def test_environment_has_mplot3d():
    print("\n--- [1] Checking Environment ---")
    try:
        import mpl_toolkits.mplot3d
        print("SUCCESS: mpl_toolkits.mplot3d is importable.")
    except ImportError as e:
        pytest.fail(f"CRITICAL: Cannot import mpl_toolkits.mplot3d. Reason: {e}")

# 2. Test Backend Logic Directly (Bypassing State Manager)
def test_backend_direct_creation():
    print("\n--- [2] Checking Backend Widget ---")
    
    # Import the backend widget
    try:
        from shared.plotting_engine.mpl_backend import HeadlessPlotWidget
    except ImportError:
        pytest.fail("Could not import HeadlessPlotWidget from shared.plotting_engine.mpl_backend")

    widget = HeadlessPlotWidget()
    
    # Try to create 3D axes directly
    try:
        ax = widget.new_axes(projection='3d')
        print(f"Widget returned axes type: {type(ax)}")
        print(f"Axes name: {getattr(ax, 'name', 'unknown')}")
        
        # VERIFICATION
        assert ax.name == '3d', f"Expected '3d' axes, got '{ax.name}' (This is the 2D plane issue!)"
        print("SUCCESS: Backend created a valid 3D axis.")
        
    except Exception as e:
        pytest.fail(f"Backend crashed when requesting 3D axes: {e}")

# 3. Test Full Integration (plot3 command)
def test_plot3_integration():
    print("\n--- [3] Checking plot3() Integration ---")
    
    # Initialize Engine (FORCE test mode)
    # [FIX] Import 'close' directly to avoid the AttributeError
    from shared.plotting_engine import engine, plot3d, state, close
    
    # [FIX] Force Engine to Test Mode
    engine.PlotEngine.initialize("test", force=True)
    
    # [CRITICAL STEP] Factory Reset!
    # Destroy any old widgets created before we forced the engine mode.
    close('all') 
    
    # Run plot3
    try:
        plot3d.plot3([0, 1], [0, 1], [0, 1])
        
        # Get the current axes from the manager
        ax = state.plot_manager.gca()
        
        # DEBUG INFO
        fig_state = state.plot_manager._get_fig_state()
        print(f"Current Widget Type: {type(fig_state.widget)}")
        print(f"Resulting Axis Name: {ax.name}")

        # VERIFICATION
        assert ax.name == '3d', f"plot3() resulted in a '{ax.name}' axis instead of '3d'."
        print("SUCCESS: plot3() correctly produced a 3D plot.")
        
    except Exception as e:
        pytest.fail(f"plot3() failed: {e}")

if __name__ == "__main__":
    # Allow running directly with python
    sys.exit(pytest.main(["-s", __file__]))