"""
PlotStateManager
================

Single authoritative MATLAB-style plotting state manager.
"""

from __future__ import annotations

import time
import threading  # [FIX] Required for animation synchronization
import numpy as np
import mpl_toolkits.mplot3d  # [FIX] Essential: Registers '3d' projection
from typing import Dict, Optional, Union, Callable


BoolLike = Union[bool, str]


class _AxesState:
    __slots__ = ("hold", "grid", "equal", "tight")

    def __init__(self):
        self.hold = False
        self.grid = False
        self.equal = False
        self.tight = False


class _FigureState:
    __slots__ = ("widget", "axes_state", "current_axes")

    def __init__(self, widget):
        self.widget = widget
        self.axes_state: Dict[object, _AxesState] = {}
        self.current_axes = None


class PlotStateManager:
    """
    MATLAB-compatible global plotting state manager.
    """

    _instance: Optional["PlotStateManager"] = None

    # ---- class-level typing (IMPORTANT) ----
    _figures: Dict[int, _FigureState]
    _current_fig_id: Optional[int]
    _dirty: bool
    _last_draw_request: float
    _immediate_draw: bool
    _figure_creator: Optional[Callable[[], None]]
    _draw_event: threading.Event  # [FIX] Sync event

    def __new__(cls):
        if cls._instance is None:
            inst = super().__new__(cls)

            inst._figures = {}
            inst._current_fig_id = None
            inst._dirty = False
            inst._last_draw_request = 0.0
            inst._immediate_draw = False
            inst._figure_creator = None
            
            # [FIX] Event to block kernel until UI finishes drawing
            inst._draw_event = threading.Event()

            cls._instance = inst
        return cls._instance

    # ------------------------------------------------------------
    # Figure management
    # ------------------------------------------------------------
    def bind_figure(self, fig_id: int, widget) -> None:
        self._figures[fig_id] = _FigureState(widget)
        self._current_fig_id = fig_id
        self._mark_dirty()

    def set_figure_creator(self, callback: Callable[[], None]) -> None:
        """Register a callback to create a figure if one is missing."""
        self._figure_creator = callback

    def figure(self, fig_id: Optional[int] = None):
        if fig_id is None:
            if self._current_fig_id is None:
                if self._figure_creator:
                    self._figure_creator()
                if self._current_fig_id is None:
                    raise RuntimeError("No figure bound.")
            return self._figures[self._current_fig_id].widget.figure

        if fig_id not in self._figures:
            raise RuntimeError(f"Figure {fig_id} not bound.")

        self._current_fig_id = fig_id
        return self._figures[fig_id].widget.figure

    def gcf(self):
        if self._current_fig_id is None:
            if self._figure_creator:
                self._figure_creator()
            if self._current_fig_id is None:
                raise RuntimeError("No current figure.")
        return self._figures[self._current_fig_id].widget.figure

    # ------------------------------------------------------------
    # [FIX] Advanced CLF: Delegating to Backend
    # ------------------------------------------------------------
    def clf(self):
        """
        Clear current figure.
        DELEGATES to widget.clear() to ensure Layout State Machine is reset.
        """
        if self._current_fig_id is None:
            if self._figure_creator:
                self._figure_creator()
            if self._current_fig_id is None:
                return

        fig_state = self._figures[self._current_fig_id]
        
        # [CRITICAL FIX] Do not call figure.clf() directly.
        # Call widget.clear() so the backend can reset the layout engine from 3D->2D.
        if hasattr(fig_state.widget, 'clear'):
            fig_state.widget.clear()
        else:
            fig_state.widget.figure.clf()
        
        # Reset internal state tracking
        fig_state.current_axes = None
        fig_state.axes_state.clear()
        
        self._mark_dirty(immediate=True)

    # ------------------------------------------------------------
    # Axes management
    # ------------------------------------------------------------
    def gca(self, *, is_3d: Optional[bool] = None):
        """
        Get Current Axes with Layout Safety Checks.
        """
        fig_state = self._get_fig_state()
        ax = fig_state.current_axes

        if ax is not None:
            if is_3d is not None:
                current_is_3d = getattr(ax, 'name', '') == '3d'
                
                if is_3d != current_is_3d:
                    # 1. Capture geometry
                    geometry = None
                    try:
                        geometry = ax.get_subplotspec()
                    except Exception:
                        pass

                    # 2. Delete old
                    try:
                        ax.clear() # Wiping Artists first fixes ghosting bug
                        fig_state.widget.figure.delaxes(ax)
                    except Exception:
                        pass
                        
                    if ax in fig_state.axes_state:
                        del fig_state.axes_state[ax]
                    
                    # 3. Recreate
                    if geometry:
                        # [CRITICAL] Update layout engine before adding subplot
                        if hasattr(fig_state.widget, 'configure_layout'):
                            fig_state.widget.configure_layout(is_3d=is_3d)
                        
                        try:
                            ax = fig_state.widget.figure.add_subplot(geometry, projection="3d" if is_3d else None)
                        except Exception:
                             ax = fig_state.widget.new_axes(projection="3d" if is_3d else None)
                    else:
                        ax = fig_state.widget.new_axes(projection="3d" if is_3d else None)
                    
                    # [PARANOIA CHECK] Ensure the new axes actually matches the request
                    new_is_3d = getattr(ax, 'name', '') == '3d'
                    if is_3d and not new_is_3d:
                        try: fig_state.widget.figure.delaxes(ax)
                        except: pass
                        ax = fig_state.widget.new_axes(projection='3d')

                    # [FIX] Re-apply styling (Backend handles geometry now)
                    if hasattr(fig_state.widget, '_apply_axes_defaults'):
                        try: fig_state.widget._apply_axes_defaults(ax)
                        except: pass
                    
                    # 4. Update state
                    fig_state.current_axes = ax
                    fig_state.axes_state[ax] = _AxesState()
                    self._apply_axes_state(ax)

        # Create new if none exists
        if ax is None:
            target_proj = "3d" if (is_3d is True) else None
            # Delegating to widget.new_axes handles the layout switch automatically
            ax = fig_state.widget.new_axes(projection=target_proj)
            fig_state.current_axes = ax
            fig_state.axes_state[ax] = _AxesState()
            self._apply_axes_state(ax)

        return ax

    def subplot(self, m: int, n: int, p: Union[int, list, np.ndarray], *, is_3d: bool = False):
        fig_state = self._get_fig_state()
        fig = fig_state.widget.figure
        
        # [CRITICAL FIX] Force backend to configure layout engine based on 'is_3d'
        if hasattr(fig_state.widget, 'configure_layout'):
            fig_state.widget.configure_layout(is_3d=is_3d)

        # Handle Spanning Subplots (Vector p)
        is_vector = False
        if hasattr(p, '__len__') and not isinstance(p, str):
             if np.ndim(p) > 0: 
                 is_vector = True
        
        try:
            if is_vector:
                # Vector p logic (e.g., [3, 4])
                p_arr = np.array(p).flatten()
                if p_arr.size == 1:
                    idx = int(p_arr[0])
                    ax = fig.add_subplot(int(m), int(n), idx, projection="3d" if is_3d else None)
                else:
                    rows = (p_arr - 1) // n
                    cols = (p_arr - 1) % n
                    r_start, r_end = int(rows.min()), int(rows.max()) + 1
                    c_start, c_end = int(cols.min()), int(cols.max()) + 1
                    
                    gs = fig.add_gridspec(int(m), int(n))
                    ax = fig.add_subplot(gs[r_start:r_end, c_start:c_end], projection="3d" if is_3d else None)
            else:
                # Standard scalar subplot
                p_val = int(p) if not isinstance(p, int) else p
                ax = fig.add_subplot(
                    int(m), int(n), p_val, projection="3d" if is_3d else None
                )
        except Exception:
            # Fallback to widget logic
            ax = fig_state.widget.new_axes(projection="3d" if is_3d else None)

        # [FIX] Apply defaults
        if hasattr(fig_state.widget, '_apply_axes_defaults'):
            try: fig_state.widget._apply_axes_defaults(ax)
            except: pass

        fig_state.current_axes = ax
        fig_state.axes_state.setdefault(ax, _AxesState())
        self._apply_axes_state(ax)
        self._mark_dirty(immediate=True)
        return ax

    # ------------------------------------------------------------
    # Plot preparation
    # ------------------------------------------------------------
    def prepare_plot(self, *, is_3d: bool = False):
        fig = self._get_fig_state()
        ax = fig.current_axes

        if ax is None:
            return self.gca(is_3d=is_3d)

        # Verify 3D compatibility
        current_is_3d = getattr(ax, 'name', '') == '3d'
        
        # [FIX] Smart Hold Logic:
        # If we are holding, and the current axes is 3D, allow 2D plots (like title, text)
        # to draw on it without destroying the 3D axes.
        state = fig.axes_state.get(ax)
        is_hold = state.hold if state else False

        if is_hold and current_is_3d and not is_3d:
            # Allow 2D plot on 3D axes
            return ax
        
        # Otherwise, strictly enforce type
        if is_3d and not current_is_3d:
            return self.gca(is_3d=True)
        
        if not is_3d and current_is_3d:
            return self.gca(is_3d=False)

        if state and not state.hold:
            try:
                ax.clear()
                # [FIX] Re-apply style after clear
                if hasattr(fig.widget, '_apply_axes_defaults'):
                    fig.widget._apply_axes_defaults(ax)
                self._apply_axes_state(ax) 
            except Exception:
                pass
            return ax

        return ax
    
    # ------------------------------------------------------------
    # Backward compatibility
    # ------------------------------------------------------------
    @property
    def widget(self):
        if self._current_fig_id is None:
            return None
        fig = self._figures.get(self._current_fig_id)
        return fig.widget if fig else None

    def set_widget(self, widget):
        if widget is None:
            return
        fig_id = id(widget)
        if fig_id not in self._figures:
            self.bind_figure(fig_id, widget)
        self._current_fig_id = fig_id

    # ------------------------------------------------------------
    # Axes-local state setters
    # ------------------------------------------------------------
    def hold(self, mode: BoolLike):
        self._set_axes_flag("hold", mode)

    def grid(self, mode: BoolLike):
        self._set_axes_flag("grid", mode)

    def axis_equal(self, mode: BoolLike):
        self._set_axes_flag("equal", mode)

    def axis_tight(self, mode: BoolLike):
        self._set_axes_flag("tight", mode)

    def _set_axes_flag(self, name: str, mode: BoolLike):
        ax = self.gca(is_3d=None)
        fig = self._get_fig_state()
        state = fig.axes_state.setdefault(ax, _AxesState())

        value = (
            str(mode).lower() in ("on", "true", "equal", "tight")
            if isinstance(mode, str)
            else bool(mode)
        )

        setattr(state, name, value)
        self._apply_axes_state(ax)
        self._mark_dirty()

    # ------------------------------------------------------------
    # Apply axes state (NO DRAWING)
    # ------------------------------------------------------------
    def _apply_axes_state(self, ax):
        fig = self._get_fig_state()
        state = fig.axes_state.get(ax)
        if not state:
            return

        try:
            ax.grid(state.grid)
        except Exception:
            pass

        try:
            if getattr(ax, 'name', '') == '3d':
                if state.equal:
                    ax.set_box_aspect((1, 1, 1))
                else:
                    ax.set_box_aspect(None) 
            else:
                ax.set_aspect("equal" if state.equal else "auto", adjustable="box")
        except Exception:
            pass

        if state.tight:
            try:
                # [CRITICAL FIX] axis tight must NOT call figure.tight_layout()
                # It should only set the axes limits to match data.
                ax.autoscale(enable=True, axis='both', tight=True)
            except Exception:
                pass

    # ------------------------------------------------------------
    # Redraw scheduling (THREAD SYNCHRONIZED)
    # ------------------------------------------------------------
    def request_draw(self, *, immediate: bool = False, wait: bool = False):
        """
        Request a draw.
        if wait=True: BLOCKS this thread until the Engine (Main Thread) completes the draw.
        """
        # [FIX] Race Condition Prevention:
        # We must clear the event BEFORE marking dirty.
        # Otherwise, if the Engine draws and sets the event 
        # BEFORE we clear it, we will wait forever (deadlock).
        is_worker = wait and (threading.current_thread() is not threading.main_thread())
        
        if is_worker:
            self._draw_event.clear()

        self._mark_dirty(immediate=immediate)
        
        if wait:
            # Prevent Deadlock: If we are the Main Thread, we cannot wait for ourselves.
            if threading.current_thread() is threading.main_thread():
                # We are the renderer. Trigger a tick immediately to process the request.
                # Local import avoids circular dependency.
                from .engine import PlotEngine
                PlotEngine.tick()
                return

            # We are the Worker Thread. Wait for UI to finish drawing.
            self._draw_event.wait(timeout=2.0)

    def notify_draw_complete(self):
        """Called by PlotEngine after a draw is finished to wake up the kernel."""
        self._draw_event.set()

    def consume_draw_request(self):
        if not self._dirty:
            return False, False

        dirty = self._dirty
        immediate = self._immediate_draw

        self._dirty = False
        self._immediate_draw = False
        self._last_draw_request = time.time()

        return dirty, immediate

    # ------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------
    def _mark_dirty(self, *, immediate: bool = False):
        self._dirty = True
        if immediate:
            self._immediate_draw = True

    def _get_fig_state(self) -> _FigureState:
        if self._current_fig_id is None:
            if self._figure_creator:
                self._figure_creator()
            if self._current_fig_id is None:
                raise RuntimeError("No active figure.")
        return self._figures[self._current_fig_id]


plot_manager = PlotStateManager()