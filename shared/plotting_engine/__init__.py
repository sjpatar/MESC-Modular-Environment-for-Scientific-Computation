"""
Mathex unified plotting namespace.

Exports MATLAB-style plotting APIs so user code can call:
    plot(), surf(), figure(), hold(), axis(), view(), etc.

This namespace is:
- engine-compliant
- backend-agnostic
- UI / CLI safe
"""

# ============================================================
# STATE (INTERNAL – not exported)
# ============================================================

from .state import plot_manager


# ============================================================
# HANDLE GRAPHICS (MATLAB set/get)
# ============================================================

from .handles import set, get


# ============================================================
# 2D PLOTTING
# ============================================================

from .plot2d import (
    plot, line, scatter,
    bar, barh, barstacked,
    area, areastacked,
    histogram, hist, pie,
    errorbar, stem, stairs, boxplot,
    contour, contourf, pcolor,
    imagesc, imshow, heatmap,
    gscatter, plotmatrix,
    subplot, title, xlabel, ylabel,
    grid, xlim, ylim, axis,
    colorbar, legend,
    # NEW PHYSICS & VISUALS
    quiver, streamline, colormap, caxis
)


# ============================================================
# 3D PLOTTING (ONLY IMPLEMENTED FUNCTIONS)
# ============================================================

from .plot3d import (
    plot3, scatter3,
    surf, mesh,
    contour3,
    contourf3,
    view,
    axis as axis3,
    shading,
    # [FIX] Ensure lighting/camlight/zlabel are exported
    lighting, camlight,
    zlabel, zlim,
    # NEW PHYSICS
    quiver3
)


# ============================================================
# FIGURE MANAGEMENT
# ============================================================

from .figure import (
    figure, gcf, clf, close, closeall
)

from .router import smart_plot, UniversalPlotRouter


# ============================================================
# MATLAB-STYLE CONVENIENCE WRAPPERS
# ============================================================

def hold(mode="on"):
    """
    hold on / hold off
    """
    plot_manager.hold(mode)


def brush(mode="on"):
    """
    brush on / brush off / brush lasso

    Enables Plotly rectangle/lasso selection on the active figure surface.
    Matplotlib figures ignore this command gracefully.
    """
    target = str(mode or "on").lower()
    widget = plot_manager.widget
    if widget is None:
        try:
            plot_manager.activate_figure(1, backend="plotly")
            widget = plot_manager.widget
        except Exception:
            return target

    if hasattr(widget, "set_brush_mode"):
        widget.set_brush_mode(target)
    elif hasattr(widget, "get_plotly_widget"):
        widget.get_plotly_widget().set_brush_mode(target)

    return target


brush.__mathex_command__ = True


# ============================================================
# ANIMATION
# ============================================================

try:
    from .animation import (
        drawnow, getframe, movie,
        animatedline, addpoints, clearpoints,
        comet, comet3, drawnowlimit
    )
except Exception:
    def drawnow(*a, **k): ...
    def getframe(*a, **k): ...
    def movie(*a, **k): ...
    def animatedline(*a, **k): ...
    def addpoints(*a, **k): ...
    def clearpoints(*a, **k): ...
    def comet(*a, **k): ...
    def comet3(*a, **k): ...
    def drawnowlimit(*a, **k): ...


# ============================================================
# PUBLIC API
# ============================================================

__all__ = [
    # handle graphics
    "set", "get",

    # 2D
    "plot", "line", "scatter",
    "bar", "barh", "barstacked",
    "area", "areastacked",
    "histogram", "hist", "pie",
    "errorbar", "stem", "stairs", "boxplot",
    "contour", "contourf", "pcolor",
    "imagesc", "imshow", "heatmap",
    "gscatter", "plotmatrix",
    "subplot", "title", "xlabel", "ylabel", "zlabel",
    "grid", "xlim", "ylim", "zlim", "axis", 
    "colorbar", "legend",
    # New 2D
    "quiver", "streamline", "colormap", "caxis",

    # 3D
    "plot3", "scatter3",
    "surf", "mesh",
    "contour3", "contourf3",
    "view", "axis3", "shading",
    # New 3D
    "quiver3",
    "lighting", "camlight",

    # figures
    "figure", "gcf", "clf", "close", "closeall", "hold", "brush",
    "smart_plot", "UniversalPlotRouter",

    # animation
    "drawnow", "getframe", "movie",
    "animatedline", "addpoints", "clearpoints",
    "comet", "comet3", "drawnowlimit",
]
