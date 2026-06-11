"""
MATLAB-style 2D plotting API for Mathex.

FINAL, ENGINE-COMPLIANT VERSION.

Rules:
- NO widget access
- NO canvas access
- NO drawing / flushing
- ONLY request draws via PlotStateManager
"""

import numpy as np
import matplotlib.pyplot as plt

from shared.symbolic_core.arrays import MatlabArray
from .state import plot_manager
from shared.plotting_engine.handles import (
    LineHandle, GraphicsHandle, ScatterHandle, TextHandle
)
from .text_support import apply_script_font_kwargs, apply_script_font_to_artist
from ides.mathex.language.locale import tr


# ============================================================
# HELPERS
# ============================================================

def _unwrap(arg):
    if isinstance(arg, MatlabArray):
        return arg._data
    if isinstance(arg, (list, tuple)):
        return np.asarray(arg)
    return arg


def _map_matlab_kwargs(kwargs):
    mapping = {
        "LineWidth": "linewidth",
        "LineStyle": "linestyle",
        "MarkerSize": "markersize",
        "SizeData": "s",
        "MarkerFaceColor": "markerfacecolor",
        "MarkerEdgeColor": "markeredgecolor",
        "Color": "color",
        "Marker": "marker",
        "Location": "loc",
        "FontSize": "fontsize",
        "FontWeight": "fontweight",
        "FaceColor": "facecolor",
        "EdgeColor": "edgecolor",
        "HorizontalAlignment": "horizontalalignment",
        "VerticalAlignment": "verticalalignment"
    }
    out = {}
    for k, v in kwargs.items():
        key = k.strip("'") if isinstance(k, str) else k
        out[mapping.get(key, key)] = _unwrap(v)
    return out


def _is_format_string(s):
    if not isinstance(s, str):
        return False
    valid = set("rgbcmykw" + "o+*.xsd^v><ph" + "-:")
    return 1 <= len(s) <= 4 and set(s).issubset(valid)


def _parse_args(args):
    data, kw = [], {}
    i = 0
    while i < len(args):
        v = _unwrap(args[i])
        if isinstance(v, str) and not _is_format_string(v) and len(data) >= 1:
            if i + 1 < len(args):
                kw[v] = args[i + 1]
                i += 2
                continue
        data.append(v)
        i += 1
    return data, _map_matlab_kwargs(kw)


def _ensure_vector_flatness(args):
    """
    MATLAB compatibility: Flatten 1xN or Nx1 arrays to 1D.
    Matplotlib treats (1,N) as N lines of 1 point (columns).
    We want 1 line of N points.
    """
    cleaned = []
    for a in args:
        if isinstance(a, np.ndarray) and a.ndim == 2:
            # Check if vector-like (one dim is 1, other is > 1)
            # or if it's empty or scalar-like
            if a.shape[0] == 1 or a.shape[1] == 1:
                cleaned.append(a.flatten())
            else:
                cleaned.append(a)
        else:
            cleaned.append(a)
    return cleaned


# ============================================================
# CORE PLOTS
# ============================================================

def plot(*args, **kwargs):
    ax = plot_manager.prepare_plot(is_3d=False)
    if ax is None:
        return

    aa, kk = _parse_args(args)
    kk.update(_map_matlab_kwargs(kwargs))
    
    # Flatten vectors to prevent plotting N columns as N lines
    aa = _ensure_vector_flatness(aa)

    if len(aa) == 1:
        y = np.asarray(aa[0]).squeeze()
        if y.ndim != 1:
            y = y.reshape(-1)
        x = np.arange(1, y.size + 1)
        lines = ax.plot(x, y, **kk)
    else:
        lines = ax.plot(*aa, **kk)

    handles = [LineHandle(line, parent=ax) for line in lines]

    plot_manager.request_draw()
    return handles[0] if len(handles) == 1 else handles


def line(*args, **kwargs):
    return plot(*args, **kwargs)


def scatter(*args, **kwargs):
    ax = plot_manager.prepare_plot(is_3d=False)
    if ax is None:
        return

    raw = [_unwrap(x) for x in args if not (isinstance(x, str) and x.lower() == "filled")]
    aa, kk = _parse_args(raw)
    kk.update(_map_matlab_kwargs(kwargs))
    
    # Flatten inputs for scatter too (x, y must match)
    aa = _ensure_vector_flatness(aa)

    sc = ax.scatter(*aa, **kk)
    plot_manager.request_draw()
    return ScatterHandle(sc, parent=ax)


def errorbar(x, y, yerr, **k):
    ax = plot_manager.prepare_plot(is_3d=False)
    if ax is None:
        return

    args = _ensure_vector_flatness([_unwrap(x), _unwrap(y), _unwrap(yerr)])
    
    ax.errorbar(
        args[0],
        args[1],
        yerr=args[2],
        **_map_matlab_kwargs(k),
    )
    plot_manager.request_draw()


def stem(x, y, **k):
    ax = plot_manager.prepare_plot(is_3d=False)
    if ax is None:
        return
    
    args = _ensure_vector_flatness([_unwrap(x), _unwrap(y)])

    ax.stem(args[0], args[1], **_map_matlab_kwargs(k))
    plot_manager.request_draw()


def stairs(x, y, **k):
    ax = plot_manager.prepare_plot(is_3d=False)
    if ax is None:
        return

    args = _ensure_vector_flatness([_unwrap(x), _unwrap(y)])
    
    ax.stairs(args[0], args[1], **_map_matlab_kwargs(k))
    plot_manager.request_draw()


# ============================================================
# TEXT & ANNOTATION
# ============================================================

def text(x, y, s, **kwargs):
    """
    text(x, y, str) - Add text to current plot.
    """
    ax = plot_manager.prepare_plot(is_3d=False)
    if ax is None: return

    # Unwrap args
    x = float(_unwrap(x)) if hasattr(_unwrap(x), 'item') else _unwrap(x)
    y = float(_unwrap(y)) if hasattr(_unwrap(y), 'item') else _unwrap(y)
    s = str(_unwrap(s))
    
    # Map kwargs
    kw = _map_matlab_kwargs(kwargs)
    
    # Defaults for MATLAB look
    if 'fontsize' not in kw: kw['fontsize'] = 10
    kw = apply_script_font_kwargs(s, kw)
    
    t = ax.text(x, y, s, **kw)
    plot_manager.request_draw()
    return TextHandle(t, parent=ax)


def title(t, **kwargs):
    ax = plot_manager.gca()
    if ax:
        kw = _map_matlab_kwargs(kwargs)
        # Smart defaults for dark theme
        if 'fontsize' not in kw: kw['fontsize'] = 12
        if 'fontweight' not in kw: kw['fontweight'] = 'bold'
        if 'color' not in kw: kw['color'] = 'white'
        label = str(_unwrap(t))
        kw = apply_script_font_kwargs(label, kw)
        title_artist = ax.set_title(label, **kw)
        apply_script_font_to_artist(title_artist, label)
        plot_manager.request_draw()


def xlabel(t, **kwargs):
    ax = plot_manager.gca()
    if ax:
        kw = _map_matlab_kwargs(kwargs)
        if 'color' not in kw: kw['color'] = '#eeeeee'
        label = str(_unwrap(t))
        kw = apply_script_font_kwargs(label, kw)
        text_artist = ax.set_xlabel(label, **kw)
        apply_script_font_to_artist(text_artist, label)
        plot_manager.request_draw()


def ylabel(t, **kwargs):
    ax = plot_manager.gca()
    if ax:
        kw = _map_matlab_kwargs(kwargs)
        if 'color' not in kw: kw['color'] = '#eeeeee'
        label = str(_unwrap(t))
        kw = apply_script_font_kwargs(label, kw)
        text_artist = ax.set_ylabel(label, **kw)
        apply_script_font_to_artist(text_artist, label)
        plot_manager.request_draw()


# ============================================================
# INTERACTIVE INPUT
# ============================================================

def ginput(n=1):
    """
    [x, y] = ginput(n) - Get n clicks from the user.
    Blocks execution until clicks are received or timeout.
    """
    fig_state = plot_manager._get_fig_state()
    widget = fig_state.widget
    
    # Only works if we have a real UI widget with ginput method
    if hasattr(widget, 'ginput'):
        pts = widget.ginput(n=int(_unwrap(n)))
        if not pts:
            return np.array([])
        # Convert to numpy array Nx2
        return np.array(pts)
    return np.array([])


def gtext(s, **kwargs):
    """
    gtext('string') - Place text with mouse click.
    """
    print("Click to place text...")
    pts = ginput(1)
    if len(pts) > 0:
        return text(pts[0][0], pts[0][1], s, **kwargs)


# ============================================================
# VECTOR FIELDS (PHYSICS)
# ============================================================

def quiver(x, y, u, v, **kwargs):
    """
    quiver(x, y, u, v) - Quiver plot (vector field arrows).
    """
    ax = plot_manager.prepare_plot(is_3d=False)
    if ax is None:
        return

    q = ax.quiver(
        _unwrap(x), _unwrap(y), _unwrap(u), _unwrap(v),
        **_map_matlab_kwargs(kwargs)
    )
    plot_manager.request_draw()
    return GraphicsHandle(q, parent=ax)


def streamline(x, y, u, v, **kwargs):
    """
    streamline(x, y, u, v) - Streamlines from vector data.
    """
    ax = plot_manager.prepare_plot(is_3d=False)
    if ax is None:
        return

    kw = _map_matlab_kwargs(kwargs)
    color = kw.pop('color', None)
    
    sp = ax.streamplot(
        _unwrap(x), _unwrap(y), _unwrap(u), _unwrap(v),
        color=color,
        **kw
    )
    plot_manager.request_draw()
    return GraphicsHandle(sp, parent=ax)


# ============================================================
# BAR / AREA
# ============================================================

def bar(x, y, width=0.8, **k):
    ax = plot_manager.prepare_plot(is_3d=False)
    if ax is None:
        return

    args = _ensure_vector_flatness([_unwrap(x), _unwrap(y)])
    ax.bar(args[0], args[1], width=width, **_map_matlab_kwargs(k))
    plot_manager.request_draw()


def barh(x, y, height=0.8, **k):
    ax = plot_manager.prepare_plot(is_3d=False)
    if ax is None:
        return

    args = _ensure_vector_flatness([_unwrap(x), _unwrap(y)])
    ax.barh(args[0], args[1], height=height, **_map_matlab_kwargs(k))
    plot_manager.request_draw()


def barstacked(Y, **k):
    ax = plot_manager.prepare_plot(is_3d=False)
    if ax is None:
        return

    Y = np.asarray(_unwrap(Y))
    x = np.arange(Y.shape[1])
    bottom = np.zeros(Y.shape[1])

    for i in range(Y.shape[0]):
        ax.bar(x, Y[i], bottom=bottom, **_map_matlab_kwargs(k))
        bottom += Y[i]

    plot_manager.request_draw()


def area(x, y, **k):
    ax = plot_manager.prepare_plot(is_3d=False)
    if ax is None:
        return

    args = _ensure_vector_flatness([_unwrap(x), _unwrap(y)])
    ax.fill_between(args[0], args[1], **_map_matlab_kwargs(k))
    plot_manager.request_draw()


def areastacked(Y, **k):
    ax = plot_manager.prepare_plot(is_3d=False)
    if ax is None:
        return

    Y = np.asarray(_unwrap(Y))
    x = np.arange(Y.shape[1])
    S = np.cumsum(Y, axis=0)

    for i in range(Y.shape[0]):
        lo = S[i - 1] if i > 0 else None
        ax.fill_between(x, lo, S[i], **_map_matlab_kwargs(k))

    plot_manager.request_draw()


# ============================================================
# HIST / PIE / BOX
# ============================================================

def histogram(x, bins=10, **k):
    ax = plot_manager.prepare_plot(is_3d=False)
    if ax is None:
        return
    
    x_val = np.asarray(_unwrap(x)).flatten()
    ax.hist(x_val, bins=bins, **_map_matlab_kwargs(k))
    plot_manager.request_draw()


def hist(x, bins=10, **k):
    histogram(x, bins=bins, **k)


def boxplot(x, **k):
    ax = plot_manager.prepare_plot(is_3d=False)
    if ax is None:
        return

    ax.boxplot(_unwrap(x), **_map_matlab_kwargs(k))
    plot_manager.request_draw()


def pie(x, labels=None, **k):
    ax = plot_manager.prepare_plot(is_3d=False)
    if ax is None:
        return
    
    x_val = np.asarray(_unwrap(x)).flatten()
    ax.pie(x_val, labels=labels, **_map_matlab_kwargs(k))
    plot_manager.request_draw()


# ============================================================
# IMAGE / CONTOUR
# ============================================================

def contour(*a, **k):
    ax = plot_manager.prepare_plot(is_3d=False)
    if ax is None:
        return

    aa, kk = _parse_args(a)
    kk.update(_map_matlab_kwargs(k))
    
    if len(aa) >= 3:
        aa = list(aa)
        aa[0] = _ensure_vector_flatness([aa[0]])[0]
        aa[1] = _ensure_vector_flatness([aa[1]])[0]
    
    ax.contour(*aa, **kk)
    plot_manager.request_draw()


def contourf(*a, **k):
    ax = plot_manager.prepare_plot(is_3d=False)
    if ax is None:
        return

    aa, kk = _parse_args(a)
    kk.update(_map_matlab_kwargs(k))
    
    if len(aa) >= 3:
        aa = list(aa)
        aa[0] = _ensure_vector_flatness([aa[0]])[0]
        aa[1] = _ensure_vector_flatness([aa[1]])[0]

    ax.contourf(*aa, **kk)
    plot_manager.request_draw()


def pcolor(*a, **k):
    ax = plot_manager.prepare_plot(is_3d=False)
    if ax is None:
        return

    aa, kk = _parse_args(a)
    kk.update(_map_matlab_kwargs(k))
    
    if len(aa) >= 3:
        aa = list(aa)
        aa[0] = _ensure_vector_flatness([aa[0]])[0]
        aa[1] = _ensure_vector_flatness([aa[1]])[0]

    ax.pcolor(*aa, **kk)
    plot_manager.request_draw()


def imagesc(*a, **k):
    """
    imagesc(C)
    imagesc(x, y, C)
    """
    ax = plot_manager.prepare_plot(is_3d=False)
    if ax is None:
        return

    aa, kk = _parse_args(a)
    kk.update(_map_matlab_kwargs(k))

    img_data = None

    # CRITICAL FIX: Handle imagesc(x, y, C)
    # Matplotlib imshow does not accept x, y as positional args
    if len(aa) == 3:
        x = _ensure_vector_flatness([aa[0]])[0]
        y = _ensure_vector_flatness([aa[1]])[0]
        img_data = _unwrap(aa[2])

        # Map bounds to extent=[xmin, xmax, ymin, ymax]
        if x.size > 1 and y.size > 1:
            extent = [x.min(), x.max(), y.min(), y.max()]
            kk['extent'] = extent
    
    elif len(aa) == 1:
        img_data = _unwrap(aa[0])
    
    else:
        # Fallback
        if len(aa) > 0:
            img_data = _unwrap(aa[0])

    if img_data is None:
        return

    # Defaults matching MATLAB behavior
    if 'aspect' not in kk:
        kk['aspect'] = 'auto'
    if 'origin' not in kk:
        # [FIX] strict MATLAB compliance sets origin to upper for imagesc
        kk['origin'] = 'upper'

    im = ax.imshow(img_data, **kk)
    
    plot_manager.request_draw()
    # Return handle so set(h, 'CData', ...) works
    return GraphicsHandle(im, parent=ax)


def imshow(img, **k):
    ax = plot_manager.prepare_plot(is_3d=False)
    if ax is None:
        return

    ax.imshow(np.asarray(_unwrap(img)), origin="upper", **_map_matlab_kwargs(k))
    plot_manager.request_draw()


def heatmap(Z, **k):
    ax = plot_manager.prepare_plot(is_3d=False)
    if ax is None:
        return

    ax.imshow(np.asarray(_unwrap(Z)), aspect="auto", origin="lower", **_map_matlab_kwargs(k))
    plot_manager.request_draw()


# ============================================================
# MULTI-AXIS / GROUPED
# ============================================================

def subplot(m, n, p):
    ax = plot_manager.subplot(_unwrap(m), _unwrap(n), _unwrap(p))
    plot_manager.request_draw(immediate=True)
    return ax


def gscatter(x, y, g, **k):
    ax = plot_manager.prepare_plot(is_3d=False)
    if ax is None:
        return

    x = np.asarray(_unwrap(x))
    y = np.asarray(_unwrap(y))
    g = np.asarray(_unwrap(g))

    groups = np.unique(g)
    for idx, grp in enumerate(groups):
        sel = g == grp
        ax.scatter(
            x[sel],
            y[sel],
            color=f"C{idx % 10}",
            **_map_matlab_kwargs(k),
        )

    plot_manager.request_draw()


def plotmatrix(X):
    X = np.asarray(_unwrap(X))
    n = X.shape[1]

    fig = plot_manager.gcf()
    fig.clf()

    for i in range(n):
        for j in range(n):
            ax = fig.add_subplot(n, n, i * n + j + 1)
            if i == j:
                ax.hist(X[:, i])
            else:
                ax.scatter(X[:, j], X[:, i], s=6)

    plot_manager.request_draw(immediate=True)


# ============================================================
# AXES / DECORATION (UTILITIES)
# ============================================================

def grid(mode="on"):
    plot_manager.grid(mode)
    plot_manager.request_draw()


def xlim(lim):
    ax = plot_manager.gca()
    if ax:
        # [FIX] Flatten input array to prevent unpacking errors (e.g. from 2D row vectors)
        val = np.asarray(_unwrap(lim)).flatten()
        if val.size >= 2:
            ax.set_xlim(val[0], val[1])
        plot_manager.request_draw()


def ylim(lim):
    ax = plot_manager.gca()
    if ax:
        # [FIX] Flatten input array to prevent unpacking errors
        val = np.asarray(_unwrap(lim)).flatten()
        if val.size >= 2:
            ax.set_ylim(val[0], val[1])
        plot_manager.request_draw()


def axis(mode):
    """
    axis([xmin xmax ymin ymax])
    axis([xmin xmax ymin ymax zmin zmax])
    axis on / off / equal / tight
    """
    ax = plot_manager.gca()
    if ax is None:
        return

    val = _unwrap(mode)
    
    # [FIX] Handle numeric array input for axis limits
    if isinstance(val, (list, tuple, np.ndarray)):
        arr = np.asarray(val).flatten()
        # 2D limits
        if arr.size == 4:
            ax.set_xlim(arr[0], arr[1])
            ax.set_ylim(arr[2], arr[3])
        # 3D limits (or 2D fallback)
        elif arr.size == 6:
            # Check if axis is 3D compatible
            if hasattr(ax, 'set_zlim'):
                ax.set_xlim(arr[0], arr[1])
                ax.set_ylim(arr[2], arr[3])
                ax.set_zlim(arr[4], arr[5])
            else:
                # Fallback for 2D axes receiving 3D limits: just ignore Z
                ax.set_xlim(arr[0], arr[1])
                ax.set_ylim(arr[2], arr[3])
    else:
        # String mode
        try:
            ax.axis(str(mode).lower())
        except Exception:
            pass

    plot_manager.request_draw()


def legend(*args, **kwargs):
    ax = plot_manager.gca()
    if ax:
        labels = [_unwrap(x) for x in args if isinstance(_unwrap(x), str)]
        kw = _map_matlab_kwargs(kwargs)
        legend_obj = None
        
        if labels:
            # First, see if matplotlib can natively find the handles
            handles, _ = ax.get_legend_handles_labels()
            
            if not handles:
                # Manual fallback aggregation
                handles = []
                handles.extend(ax.lines)
                handles.extend(ax.collections)
                handles.extend(ax.patches)
            
            if handles:
                # [FIX] The Legend Bug: Prevent silent array-mismatch failures
                # by safely slicing handles and labels to the minimum common length.
                min_len = min(len(handles), len(labels))
                legend_obj = ax.legend(handles=handles[:min_len], labels=labels[:min_len], **kw)
            else:
                legend_obj = ax.legend(labels, **kw)
        else:
            # Auto-legend
            legend_obj = ax.legend(**kw)

        if legend_obj is not None:
            for text_artist in legend_obj.get_texts():
                apply_script_font_to_artist(text_artist)
            apply_script_font_to_artist(legend_obj.get_title())
            
        plot_manager.request_draw()


def colorbar():
    """
    MATLAB-style colorbar.
    """
    ax = plot_manager.gca()
    if ax is None:
        return

    # Find last mappable (imshow, contourf, pcolor, etc.)
    mappable = None
    for artist in reversed(ax.get_children()):
        if hasattr(artist, "get_array"):
            mappable = artist
            break

    if mappable is None:
        return

    ax.figure.colorbar(mappable, ax=ax)
    plot_manager.request_draw()


def colormap(name):
    """
    colormap('jet') - Set the current figure's colormap.
    """
    name = str(_unwrap(name))
    plt.rcParams['image.cmap'] = name # Set global default
    
    # Update existing plots
    fig = plot_manager.gcf()
    if fig:
        for ax in fig.axes:
            for artist in ax.get_children():
                if hasattr(artist, 'set_cmap'):
                    artist.set_cmap(name)
    plot_manager.request_draw()


def caxis(limits):
    """
    caxis([min max]) - Set the color axis scaling limits.
    """
    lims = _unwrap(limits)
    vmin, vmax = float(lims[0]), float(lims[1])
    
    fig = plot_manager.gcf()
    if fig:
        for ax in fig.axes:
            for artist in ax.get_children():
                if hasattr(artist, 'set_clim'):
                    artist.set_clim(vmin, vmax)
    plot_manager.request_draw()

def backend(target: str):
    """
    backend('plotly') - Switch to interactive WebGL rendering (best for 3D).
    backend('matplotlib') - Switch to native rendering (best for 2D/Animations).
    """
    from .state import plot_manager
    target = str(target).lower()
    
    if target not in ['matplotlib', 'plotly']:
        raise ValueError("Backend must be 'matplotlib' or 'plotly'")
        
    fig_state = plot_manager._get_fig_state()
    
    # Send signal to the UI (PlotDock) to swap the active QStackedWidget
    if fig_state and hasattr(fig_state.widget, 'switch_backend'):
        fig_state.widget.switch_backend(target)
        plot_manager.request_draw(immediate=True)
    else:
        print(f"{tr('console_warning_prefix')}: {tr('warning_backend_hot_swap', target=target)}")
