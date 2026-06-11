import numpy as np
from shared.symbolic_core.arrays import MatlabArray

def meshgrid(x, y=None):
    x_data = x._data if isinstance(x, MatlabArray) else np.array(x)
    if y is None:
        y_data = x_data
    else:
        y_data = y._data if isinstance(y, MatlabArray) else np.array(y)
    X, Y = np.meshgrid(x_data, y_data)
    return MatlabArray(X), MatlabArray(Y)

def sphere(n=20):
    theta = np.linspace(0, 2*np.pi, int(n)+1)
    phi = np.linspace(0, np.pi, int(n)+1)
    theta, phi = np.meshgrid(theta, phi)
    x = np.sin(phi) * np.cos(theta)
    y = np.sin(phi) * np.sin(theta)
    z = np.cos(phi)
    return MatlabArray(x), MatlabArray(y), MatlabArray(z)

def cylinder(r=1, n=20):
    theta = np.linspace(0, 2*np.pi, int(n)+1)
    x = r * np.cos(theta)
    y = r * np.sin(theta)
    X = np.array([x, x])
    Y = np.array([y, y])
    Z = np.array([np.zeros_like(x), np.ones_like(x)])
    return MatlabArray(X), MatlabArray(Y), MatlabArray(Z)

def gradient(f, *varargs):
    data = f._data if isinstance(f, MatlabArray) else f
    grads = np.gradient(data, *varargs)
    if isinstance(grads, list):
        return tuple(MatlabArray(g) for g in grads)
    return MatlabArray(grads)

def cross(a, b):
    val_a = a._data if isinstance(a, MatlabArray) else a
    val_b = b._data if isinstance(b, MatlabArray) else b
    return MatlabArray(np.cross(val_a, val_b))

def dot(a, b):
    val_a = a._data if isinstance(a, MatlabArray) else a
    val_b = b._data if isinstance(b, MatlabArray) else b
    return MatlabArray(np.vdot(val_a, val_b))