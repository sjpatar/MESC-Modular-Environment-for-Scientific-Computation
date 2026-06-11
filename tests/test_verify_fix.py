"""
Verification Test.
Checks if mpl_backend.py is TRULY fixed.
"""
import pytest
from shared.plotting_engine.mpl_backend import HeadlessPlotWidget

def test_trap_fallback():
    print("\n--- Testing for Silent Fallback Bug ---")
    widget = HeadlessPlotWidget()
    
    try:
        # We request a NON-EXISTENT projection.
        # IF FIXED: This SHOULD raise a ValueError.
        # IF BUGGY: This will silently return a 2D axis.
        ax = widget.new_axes(projection='GARBAGE_PROJECTION')
        
        # If we get here, the bug is STILL THERE.
        if ax.name == 'rectilinear':
            pytest.fail("FAIL: The code silently fell back to 2D! The try...except block is still in mpl_backend.py.")
        else:
            pytest.fail(f"FAIL: Weird behavior. Got axis: {ax.name}")
            
    except ValueError:
        print("SUCCESS: The code correctly raised an error for bad projection.")
        print("The try...except block has been removed.")

if __name__ == "__main__":
    pytest.main(["-s", __file__])