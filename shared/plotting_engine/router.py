"""
Smart Plot Router
=================
Intercepts plotting commands, determines the optimal backend, 
and manages multi-window distribution.
"""

from typing import Any, Dict
from shared.plotting_engine.state import plot_manager

class UniversalPlotRouter:
    # Define which backend handles which plot types best
    PLOTLY_DOMAINS = {"surface", "heatmap", "box", "violin", "interactive_scatter"}
    MPL_DOMAINS = {"implicit", "vector_field", "bode", "nyquist", "contour", "polar"}

    @classmethod
    def route(cls, plot_type: str, data: Any, kwargs: Dict[str, Any]):
        """
        The universal entry point for all plotting commands.
        """
        # 1. Determine Backend
        backend_target = "plotly" if plot_type in cls.PLOTLY_DOMAINS else "mpl"

        # 2. Window Manager: Check if we need to force a new window
        # For example, if the user explicitly passes `figure=2` in their plot command
        target_fig_id = kwargs.pop("figure", None)
        
        # 3. Prepare the Window
        # This will automatically spawn a detached window if fig_id > 1
        active_surface = plot_manager.figure(fig_id=target_fig_id, backend=backend_target)

        # 4. Dispatch to the correct rendering engine
        if backend_target == "plotly":
            cls._dispatch_plotly(active_surface, plot_type, data, kwargs)
        else:
            cls._dispatch_mpl(plot_type, data, kwargs)

        # 5. Request a scheduled draw from the engine
        plot_manager.request_draw(immediate=False, wait=False)

    @classmethod
    def _dispatch_plotly(cls, widget, plot_type: str, data: Any, kwargs: Dict):
        import plotly.graph_objects as go
        
        # Construct the Plotly figure
        fig = go.Figure()
        
        if plot_type == "surface":
            fig.add_trace(go.Surface(z=data, **kwargs))
        elif plot_type == "heatmap":
            fig.add_trace(go.Heatmap(z=data, **kwargs))
            
        # Send to your PlotlyWidget natively
        widget.render_figure(fig)

    @classmethod
    def _dispatch_mpl(cls, plot_type: str, data: Any, kwargs: Dict):
        # Delegate to Matplotlib backend
        # We use plot_manager.gca() to ensure layout safety
        is_3d = plot_type in ["vector_field_3d", "contour3d"]
        ax = plot_manager.gca(is_3d=is_3d)
        
        if plot_type == "vector_field":
            # Expecting data = (X, Y, U, V)
            ax.quiver(*data, **kwargs)
        elif plot_type == "implicit":
            # Handle implicit math plotting
            pass 
        else:
            # Standard 2D line plot fallback
            ax.plot(*data, **kwargs)