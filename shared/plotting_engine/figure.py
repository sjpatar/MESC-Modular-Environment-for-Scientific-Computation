"""
MATLAB-style Figure Management for Mathex
--------------------------------------------

Semantics:
    figure()              -> select/create Figure 1
    figure(n)             -> select/create Figure n
    gcf()                 -> return current Figure
    clf()                 -> clear current Figure
    close()               -> close current Figure
    close(n)              -> close Figure n
    close('all')          -> close all non-UI figures

Rules:
    - Figure 1 is the docked UI figure (if UI exists)
    - figure(n>1) creates standalone PlotWidget figures
    - No backend selection
    - No pyplot usage
"""

from typing import Optional, Dict, Union

from .state import plot_manager
from .mpl_backend import PlotWidget, HeadlessPlotWidget
from .engine import PlotEngine

# ------------------------------------------------------------------
# Internal registry
# ------------------------------------------------------------------

_figures: Dict[int, Union[PlotWidget, HeadlessPlotWidget]] = {}
_current: int = 1

# Injected by UI on startup (optional)
_ui_widget: Optional[PlotWidget] = None


# ------------------------------------------------------------------
# UI bootstrap (called once by UI layer)
# ------------------------------------------------------------------

def init_ui_widget(widget: PlotWidget):
    """
    Register the docked UI PlotWidget as Figure 1.
    """
    global _ui_widget
    _ui_widget = widget
    _figures[1] = widget
    plot_manager.set_widget(widget)


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _create_widget():
    """Factory to create appropriate widget based on engine mode."""
    # Ensure engine is initialized to check mode
    PlotEngine.initialize()
    
    # If in test or CLI mode, use headless
    if PlotEngine._mode in ("test", "cli"):
        return HeadlessPlotWidget()
        
    # Default to Qt widget
    return PlotWidget()

def _ensure_figure_1():
    """
    Guarantee Figure 1 exists.
    """
    if 1 not in _figures:
        if _ui_widget is not None:
            _figures[1] = _ui_widget
        else:
            _figures[1] = _create_widget()


def _activate(num: int):
    """
    Activate figure `num` and bind it to PlotStateManager.
    """
    global _current

    if num == 1:
        _ensure_figure_1()
    else:
        if num not in _figures:
            # [FIX] Thread-Safety & UI Routing
            # Creating QWidgets from a background KernelWorker thread causes PySide6 
            # to fail silently. To ensure plots appear properly in the main plot window, 
            # we safely alias all requested figures back to the UI widget if it exists.
            if _ui_widget is not None:
                _figures[num] = _ui_widget
            else:
                _figures[num] = _create_widget()

    _current = num
    plot_manager.set_widget(_figures[num])

# ------------------------------------------------------------------
# Auto-Creation Hook
# ------------------------------------------------------------------
def _auto_create_figure():
    """Callback for PlotStateManager to auto-create figure."""
    figure(1)

# Register the hook immediately
plot_manager.set_figure_creator(_auto_create_figure)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def figure(*args, **kwargs) -> int:
    """
    Select or create a figure.

    figure()                  -> Figure 1
    figure(n)                 -> Figure n
    figure(..., 'Prop', Val)  -> Set properties (Name, Color)
    """
    num = None

    # 1. Support explicit 'num' kwarg (Backward compatibility)
    if 'num' in kwargs:
        try:
            num = int(kwargs.pop('num'))
        except Exception:
            pass

    # 2. Parse positional arguments
    props = kwargs.copy()
    start_idx = 0

    if num is None and len(args) > 0:
        first = args[0]
        # Check if first argument is a figure number
        # Logic: If it's a number, it's the ID. If it's a string, it's a property key.
        try:
            if isinstance(first, (int, float)):
                num = int(first)
                start_idx = 1
        except Exception:
            pass

    # Default to Figure 1 if no number provided
    if num is None:
        num = 1

    # 3. Extract Key-Value pairs from remaining variable arguments
    # e.g. figure('Color', 'w') -> args=['Color', 'w']
    remaining_args = args[start_idx:]
    for i in range(0, len(remaining_args), 2):
        if i + 1 < len(remaining_args):
            k = remaining_args[i]
            v = remaining_args[i+1]
            if isinstance(k, str):
                props[k] = v

    # 4. Activate the figure
    _activate(num)

    # 5. Apply supported properties
    try:
        widget = _figures[num]
        
        # 'Name': Window Title
        name = props.get("Name") or props.get("name")
        if name:
            if hasattr(widget, "setWindowTitle"):
                widget.setWindowTitle(str(name))
            elif hasattr(widget, "parent"):
                 p = widget.parent()
                 if hasattr(p, "setWindowTitle"):
                     p.setWindowTitle(str(name))

        # 'Color': Figure Background Color
        color = props.get("Color") or props.get("color")
        if color:
            fig = getattr(widget, "figure", None)
            if fig:
                fig.set_facecolor(color)
                # Force re-draw if canvas exists
                if hasattr(widget, "canvas"):
                    try: widget.canvas.draw_idle()
                    except: pass

    except Exception:
        pass

    return num


def gcf():
    """
    Return the current Matplotlib Figure object.
    """
    _ensure_figure_1()
    widget = _figures.get(_current)
    return getattr(widget, "figure", None)


def clf():
    """
    Clear current figure contents (MATLAB clf).
    This function forces a backend reset to handle mixed 3D/2D layouts.
    """
    _ensure_figure_1()
    
    # 1. Clear Mathex internal state (lines, hold state, etc.)
    try:
        plot_manager.clf()
    except Exception:
        pass

    # 2. [CRITICAL FIX] Force Clear the Backend Widget
    # This ensures the screen is wiped even if the plot_manager thinks it's already done.
    widget = _figures.get(_current)
    if widget:
        # Check if it's a real Qt widget or Headless
        if hasattr(widget, 'clear'):
            # Use the robust clear method from mpl_backend (reset layout modes)
            widget.clear()
        
        # Explicitly grab figure/canvas for manual override if needed
        fig = getattr(widget, 'figure', None)
        if fig:
            # Ensure background stays dark (Matplotlib clf defaults to white/grey)
            fig.set_facecolor('#1e1e1e')
            
        canvas = getattr(widget, 'canvas', None)
        if canvas:
            try:
                canvas.draw_idle()
            except Exception:
                pass


def close(target: Union[int, str, None] = None):
    """
    Close figures.

    close()        -> close current figure
    close(n)       -> close figure n
    close('all')   -> close all non-UI figures
    """
    global _current

    if target is None:
        target = _current

    # Close all non-UI figures
    if isinstance(target, str) and target.lower() == "all":
        for n in list(_figures.keys()):
            if n == 1:
                # For UI figure, just clear it, don't destroy
                clf()
                continue
            
            w = _figures.pop(n, None)
            # [FIX] Protect the main UI widget from destruction if it was aliased
            if w and w is not _ui_widget:
                try:
                    # Qt cleanup
                    if hasattr(w, "close"): w.close()
                    if hasattr(w, "setParent"): w.setParent(None)
                except Exception:
                    pass
        _activate(1)
        return

    # Close single figure
    try:
        n = int(target)
    except Exception:
        return

    w = _figures.pop(n, None)
    if n == 1:
        # MATLAB: close(1) clears but does not destroy UI figure
        _ensure_figure_1() 
        clf()
    elif w and w is not _ui_widget:
        # [FIX] Protect the main UI widget from destruction if it was aliased
        try:
            if hasattr(w, "close"): w.close() 
            if hasattr(w, "setParent"): w.setParent(None)
        except Exception:
            pass

    if _current == n:
        remaining = sorted(_figures.keys())
        _activate(remaining[0] if remaining else 1)


def closeall():
    """Alias for close('all')."""
    close("all")


# [FIX] Ensure Transpiler supports these as parameterless commands (e.g. `clf;`)
figure.__mathex_command__ = True
gcf.__mathex_command__ = True
clf.__mathex_command__ = True
close.__mathex_command__ = True
closeall.__mathex_command__ = True