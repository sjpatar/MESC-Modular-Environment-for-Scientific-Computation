"""
Mathex Animation Routines
===========================

MATLAB-compatible animation layer.
"""

import time
import numpy as np

from .state import plot_manager


# ============================================================
# HELPER: MATLAB ARG PARSER
# ============================================================

def _parse_matlab_args(args):
    """
    Separates MATLAB-style Name,Value pairs from positional args.
    Example: ('Color', 'r', 'LineWidth', 2) -> [], {'color': 'r', 'linewidth': 2}
    """
    pos_args = []
    kwargs = {}
    i = 0
    while i < len(args):
        # Check for Name,Value pair
        if isinstance(args[i], str) and i + 1 < len(args):
            key = args[i].lower()
            val = args[i+1]
            
            # Remap common MATLAB property names to Matplotlib
            mapping = {
                'linewidth': 'linewidth',
                'linestyle': 'linestyle',
                'color': 'color',
                'marker': 'marker',
                'markersize': 'markersize',
                'markerfacecolor': 'markerfacecolor',
                'markeredgecolor': 'markeredgecolor'
            }
            if key in mapping:
                kwargs[mapping[key]] = val
                i += 2
                continue
            
            # If not a known key, treat as positional
            pos_args.append(args[i])
            i += 1
        else:
            pos_args.append(args[i])
            i += 1
    return pos_args, kwargs


# ============================================================
# FRAME CONTAINER
# ============================================================

class Frame:
    """
    MATLAB-style frame container (getframe output).
    cdata is an HxWx4 uint8 array.
    """
    def __init__(self, cdata, colormap=None):
        self.cdata = cdata
        self.colormap = colormap


# ============================================================
# DRAWNOW
# ============================================================

def drawnow():
    """
    MATLAB drawnow.
    Requests an immediate draw AND blocks until it is complete.
    """
    plot_manager.request_draw(immediate=True, wait=True)
drawnow.__mathex_command__ = True

# ============================================================
# GETFRAME
# ============================================================

def getframe(ax_handle=None):
    """
    getframe()
    Captures the current figure as a Frame.
    """
    fig = plot_manager.gcf()
    if fig is None:
        raise RuntimeError("No active figure to capture.")

    # Force render before capture
    plot_manager.request_draw(immediate=True, wait=True)

    canvas = fig.canvas
    width, height = canvas.get_width_height()
    buf = canvas.buffer_rgba()

    arr = np.asarray(buf, dtype=np.uint8)
    try:
        arr = arr.reshape((height, width, 4))
    except Exception:
        fig_w, fig_h = fig.get_size_inches() * fig.get_dpi()
        arr = arr.reshape((int(fig_h), int(fig_w), 4))

    return Frame(cdata=arr)


# ============================================================
# MOVIE
# ============================================================

def movie(frames, num_plays=1, fps=12):
    """
    movie(F)
    """
    if not frames:
        return

    ax = plot_manager.gca()
    if ax is None:
        return

    delay = 1.0 / float(fps)

    img = ax.imshow(frames[0].cdata)
    plot_manager.request_draw(immediate=True, wait=True)

    for _ in range(int(num_plays)):
        for fr in frames:
            img.set_data(fr.cdata)
            plot_manager.request_draw(immediate=True, wait=True)
            time.sleep(delay)


# ============================================================
# COMET (2D / 3D)
# ============================================================

def comet(x, y=None, z=None, style="r", **kwargs):
    """
    comet(y)
    comet(x,y)
    comet(x,y,z)
    """
    if y is None:
        y = x
        x = np.arange(len(y))

    # [FIX] Flatten inputs to ensure 1D arrays
    X = np.asarray(x).flatten()
    Y = np.asarray(y).flatten()

    is3d = z is not None
    if is3d:
        Z = np.asarray(z).flatten()

    ax = plot_manager.prepare_plot(is_3d=is3d)
    if ax is None:
        return

    # Create empty lines
    if is3d:
        head, = ax.plot([], [], [], style, **kwargs)
        trail, = ax.plot([], [], [], style, alpha=0.6, **kwargs)
    else:
        head, = ax.plot([], [], style, **kwargs)
        trail, = ax.plot([], [], style, alpha=0.6, **kwargs)

    for i in range(len(X)):
        if is3d:
            if hasattr(head, "set_data_3d"):
                head.set_data_3d([X[i]], [Y[i]], [Z[i]])
                trail.set_data_3d(X[: i + 1], Y[: i + 1], Z[: i + 1])
            else:
                head.set_data([X[i]], [Y[i]])
                trail.set_data(X[: i + 1], Y[: i + 1])
        else:
            head.set_data([X[i]], [Y[i]])
            trail.set_data(X[: i + 1], Y[: i + 1])

        # Force axis scaling during animation
        try:
            ax.relim()
            ax.autoscale_view()
        except:
            pass

        plot_manager.request_draw(immediate=True, wait=True)
        time.sleep(0.01)

def comet3(*args, **kwargs):
    comet(*args, **kwargs)


# ============================================================
# ANIMATEDLINE
# ============================================================

class AnimatedLine:
    """
    MATLAB animatedline object.
    Supports 2D and 3D.
    """

    def __init__(self, *args, **kwargs):
        # 1. Prepare a 2D axis by default. A previous 3D plot must not leak
        # into animatedline(x, y); addpoints(..., z) promotes it to 3D later.
        ax = plot_manager.prepare_plot(is_3d=False)
        if ax is None:
            ax = plot_manager.gca(is_3d=False)

        self.ax = ax
        self.is_3d = False

        # 2. Parse MATLAB style args
        pos_args, parsed_kwargs = _parse_matlab_args(args)
        kwargs.update(parsed_kwargs)

        # 3. Handle Special Properties
        self.max_points = kwargs.pop('maximumnumpoints', None)
        if self.max_points is not None:
             self.max_points = int(self.max_points)

        self.x = []
        self.y = []
        self.z = [] # 3D support

        # 4. Create Line
        if self.is_3d:
            (self.line,) = ax.plot([], [], [], *pos_args, **kwargs)
        else:
            (self.line,) = ax.plot([], [], *pos_args, **kwargs)

        self._pos_args = pos_args
        self._line_kwargs = kwargs.copy()

    def _promote_to_3d(self):
        if self.is_3d:
            return

        try:
            if self.line is not None:
                self.line.remove()
        except Exception:
            pass

        ax = plot_manager.prepare_plot(is_3d=True)
        if ax is None:
            return

        self.ax = ax
        self.is_3d = True
        (self.line,) = ax.plot([], [], [], *self._pos_args, **self._line_kwargs)

    def addpoints(self, x, y, z=None):
        if self.line is None: return

        # [CRITICAL FIX] Aggressively flatten inputs.
        # This prevents shape (N, 1) errors in Matplotlib 3D projection.
        # tolist() on a flat array guarantees a simple list of floats.
        x_arr = np.asarray(x).flatten().tolist()
        y_arr = np.asarray(y).flatten().tolist()
        
        self.x.extend(x_arr)
        self.y.extend(y_arr)
        
        if z is not None:
            z_arr = np.asarray(z).flatten().tolist()
            self.z.extend(z_arr)
            if not self.is_3d:
                self._promote_to_3d()
        elif self.is_3d:
            self.z.extend([0.0] * len(x_arr))

        # Handle MaximumNumPoints (Sliding Window)
        if self.max_points is not None:
            if len(self.x) > self.max_points:
                trim = len(self.x) - self.max_points
                self.x = self.x[trim:]
                self.y = self.y[trim:]
                if self.is_3d:
                    self.z = self.z[trim:]

        # Update Data
        if self.is_3d:
            # Matplotlib 3D requires set_data_3d OR separate set_data/set_3d_properties
            if hasattr(self.line, "set_data_3d"):
                self.line.set_data_3d(self.x, self.y, self.z)
            else:
                self.line.set_data(self.x, self.y)
                self.line.set_3d_properties(self.z)
        else:
            self.line.set_data(self.x, self.y)

        # Force Autoscale
        try:
            self.ax.relim()
            self.ax.autoscale_view()
        except Exception:
            pass

    def clearpoints(self):
        self.x = []
        self.y = []
        self.z = []
        if self.line:
            if self.is_3d and hasattr(self.line, "set_data_3d"):
                self.line.set_data_3d([], [], [])
            else:
                self.line.set_data([], [])
            
            try:
                self.ax.relim()
                self.ax.autoscale_view()
            except Exception:
                pass


# -- GLOBAL HELPERS --

def animatedline(*args, **kwargs):
    return AnimatedLine(*args, **kwargs)

def addpoints(h, *args):
    """
    addpoints(h, x, y)
    addpoints(h, x, y, z)
    """
    if hasattr(h, 'addpoints'):
        h.addpoints(*args)

def clearpoints(h):
    if hasattr(h, 'clearpoints'):
        h.clearpoints()


# ============================================================
# DRAW RATE LIMITER
# ============================================================

_last_draw = 0.0

def drawnow_limiter(min_interval=0.03):
    global _last_draw
    now = time.time()
    if now - _last_draw >= float(min_interval):
        _last_draw = now
        plot_manager.request_draw(immediate=True, wait=True)

drawnowlimit = drawnow_limiter
