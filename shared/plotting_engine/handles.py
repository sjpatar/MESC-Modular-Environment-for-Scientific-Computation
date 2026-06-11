"""
MATLAB-style Handle Graphics System
==================================

This module defines persistent graphics handles used by plotting
functions (plot, scatter, surf, etc.).

Design rules:
- Handles are lightweight Python objects
- Wrap backend-specific artists (e.g. Matplotlib)
- Support MATLAB-style set/get semantics
- Backend-agnostic
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Union, List
import numpy as np
from shared.symbolic_core.arrays import MatlabArray


# ============================================================
# HELPERS
# ============================================================

def _unwrap(arg):
    if isinstance(arg, MatlabArray):
        return arg._data
    if isinstance(arg, (list, tuple)):
        return np.asarray(arg)
    return arg

def _ensure_flat_if_vector(val):
    """
    If val is a 2D numpy array that is effectively a vector (1xN or Nx1),
    flatten it to 1D. This ensures Matplotlib Line2D gets (N,) instead of (1,N).
    """
    val = _unwrap(val)
    if isinstance(val, np.ndarray) and val.ndim == 2:
        if val.shape[0] == 1 or val.shape[1] == 1:
            return val.flatten()
    return val

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
        "FaceAlpha": "alpha",
        "AlphaData": "alpha",
        "String": "text",
        "HorizontalAlignment": "horizontalalignment",
        "VerticalAlignment": "verticalalignment"
    }
    out = {}
    for k, v in kwargs.items():
        # Defensive check: ensure key is string
        if not isinstance(k, str):
            continue
            
        key = k.strip("'")
        out[mapping.get(key, key)] = _unwrap(v)
    return out


# ============================================================
# BASE HANDLE
# ============================================================

class GraphicsHandle:
    """
    Base class for all graphics handles.

    A handle wraps a backend object (artist) and exposes
    MATLAB-style property access.
    """

    def __init__(self, artist: Any, *, parent=None):
        self._artist = artist
        self._parent = parent
        self._props: Dict[str, Any] = {}

    # --------------------------------------------------------
    # Core API
    # --------------------------------------------------------

    def set(self, **kwargs):
        """
        set(h, 'Property', value, ...)
        Supports live update of data: set(h, XData=..., YData=..., CData=...)
        """
        # 1. Update internal props dict
        for k, v in kwargs.items():
            if isinstance(k, str):
                self._props[k] = v

        # 2. Handle Data Updates (Explicit Matplotlib Mapping)
        if 'XData' in kwargs:
            try:
                val = _ensure_flat_if_vector(kwargs['XData'])
                if hasattr(self._artist, 'set_xdata'):
                    self._artist.set_xdata(val)
                if hasattr(self._artist, 'set_x'):
                    self._artist.set_x(val)
                if hasattr(self._artist, 'set_position'):
                    pos = list(self._artist.get_position())
                    pos[0] = val
                    self._artist.set_position(pos)
            except Exception:
                pass 
        
        if 'YData' in kwargs:
            try:
                val = _ensure_flat_if_vector(kwargs['YData'])
                if hasattr(self._artist, 'set_ydata'):
                    self._artist.set_ydata(val)
                if hasattr(self._artist, 'set_y'):
                    self._artist.set_y(val)
                if hasattr(self._artist, 'set_position'):
                    pos = list(self._artist.get_position())
                    pos[1] = val
                    self._artist.set_position(pos)
            except Exception:
                pass

        if 'ZData' in kwargs:
            try:
                val = _ensure_flat_if_vector(kwargs['ZData'])
                if hasattr(self._artist, 'set_3d_properties'):
                    self._artist.set_3d_properties(val, 'z')
            except Exception:
                pass

        # --- FIX START: Handle CData (Color Data) ---
        if 'CData' in kwargs:
            try:
                val = _unwrap(kwargs['CData'])
                
                # Case 1: Images (imagesc, imshow)
                if hasattr(self._artist, 'set_data'):
                    self._artist.set_data(val)
                    
                    # [CRITICAL FIX] Auto-scale colors for animations
                    # Matplotlib set_data() does NOT auto-update limits. 
                    # We must manually update clim to match the new data range.
                    if hasattr(self._artist, 'set_clim'):
                        if hasattr(val, 'min') and hasattr(val, 'max'):
                             # Update limits to full range of new data
                             self._artist.set_clim(val.min(), val.max())

                # Case 2: Collections/Mesh (scatter, surf, pcolor)
                elif hasattr(self._artist, 'set_array'):
                    # Collections often need flattened arrays
                    if hasattr(val, 'flatten') and not hasattr(self._artist, 'set_z'): 
                        self._artist.set_array(val.flatten())
                        # Auto-scale for scatter/mesh as well
                        if hasattr(self._artist, 'autoscale'):
                             self._artist.autoscale()
                    else:
                        self._artist.set_array(val)
                        if hasattr(self._artist, 'autoscale'):
                             self._artist.autoscale()

            except Exception:
                pass
        # --- FIX END ---

        # 3. Handle Text Updates
        if 'String' in kwargs:
             if hasattr(self._artist, 'set_text'):
                 self._artist.set_text(kwargs['String'])

        # 4. Handle Style Updates (Color, LineWidth, etc.)
        # Exclude data keys from style processing
        data_keys = ['XData', 'YData', 'ZData', 'CData', 'String']
        style_args = {k: v for k, v in kwargs.items() if k not in data_keys}
        
        if style_args:
            mpl_kwargs = _map_matlab_kwargs(style_args)
            try:
                self._artist.update(mpl_kwargs)
            except Exception:
                # Fallback: try individual setters for unmapped props
                for k, v in mpl_kwargs.items():
                    self._set_property(k, v)

    def get(self, name: Optional[str] = None):
        """
        get(h)
        get(h, 'Property')
        """
        if name is None:
            return dict(self._props)
        return self._props.get(name)

    # --------------------------------------------------------
    # Internal property routing
    # --------------------------------------------------------

    def _set_property(self, name: str, value: Any):
        """
        Route property to backend artist if possible.
        """
        # Try common matplotlib patterns
        setter = f"set_{name.lower()}"
        if hasattr(self._artist, setter):
            try:
                getattr(self._artist, setter)(value)
                return
            except Exception:
                pass

        # Fallback: direct attribute
        try:
            setattr(self._artist, name, value)
        except Exception:
    
            pass

    def __getattr__(self, name: str):
        # 1. Prevent infinite recursion for internal Python attributes
        if name.startswith('_'):
            raise AttributeError(name)
        
        # 2. Try to get from tracked properties dict
        val = self.get(name)
        if val is not None:
            return val
            
        # 3. Fallback: Map MATLAB name to Matplotlib getter and call it
        try:
            mpl_name = _map_matlab_kwargs({name: None}).copy().popitem()[0]
            getter = f"get_{mpl_name}"
            if hasattr(self._artist, getter):
                return getattr(self._artist, getter)()
        except Exception:
            pass
            
        raise AttributeError(f"GraphicsHandle has no property '{name}'")

    def __setattr__(self, name: str, value: Any):
        # Protect internal properties
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            # Route through the robust set() method you already built
            self.set(**{name: value})
            
            # [CRITICAL] Auto-trigger UI redraw when a property changes
            from .state import plot_manager
            plot_manager.request_draw()


# ============================================================
# HANDLE TYPES
# ============================================================

class LineHandle(GraphicsHandle): pass
class ScatterHandle(GraphicsHandle): pass
class SurfaceHandle(GraphicsHandle): pass
class TextHandle(GraphicsHandle): pass
class AxesHandle(GraphicsHandle): pass
class FigureHandle(GraphicsHandle): pass


# ============================================================
# MATLAB-STYLE FREE FUNCTIONS
# ============================================================

def set(handle: Union[GraphicsHandle, List[GraphicsHandle]], *args, **kwargs):
    """
    MATLAB-style set(h, ...)
    Supports:
      set(h, 'Name', Value, ...)
      set(h, Name=Value, ...)
      set([h1, h2], ...)  <-- Arrays of handles
    """
    # Parse positional Name, Value pairs
    props = {}
    if len(args) > 0:
        for i in range(0, len(args), 2):
            if i + 1 < len(args):
                # Ensure key is hashable (string)
                key = args[i]
                if isinstance(key, str):
                    props[key] = args[i+1]
    
    # Merge with kwargs
    props.update(kwargs)
    
    # Delegate to handle(s)
    if isinstance(handle, (list, tuple, np.ndarray)):
        for h in handle:
            if hasattr(h, 'set'):
                h.set(**props)
    elif hasattr(handle, 'set'):
        handle.set(**props)
    else:
        pass


def get(handle: GraphicsHandle, name: Optional[str] = None):
    """
    MATLAB-style get(h)
    """
    if hasattr(handle, 'get'):
        return handle.get(name)
    return None