import numpy as np
import warnings
from shared.symbolic_core.arrays import MatlabArray

# Try to import scikit-image, fail gracefully if missing
try:
    from skimage import io, color, filters, transform, util
    HAS_SKIMAGE = True
except ImportError:
    HAS_SKIMAGE = False

def _ensure_skimage():
    if not HAS_SKIMAGE:
        raise ImportError("Image Processing Toolbox requires 'scikit-image'. Run: pip install scikit-image")

def imread(filename):
    _ensure_skimage()
    # skimage reads as RGB, MATLAB reads as RGB. Compatible.
    img = io.imread(str(filename))
    return MatlabArray(img)

def imshow(I, **kwargs):
    _ensure_skimage()
    import matplotlib.pyplot as plt
    img = I._data if isinstance(I, MatlabArray) else I
    plt.imshow(img, **kwargs)
    plt.axis('off')
    plt.show()

def rgb2gray(I):
    _ensure_skimage()
    img = I._data if isinstance(I, MatlabArray) else I
    # skimage returns float [0,1], MATLAB mimics input class.
    # We stick to float for precision.
    return MatlabArray(color.rgb2gray(img))

def imresize(I, scale):
    _ensure_skimage()
    img = I._data if isinstance(I, MatlabArray) else I
    # Handle scale factor or explicit shape
    if isinstance(scale, (int, float)):
        out = transform.rescale(img, scale, channel_axis=-1 if img.ndim==3 else None)
    else:
        out = transform.resize(img, scale)
    return MatlabArray(out)

def imfilter(A, h):
    _ensure_skimage()
    img = A._data if isinstance(A, MatlabArray) else A
    kernel = h._data if isinstance(h, MatlabArray) else h
    # mimic MATLAB 'replicate' padding by default
    return MatlabArray(filters.correlate(img, kernel, mode='nearest'))

# Register these in your session.py globals!