"""
Smart Plot Router
=================

Universal plotting entry points that choose the best rendering backend:
- Plotly for interactive, WebGL, and 3D exploration.
- Matplotlib for static scientific, engineering, and publication plots.

The router owns backend choice only. Figure state, draw scheduling, and Qt
window creation remain delegated to PlotStateManager and the Mathex UI layer.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np

from shared.plotting_engine.state import plot_manager


MPL_BACKEND = "mpl"
PLOTLY_BACKEND = "plotly"

PLOTLY_PLOT_TYPES = {
    "plot3",
    "scatter3",
    "surface",
    "surf",
    "mesh",
    "heatmap_interactive",
    "interactive_scatter",
    "scatter_interactive",
    "violin",
    "box",
}

MPL_PLOT_TYPES = {
    "plot",
    "line",
    "scatter",
    "hist",
    "histogram",
    "heatmap",
    "imagesc",
    "imshow",
    "contour",
    "contourf",
    "quiver",
    "streamline",
    "implicit",
    "vector_field",
    "bode",
    "nyquist",
    "polar",
}


def plot(*args, kind: str = "plot", backend: Optional[str] = None, figure: Optional[int] = None, **kwargs):
    """
    Universal plot wrapper.

    Examples:
        plot(x, y)                         -> Matplotlib line plot
        plot(x, y, z, kind="scatter3")     -> Plotly 3D scatter
        plot(Z, kind="surface", figure=2)  -> Plotly surface in Figure 2
        plot(x, y, backend="mpl")          -> Force Matplotlib
    """
    return UniversalPlotRouter.route(kind, args, kwargs, backend=backend, figure=figure)


class UniversalPlotRouter:
    @classmethod
    def route(
        cls,
        plot_type: str,
        data: Any,
        kwargs: Optional[Dict[str, Any]] = None,
        *,
        backend: Optional[str] = None,
        figure: Optional[int] = None,
    ):
        kwargs = dict(kwargs or {})
        plot_type = cls._normalize_plot_type(plot_type)
        target_fig_id = cls._extract_figure_id(kwargs, figure)
        backend_target = cls._choose_backend(plot_type, kwargs, backend)

        if backend_target == PLOTLY_BACKEND:
            surface = plot_manager.activate_figure(target_fig_id, backend=PLOTLY_BACKEND)
            return cls._dispatch_plotly(surface, plot_type, data, kwargs)

        plot_manager.activate_figure(target_fig_id, backend=MPL_BACKEND)
        result = cls._dispatch_mpl(plot_type, data, kwargs)
        plot_manager.request_draw(immediate=False, wait=False)
        return result

    @staticmethod
    def _normalize_plot_type(plot_type: str) -> str:
        return str(plot_type or "plot").strip().lower().replace("-", "_")

    @staticmethod
    def _extract_figure_id(kwargs: Dict[str, Any], explicit_figure: Optional[int]) -> int:
        fig_id = explicit_figure
        if fig_id is None:
            fig_id = kwargs.pop("figure", None)
        if fig_id is None:
            fig_id = kwargs.pop("fig", None)
        if fig_id is None:
            return 1
        return int(fig_id)

    @classmethod
    def _choose_backend(cls, plot_type: str, kwargs: Dict[str, Any], backend: Optional[str]) -> str:
        explicit = backend or kwargs.pop("backend", None)
        if explicit:
            normalized = str(explicit).strip().lower()
            if normalized in ("plotly", "webgl", "interactive"):
                return PLOTLY_BACKEND
            if normalized in ("mpl", "matplotlib", "static"):
                return MPL_BACKEND
            raise ValueError("Backend must be 'plotly', 'webgl', 'interactive', 'mpl', 'matplotlib', or 'static'")

        if bool(kwargs.pop("interactive", False)) or bool(kwargs.pop("webgl", False)):
            return PLOTLY_BACKEND

        if plot_type in PLOTLY_PLOT_TYPES:
            return PLOTLY_BACKEND

        return MPL_BACKEND

    @classmethod
    def _dispatch_plotly(cls, surface, plot_type: str, data: Any, kwargs: Dict[str, Any]):
        import plotly.graph_objects as go

        fig = go.Figure()
        args = tuple(data) if isinstance(data, (tuple, list)) else (data,)
        dragmode = kwargs.pop("dragmode", "select")

        if plot_type in ("surface", "surf"):
            x, y, z = cls._surface_args(args)
            fig.add_trace(go.Surface(x=x, y=y, z=z, colorscale=kwargs.pop("colorscale", "Turbo"), **kwargs))
        elif plot_type == "mesh":
            x, y, z = cls._surface_args(args)
            fig.add_trace(
                go.Surface(
                    x=x,
                    y=y,
                    z=z,
                    colorscale=kwargs.pop("colorscale", "Turbo"),
                    contours={"x": {"show": True}, "y": {"show": True}},
                    **kwargs,
                )
            )
        elif plot_type == "plot3":
            x, y, z = cls._xyz_args(args)
            customdata = kwargs.pop("customdata", cls._point_indices(len(x)))
            fig.add_trace(
                go.Scatter3d(
                    x=x,
                    y=y,
                    z=z,
                    mode=kwargs.pop("mode", "lines"),
                    customdata=customdata,
                    **kwargs,
                )
            )
        elif plot_type == "scatter3":
            x, y, z = cls._xyz_args(args)
            marker = kwargs.pop("marker", {"size": 4, "color": z, "colorscale": "Turbo"})
            customdata = kwargs.pop("customdata", cls._point_indices(len(x)))
            fig.add_trace(
                go.Scatter3d(
                    x=x,
                    y=y,
                    z=z,
                    mode=kwargs.pop("mode", "markers"),
                    marker=marker,
                    customdata=customdata,
                    **kwargs,
                )
            )
        elif plot_type in ("interactive_scatter", "scatter_interactive"):
            x, y = cls._xy_args(args)
            customdata = kwargs.pop("customdata", cls._point_indices(len(x)))
            fig.add_trace(
                go.Scattergl(
                    x=x,
                    y=y,
                    mode=kwargs.pop("mode", "markers"),
                    customdata=customdata,
                    **kwargs,
                )
            )
        elif plot_type == "heatmap_interactive":
            fig.add_trace(go.Heatmap(z=np.asarray(args[0]), **kwargs))
        elif plot_type == "violin":
            fig.add_trace(go.Violin(y=np.asarray(args[0]).flatten(), box_visible=True, meanline_visible=True, **kwargs))
        elif plot_type == "box":
            fig.add_trace(go.Box(y=np.asarray(args[0]).flatten(), **kwargs))
        else:
            x, y = cls._xy_args(args)
            customdata = kwargs.pop("customdata", cls._point_indices(len(x)))
            fig.add_trace(
                go.Scatter(
                    x=x,
                    y=y,
                    mode=kwargs.pop("mode", "lines"),
                    customdata=customdata,
                    **kwargs,
                )
            )

        fig.update_layout(dragmode=dragmode)
        cls._render_plotly(surface, fig)
        return fig

    @classmethod
    def _dispatch_mpl(cls, plot_type: str, data: Any, kwargs: Dict[str, Any]):
        args = tuple(data) if isinstance(data, (tuple, list)) else (data,)

        if plot_type in ("plot", "line"):
            from shared.plotting_engine.plot2d import plot as mpl_plot
            return mpl_plot(*args, **kwargs)
        if plot_type == "scatter":
            from shared.plotting_engine.plot2d import scatter
            return scatter(*args, **kwargs)
        if plot_type in ("hist", "histogram"):
            from shared.plotting_engine.plot2d import histogram
            return histogram(*args, **kwargs)
        if plot_type == "heatmap":
            from shared.plotting_engine.plot2d import heatmap
            return heatmap(*args, **kwargs)
        if plot_type in ("imagesc", "imshow", "contour", "contourf", "quiver", "streamline"):
            module = __import__("shared.plotting_engine.plot2d", fromlist=[plot_type])
            return getattr(module, plot_type)(*args, **kwargs)

        ax = plot_manager.prepare_plot(is_3d=plot_type in ("vector_field_3d", "contour3d"))
        if ax is None:
            return None
        if plot_type in ("vector_field", "quiver"):
            return ax.quiver(*args, **kwargs)
        return ax.plot(*args, **kwargs)

    @staticmethod
    def _render_plotly(surface, fig) -> None:
        if hasattr(surface, "render_figure"):
            surface.render_figure(fig)
            return
        if hasattr(surface, "switch_backend") and hasattr(surface, "get_plotly_widget"):
            surface.switch_backend(PLOTLY_BACKEND)
            surface.get_plotly_widget().render_figure(fig)
            return
        if hasattr(surface, "render"):
            surface.render(fig)
            return
        raise RuntimeError("Active plotting surface does not support Plotly rendering.")

    @staticmethod
    def _xy_args(args):
        if len(args) == 1:
            y = np.asarray(args[0]).flatten()
            x = np.arange(1, y.size + 1)
            return x, y
        if len(args) >= 2:
            return np.asarray(args[0]).flatten(), np.asarray(args[1]).flatten()
        raise ValueError("Plot requires at least one data argument.")

    @staticmethod
    def _xyz_args(args):
        if len(args) < 3:
            raise ValueError("3D plots require x, y, and z data.")
        return np.asarray(args[0]).flatten(), np.asarray(args[1]).flatten(), np.asarray(args[2]).flatten()

    @staticmethod
    def _surface_args(args):
        if len(args) == 1:
            z = np.asarray(args[0])
            rows, cols = z.shape
            x, y = np.meshgrid(np.arange(cols), np.arange(rows))
            return x, y, z
        if len(args) >= 3:
            return np.asarray(args[0]), np.asarray(args[1]), np.asarray(args[2])
        raise ValueError("Surface plots require Z or X, Y, Z data.")

    @staticmethod
    def _point_indices(length: int):
        return np.arange(int(length))


smart_plot = plot
