import numpy as np
import scipy.signal
import scipy.fft
from shared.symbolic_core.arrays import MatlabArray

def fft(x, n=None, dim=-1):
    data = x._data if isinstance(x, MatlabArray) else x
    return MatlabArray(scipy.fft.fft(data, n=n, axis=dim))

def ifft(x, n=None, dim=-1):
    data = x._data if isinstance(x, MatlabArray) else x
    return MatlabArray(scipy.fft.ifft(data, n=n, axis=dim))

def fftshift(x, axes=None):
    data = x._data if isinstance(x, MatlabArray) else np.array(x)
    return MatlabArray(np.fft.fftshift(data, axes=axes))

def ifftshift(x, axes=None):
    data = x._data if isinstance(x, MatlabArray) else np.array(x)
    return MatlabArray(np.fft.ifftshift(data, axes=axes))

# ==========================================================
# NEW: 2D FFT & Filtering
# ==========================================================
def fft2(X, m=None, n=None):
    """
    2-D Discrete Fourier Transform.
    fft2(X) or fft2(X, m, n)
    """
    data = X._data if isinstance(X, MatlabArray) else X
    shape = None
    if m is not None and n is not None:
        shape = (int(m), int(n))
    return MatlabArray(scipy.fft.fft2(data, s=shape))

def ifft2(X, m=None, n=None):
    """
    2-D Inverse Discrete Fourier Transform.
    ifft2(X) or ifft2(X, m, n)
    """
    data = X._data if isinstance(X, MatlabArray) else X
    shape = None
    if m is not None and n is not None:
        shape = (int(m), int(n))
    return MatlabArray(scipy.fft.ifft2(data, s=shape))

def filter(b, a, x):
    """
    1-D Digital Filter.
    y = filter(b, a, x)
    """
    val_b = b._data if isinstance(b, MatlabArray) else b
    val_a = a._data if isinstance(a, MatlabArray) else a
    val_x = x._data if isinstance(x, MatlabArray) else x
    
    # Flatten coeffs if necessary, but keep x shape if possible
    val_b = np.asarray(val_b).flatten()
    val_a = np.asarray(val_a).flatten()
    
    # scipy.signal.lfilter applies along the last axis by default
    y = scipy.signal.lfilter(val_b, val_a, val_x)
    return MatlabArray(y)

# ==========================================================
# Existing Signal Tools
# ==========================================================
def spectrogram(x, window=None, noverlap=None, nfft=None, fs=1.0):
    x_data = np.asarray(x).flatten()
    if nfft is None: nfft = 256
    f, t, Sxx = scipy.signal.spectrogram(
        x_data, fs=fs, window=('hann' if window is None else window),
        nperseg=nfft, noverlap=noverlap
    )
    return MatlabArray(Sxx), MatlabArray(f), MatlabArray(t)

def pwelch(x, window='hann', noverlap=None, nfft=None, fs=1.0):
    x_data = np.asarray(x).flatten()
    if nfft is None: nfft = 256
    f, Pxx = scipy.signal.welch(
        x_data, fs=fs, window=window, 
        nperseg=nfft, noverlap=noverlap
    )
    return MatlabArray(Pxx), MatlabArray(f)

def findpeaks(data, **kwargs):
    x = np.asarray(data).flatten()
    if isinstance(data, MatlabArray):
        x = data._data.flatten()
    idxs, properties = scipy.signal.find_peaks(x, **kwargs)
    pks = x[idxs]
    return MatlabArray(pks), MatlabArray(idxs + 1)