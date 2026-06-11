import pytest
import numpy as np
from shared.plotting_engine.state import plot_manager
# [FIX] Import specific functions to avoid module/function name collision
from shared.plotting_engine.figure import figure, close, gcf, clf
from shared.plotting_engine import plot2d

# Ensure we use the headless backend for testing (no GUI windows)
from shared.plotting_engine.engine import PlotEngine
PlotEngine._mode = "test"

def setup_function():
    """Reset figure before each test."""
    close('all')
    figure(1)

# =================================================================
# TEST 1: The Legend Bug
# =================================================================
def test_legend_assignment():
    """
    Reproduces the 'No legend at all' issue.
    If ax.legend(labels) is called without handles, it often fails silently.
    """
    # 1. [FIX] Turn HOLD ON so multiple lines are kept
    plot_manager.hold(True)

    # 2. Create a simple plot with 2 lines
    plot2d.plot([1, 2, 3], [1, 2, 3]) # Line 1
    plot2d.plot([1, 2, 3], [3, 2, 1]) # Line 2
    
    # 3. Try to create a legend
    # This should now work because we have 2 lines on the axes
    plot2d.legend("Line A", "Line B")
    
    # 4. Verify
    fig = gcf()
    ax = fig.gca()
    leg = ax.get_legend()
    
    # ASSERTIONS
    assert leg is not None, "❌ FAILURE: Legend object was not created."
    
    texts = [t.get_text() for t in leg.get_texts()]
    assert texts == ["Line A", "Line B"], f"❌ FAILURE: Labels incorrect. Got {texts}"
    print("\n✅ Legend Test Passed")

# =================================================================
# TEST 2: The CLF / 3D Layout Bug
# =================================================================
def test_clf_3d_reset():
    """
    Reproduces the 'clf stops working' issue.
    When switching from 3D to 2D, the layout engine often gets stuck.
    """
    # 1. Create a 3D Plot (Forces '3d' layout mode)
    fig = gcf()
    # Manually add 3D axes to simulate 'surf'
    ax = fig.add_subplot(1, 1, 1, projection='3d')
    assert len(fig.axes) == 1
    
    # 2. Call CLF
    clf()
    
    # 3. Verify Canvas is empty
    assert len(fig.axes) == 0, f"❌ FAILURE: Axes not cleared. Count: {len(fig.axes)}"
    
    # 4. Verify we can plot 2D again (Layout engine check)
    try:
        plot2d.plot([1, 2], [1, 2])
        # This will crash if layout engine is still stuck in 3D mode
        if hasattr(fig.canvas, 'draw'):
            fig.canvas.draw() 
    except Exception as e:
        pytest.fail(f"❌ FAILURE: Layout engine crashed on re-plot: {e}")
        
    print("✅ CLF Test Passed")

if __name__ == "__main__":
    # Allow running directly with python
    setup_function()
    try: test_legend_assignment()
    except AssertionError as e: print(e)
    
    setup_function()
    try: test_clf_3d_reset()
    except AssertionError as e: print(e)