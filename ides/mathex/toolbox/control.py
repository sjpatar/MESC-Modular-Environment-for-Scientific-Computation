import numpy as np
import scipy.signal
from shared.symbolic_core.arrays import MatlabArray
import shared.plotting_engine.plot2d as plt2d 
import shared.plotting_engine.state as plt_state

# ==========================================================
# TRANSFER FUNCTION CLASS
# ==========================================================
class TransferFunction:
    """
    MATLAB-like Transfer Function object.
    Supports operations like G1*G2, G1+G2, 1/G, s^2, etc.
    """
    def __init__(self, num, den, dt=None):
        self.num = np.asarray(num).flatten()
        self.den = np.asarray(den).flatten()
        self.dt = dt 
        
        self.num = np.trim_zeros(self.num, 'f')
        self.den = np.trim_zeros(self.den, 'f')
        
        if len(self.den) == 0: self.den = np.array([1.0])
        if len(self.num) == 0: self.num = np.array([0.0])

        if self.dt is not None:
            self._sys = scipy.signal.TransferFunction(self.num, self.den, dt=self.dt)
        else:
            self._sys = scipy.signal.TransferFunction(self.num, self.den)

    def __repr__(self):
        n_str = np.array2string(self.num, precision=4, separator=' ')
        d_str = np.array2string(self.den, precision=4, separator=' ')
        bar_len = max(len(n_str), len(d_str))
        return f"\n{n_str.center(bar_len)}\n{'-'*bar_len}\n{d_str.center(bar_len)}\n"

    def __add__(self, other):
        if isinstance(other, (int, float)):
            other = TransferFunction([other], [1], dt=self.dt)
        n1, d1 = self.num, self.den
        n2, d2 = other.num, other.den
        new_num = np.polyadd(np.convolve(n1, d2), np.convolve(n2, d1))
        new_den = np.convolve(d1, d2)
        return TransferFunction(new_num, new_den, self.dt)

    def __radd__(self, other): return self.__add__(other)
    def __sub__(self, other): return self.__add__(other * -1)

    def __rsub__(self, other):
        if isinstance(other, (int, float)):
            other = TransferFunction([other], [1], dt=self.dt)
        return other.__add__(self * -1)

    def __mul__(self, other):
        if isinstance(other, (int, float)):
            other = TransferFunction([other], [1], dt=self.dt)
        new_num = np.convolve(self.num, other.num)
        new_den = np.convolve(self.den, other.den)
        return TransferFunction(new_num, new_den, self.dt)

    def __rmul__(self, other): return self.__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, (int, float)):
             return TransferFunction(self.num, self.den * other, self.dt)
        inv_other = TransferFunction(other.den, other.num, other.dt)
        return self.__mul__(inv_other)

    def __rtruediv__(self, other):
        if isinstance(other, (int, float)):
            return TransferFunction(self.den * other, self.num, self.dt)
        return NotImplemented

    def __pow__(self, power):
        if not isinstance(power, int):
            raise TypeError("TransferFunction power must be an integer.")
        if power == 0: return TransferFunction([1], [1], dt=self.dt)
        if power < 0:
            inv_self = TransferFunction(self.den, self.num, self.dt)
            return inv_self.__pow__(-power)
        res = self
        for _ in range(power - 1): res = res * self
        return res

    def __neg__(self): return self * -1

    def feedback(self, other=1, sign=-1):
        if isinstance(other, (int, float)):
            other = TransferFunction([other], [1], dt=self.dt)
        Ng, Dg = self.num, self.den
        Nh, Dh = other.num, other.den
        new_num = np.convolve(Ng, Dh)
        term1 = np.convolve(Dg, Dh)
        term2 = np.convolve(Ng, Nh)
        if sign == -1: new_den = np.polyadd(term1, term2)
        else: new_den = np.polysub(term1, term2)
        return TransferFunction(new_num, new_den, self.dt)

# ==========================================================
# PUBLIC API
# ==========================================================

def tf(num, den=None):
    if isinstance(num, str) and num == 's':
        return TransferFunction([1, 0], [1])
    if hasattr(num, '_data'): num = num._data
    if hasattr(den, '_data'): den = den._data
    if den is None: den = [1]
    return TransferFunction(num, den)

def step(sys, T=None):
    if not isinstance(sys, TransferFunction):
        raise ValueError("Input must be a TransferFunction object (use 'tf')")
    
    t, y = scipy.signal.step(sys._sys, T=T)
    
    plt2d.plot(t, y, 'b-', linewidth=2.0)
    plt2d.title('Step Response')
    plt2d.xlabel('Time (sec)')
    plt2d.ylabel('Amplitude')
    plt2d.grid(True)
    return MatlabArray(y), MatlabArray(t)

def impulse(sys, T=None):
    if not isinstance(sys, TransferFunction): raise ValueError("Input must be a TransferFunction")
    t, y = scipy.signal.impulse(sys._sys, T=T)
    
    plt2d.plot(t, y, 'r-', linewidth=2.0)
    plt2d.title('Impulse Response')
    plt2d.xlabel('Time (sec)')
    plt2d.ylabel('Amplitude')
    plt2d.grid(True)
    return MatlabArray(y), MatlabArray(t)

def bode(sys, w=None):
    if not isinstance(sys, TransferFunction): raise ValueError("Input must be a TransferFunction")
    w, mag, phase = scipy.signal.bode(sys._sys, w=w)
    
    ax1 = plt2d.subplot(2, 1, 1)
    plt2d.plot(w, mag, linewidth=2.0)
    plt2d.title('Bode Diagram')
    plt2d.ylabel('Magnitude (dB)')
    plt2d.grid(True)
    ax1.set_xscale('log')
    
    ax2 = plt2d.subplot(2, 1, 2)
    plt2d.plot(w, phase, linewidth=2.0)
    plt2d.ylabel('Phase (deg)')
    plt2d.xlabel('Frequency (rad/s)')
    plt2d.grid(True)
    ax2.set_xscale('log')
    
    plt_state.plot_manager.request_draw()
    return MatlabArray(mag), MatlabArray(phase), MatlabArray(w)

def series(sys1, sys2): return sys1 * sys2
def parallel(sys1, sys2): return sys1 + sys2
def feedback(sys1, sys2=1, sign=-1): return sys1.feedback(sys2, sign)

# ==========================================================
# ROOT LOCUS IMPLEMENTATION
# ==========================================================

def rlocus(sys, k=None):
    """
    rlocus(sys) -> Plots Root Locus with High Visibility
    """
    if not isinstance(sys, TransferFunction):
        raise ValueError("Input must be a TransferFunction object")

    # 1. Get Open-Loop Poles (K=0) and Zeros (K=inf)
    poles = np.roots(sys.den)
    zeros = np.roots(sys.num)

    # 2. Determine Gain Vector k
    if k is None:
        k = np.logspace(-4, 3, 500) 
        k = np.insert(k, 0, 0)
    gains = np.asarray(k).flatten()
    
    # 3. Calculate Roots
    n = len(sys.den)
    m = len(sys.num)
    max_len = max(n, m)
    
    padded_den = np.pad(sys.den, (max_len - n, 0), 'constant')
    padded_num = np.pad(sys.num, (max_len - m, 0), 'constant')

    all_roots = []
    for gain in gains:
        poly = padded_den + gain * padded_num
        r = np.roots(poly)
        r = np.sort_complex(r)
        all_roots.append(r)

    all_roots = np.array(all_roots)

    # 4. Plotting
    # [FIX] Thicker Blue lines for branches
    plt2d.plot(all_roots.real, all_roots.imag, 'b-', linewidth=2.5)
    
    # [FIX] Large Red Crosses for Poles
    if len(poles) > 0:
        plt2d.plot(
            poles.real, poles.imag, 'rx', 
            markersize=10, 
            markeredgewidth=2.5
        )
        
    # [FIX] Large Red Circles for Zeros
    if len(zeros) > 0:
        plt2d.plot(
            zeros.real, zeros.imag, 'ro', 
            markersize=10, 
            markeredgewidth=2.5,
            markerfacecolor='none' # Hollow circles are standard
        )

    # Decorations
    plt2d.title('Root Locus')
    plt2d.xlabel('Real Axis')
    plt2d.ylabel('Imaginary Axis')
    plt2d.grid(True)
    
    # Axis lines
    ax = plt_state.plot_manager.gca()
    if ax:
        # Subtle but visible zero lines
        ax.axhline(0, color='b', linewidth=0.8, linestyle='--')
        ax.axvline(0, color='w', linewidth=0.8, linestyle='--')

    plt_state.plot_manager.request_draw()
    return MatlabArray(all_roots)