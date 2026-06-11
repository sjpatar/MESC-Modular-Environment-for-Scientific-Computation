import pytest
import numpy as np
import threading
import time
from matplotlib.backends.backend_agg import FigureCanvasAgg as MPLFigureCanvasAgg

# Import the system under test
from shared.plotting_engine.animation import animatedline, addpoints, clearpoints, drawnow, comet
from shared.plotting_engine.state import plot_manager
from shared.plotting_engine.engine import PlotEngine
from shared.plotting_engine.figure import clf

# Force the engine into 'test' mode (Headless)
PlotEngine.initialize(mode="test", force=True)

def setup_function():
    """Reset state before each test."""
    clf()
    PlotEngine.initialize(mode="test", force=True)

def test_animatedline_creation():
    """Verify animatedline creates a valid handle."""
    h = animatedline()
    assert h.line is not None
    assert h.x == []
    assert h.y == []
    
    # Ensure it's attached to an axes
    ax = plot_manager.gca()
    assert h.line in ax.get_lines()

def test_animatedline_addpoints():
    """Verify adding points updates internal lists and matplotlib data."""
    h = animatedline()
    
    # 1. Add single point
    addpoints(h, 1, 1)
    assert h.x == [1.0]
    assert h.y == [1.0]
    
    # 2. Add multiple points
    addpoints(h, [2, 3], [4, 9])
    assert h.x == [1.0, 2.0, 3.0]
    assert h.y == [1.0, 4.0, 9.0]
    
    # 3. Verify Matplotlib backend was updated
    x_mpl, y_mpl = h.line.get_data()
    np.testing.assert_array_equal(x_mpl, [1.0, 2.0, 3.0])
    np.testing.assert_array_equal(y_mpl, [1.0, 4.0, 9.0])

def test_animatedline_clearpoints():
    """Verify clearpoints resets data."""
    h = animatedline()
    addpoints(h, [1, 2, 3], [1, 4, 9])
    
    clearpoints(h)
    
    assert h.x == []
    assert h.y == []
    
    x_mpl, y_mpl = h.line.get_data()
    assert len(x_mpl) == 0
    assert len(y_mpl) == 0

def test_drawnow_synchronous_main_thread():
    """
    Verify that calling drawnow() on the Main Thread does NOT deadlock.
    It should internally call PlotEngine.tick() immediately.
    """
    h = animatedline()
    addpoints(h, 1, 1)
    
    # This call passes wait=True. 
    # On the main thread, the lock logic we added should bypass the event wait 
    # and call tick() directly. If it hangs, the test fails (timeout).
    try:
        drawnow()
    except TimeoutError:
        pytest.fail("drawnow() deadlocked on main thread")

def test_draw_request_consumption():
    """Verify the request/consume cycle used by the Engine."""
    # 1. Reset
    plot_manager._dirty = False
    plot_manager._immediate_draw = False
    
    # 2. Request Draw (simulating kernel)
    plot_manager.request_draw(immediate=True)
    
    assert plot_manager._dirty is True
    assert plot_manager._immediate_draw is True
    
    # 3. Consume Request (simulating Engine loop)
    dirty, immediate = plot_manager.consume_draw_request()
    
    assert dirty is True
    assert immediate is True
    assert plot_manager._dirty is False  # Should be reset

def test_comet_smoke_test():
    """
    Smoke test for comet to ensure it runs without crashing.
    (Cannot easily test visual animation in headless mode, but ensures logic holds)
    """
    x = [0, 1, 2]
    y = [0, 1, 0]
    
    # Should run to completion
    comet(x, y)
    
    # Verify plotting happened
    ax = plot_manager.gca()
    assert len(ax.get_lines()) >= 1

def test_threaded_drawnow_simulation():
    """
    Simulate the Kernel/Engine thread interaction.
    """
    # 1. Start a thread that acts like the Kernel calling drawnow()
    draw_complete = threading.Event()
    
    def kernel_job():
        # This will block until main thread processes it
        plot_manager.request_draw(immediate=True, wait=True)
        draw_complete.set()

    t = threading.Thread(target=kernel_job)
    t.start()
    
    # 2. Give the thread a moment to hit the wait()
    time.sleep(0.1)
    
    # 3. Act like the Engine processing the request
    PlotEngine.tick() # This calls notify_draw_complete()
    
    # 4. Verify the thread was unblocked
    t.join(timeout=1.0)
    assert not t.is_alive(), "Kernel thread did not unblock after tick()"
    assert draw_complete.is_set()


def test_headless_widget_uses_plain_agg_canvas():
    ax = plot_manager.gca()
    canvas = ax.figure.canvas

    assert isinstance(canvas, MPLFigureCanvasAgg)
    assert canvas.__class__.__module__.startswith("matplotlib.backends.backend_agg")


def test_headless_widget_disables_constrained_layout():
    fig = plot_manager.gca().figure

    if hasattr(fig, "get_layout_engine"):
        engine = fig.get_layout_engine()
        engine_name = type(engine).__name__ if engine is not None else None

        assert engine is None or getattr(engine, "name", None) == "none" or engine_name == "PlaceHolderLayoutEngine"
        assert engine_name != "ConstrainedLayoutEngine"

    if hasattr(fig, "get_constrained_layout"):
        assert fig.get_constrained_layout() is False


def test_animatedline_after_3d_plot_uses_2d_axes():
    from shared.plotting_engine.plot3d import plot3

    plot3([0, 1], [0, 1], [0, 1])

    h = animatedline()
    addpoints(h, 1, 1)
    drawnow()

    ax = plot_manager.gca()
    assert getattr(ax, "name", "") == "rectilinear"
    assert h.line in ax.get_lines()


def test_animatedline_promotes_to_3d_with_z_points():
    h = animatedline()
    addpoints(h, 1, 2, 3)
    drawnow()

    ax = plot_manager.gca()
    assert getattr(ax, "name", "") == "3d"
    assert h.line in ax.get_lines()
