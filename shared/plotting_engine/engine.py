"""
Plotting Engine (Thread-Safe Fix)
=================================

Single authoritative DRAW SCHEDULER for Mathex.

Responsibilities (STRICT):
- Backend selection (once)
- Mode detection (cli / ui / test)
- Global defaults (once)
- Consuming redraw requests from PlotStateManager
- Triggering backend rendering (ONLY place allowed to draw)

This module MUST NOT:
- Own figure or axes state
- Call pyplot.plot / pyplot.figure
- Mutate plotting state
- Spawn threads (GUI updates must be on Main Thread)
"""

from __future__ import annotations

import os
import sys
import threading
from typing import Optional, Literal

import matplotlib

from shared.plotting_engine.state import plot_manager


Mode = Literal["auto", "cli", "ui", "test"]


class PlotEngine:
    """
    MATLAB-style plotting engine.

    This class is the ONLY place in the entire system
    allowed to trigger a render.
    """

    _initialized: bool = False
    _mode: Optional[Mode] = None

    # Lock to ensure we don't process draw requests while the kernel is writing
    _draw_lock = threading.Lock()

    # ------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------
    @classmethod
    def initialize(cls, mode: Mode = "auto", force: bool = False) -> None:
        # [FIX] Allow forcing re-initialization (essential for tests)
        if cls._initialized and not force:
            return

        cls._mode = cls._resolve_mode(mode)
        cls._select_backend(cls._mode)
        cls._apply_defaults()

        cls._initialized = True

        # [FIX] Do NOT start a background thread here.
        # The UI (app.py) will drive us via QTimer on the Main Thread.

    @classmethod
    def shutdown(cls):
        # No thread to join anymore
        pass

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------
    @classmethod
    def tick(cls):
        """
        Manual draw processing.
        Called by QTimer in UI mode (Main Thread), or manually in CLI/Test mode.
        """
        cls._ensure_initialized()
        cls._process_draw_requests()

    # ------------------------------------------------------------
    # Core draw scheduler
    # ------------------------------------------------------------
    @classmethod
    def _process_draw_requests(cls):
        cls._ensure_initialized()

        # [CRITICAL FIX] Use non-blocking lock for UI, blocking for CLI.
        # If CLI/Headless, we MUST block to ensure the draw finishes.
        should_block = (cls._mode != "ui")

        if not cls._draw_lock.acquire(blocking=should_block):
            return

        try:
            # Atomic check for dirty flags
            dirty, immediate = plot_manager.consume_draw_request()
            
            # If nothing to do, exit immediately
            if not dirty:
                return

            # [CRITICAL FIX] Use try/finally to ensure we ALWAYS notify the kernel.
            # If we return early due to an error (e.g. no figure), and don't notify,
            # the kernel will deadlock waiting for the signal (when wait=True).
            try:
                try:
                    fig_state = plot_manager._get_fig_state()
                except Exception:
                    # No figure exists to draw on
                    return

                widget = fig_state.widget
                if not widget:
                    return

                try:
                    # Immediate = synchronous draw (drawnow / getframe)
                    if immediate:
                        widget.canvas.draw()
                        widget.canvas.flush_events()
                    else:
                        widget.canvas.draw_idle()
                except Exception as render_err:
                    # [FIX] Do not swallow rendering errors silently
                    print(f"[PlotEngine Error] Failed to render plot: {render_err}", file=sys.stderr)
            
            finally:
                # Signal completion to any waiting threads (Kernel)
                plot_manager.notify_draw_complete()
        
        finally:
            cls._draw_lock.release()

    # ------------------------------------------------------------
    # Backend / mode resolution
    # ------------------------------------------------------------
    @staticmethod
    def _resolve_mode(mode: Mode) -> Mode:
        if mode != "auto":
            return mode

        if "PYTEST_CURRENT_TEST" in os.environ:
            return "test"

        # [FIX] Explicitly check for PySide6 to detect App Mode reliably
        if "PySide6" in sys.modules:
            return "ui"

        if hasattr(sys, "ps1"):
            return "ui"

        if sys.stdout.isatty():
            return "cli"

        return "test"

    @staticmethod
    def _select_backend(mode: Mode) -> None:
        if mode in ("cli", "test"):
            matplotlib.use("Agg", force=True)
            return

        try:
            matplotlib.use("QtAgg", force=True)
        except Exception:
            matplotlib.use("Agg", force=True)

    @staticmethod
    def _apply_defaults() -> None:
        from app_platform.core.settings.defaults import apply
        apply()

    # ------------------------------------------------------------
    # Safety
    # ------------------------------------------------------------
    @classmethod
    def _ensure_initialized(cls):
        if not cls._initialized:
            cls.initialize("auto")


# ------------------------------------------------------------
# Module-level convenience (MATLAB style)
# ------------------------------------------------------------

def initialize(mode: Mode = "auto", force: bool = False) -> None:
    PlotEngine.initialize(mode, force=force)


def tick() -> None:
    """
    Manual draw processing (CLI / tests).
    Equivalent to MATLAB implicit draw at prompt return.
    """
    PlotEngine.tick()