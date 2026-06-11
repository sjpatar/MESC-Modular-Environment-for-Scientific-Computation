from .arrays import (
    MatlabArray, mat, zeros, ones, eye, linspace, arange,
    sparse, full, colon
)

from .linalg import (
    inv, det, eig, rank, norm, lu, svd, qr, pinv, null, orth, eigs
)

from .statistics import (
    mean, std, min_func, max_func, sum_func,
    corrcoef, cov, histcounts, nlinfit
)

from .calculus import diff, int_func

# Import Optimization module
try:
    from .optim import fminsearch, fzero, lsqcurvefit, fmincon, linprog
except ImportError:
    pass

# [FIX] Import Physics Module and Constants
from .physics import (
    physconst, convtemp, convlength, convmass, convforce, convpres, convenergy,
    PhysicalConstants, c, h, hbar, G, k, e, g
)

# [FIX] Import Engineering Toolbox (ODES, Signal, Interp)
try:
    # Use relative import from toolbox package
    from ides.mathex.toolbox import (
        ode45, ode23, ode15s, bvp4c, pdepe,
        fft, ifft, fftshift, ifftshift, spectrogram, pwelch, findpeaks,
        interp1, interp2, griddata, meshgrid,
        trapz, cumtrapz, integral,
        roots, polyval, gradient, cross, dot,
        sphere, cylinder
    )
except ImportError:
    pass