# Mathex/mathex/math/physics.py
import numpy as np
import scipy.constants as _sc
from shared.symbolic_core.structs import MatlabStruct
from shared.symbolic_core.arrays import MatlabArray, mat

# =========================================================
# 1. CONSTANTS DATABASE (Powered by CODATA)
# =========================================================

# Map MATLAB/Common names to Scipy attributes
_NAME_MAP = {
    'LightSpeed': 'c',
    'GravitationalConstant': 'G',
    'PlanckConstant': 'h',
    'ReducedPlanckConstant': 'hbar',
    'BoltzmannConstant': 'k',
    'AvogadroConstant': 'N_A',
    'GasConstant': 'R',
    'ElementaryCharge': 'e',
    'ElectronMass': 'm_e',
    'ProtonMass': 'm_p',
    'NeutronMass': 'm_n',
    'RydbergConstant': 'Rydberg',
    'StefanBoltzmannConstant': 'Stefan_Boltzmann',
    'VacuumPermittivity': 'epsilon_0',
    'VacuumPermeability': 'mu_0',
    'StandardAtmosphere': 'atm',
    'AccelerationOfGravity': 'g',
    'FineStructureConstant': 'alpha',
    'WienDisplacementConstant': 'Wien',
}

def physconst(name=None):
    """
    Advanced physical constant lookup.
    
    Usage:
        c = physconst('LightSpeed')   -> Returns value
        s = physconst('LightSpeed')   -> Returns struct with Value, Unit, Uncertainty
        list = physconst()            -> Returns list of available short names
    """
    if name is None:
        # Return list of common names
        return list(_NAME_MAP.keys())
    
    # 1. Check our common mapping (e.g., 'LightSpeed')
    if name in _NAME_MAP:
        val = getattr(_sc, _NAME_MAP[name])
        return val

    # 2. Check Scipy directly (e.g., 'c', 'hbar')
    if hasattr(_sc, name):
        return getattr(_sc, name)
        
    # 3. Check full CODATA dictionary (e.g., 'proton mass energy equivalent')
    # Scipy dict format: key -> (value, unit, uncertainty)
    if name in _sc.physical_constants:
        return _sc.physical_constants[name][0]

    raise ValueError(f"Unknown physical constant: {name}")

# Struct for quick access: PhysicalConstants.c, .hbar, etc.
constants_struct = MatlabStruct(**{
    'c': _sc.c,
    'G': _sc.G,
    'h': _sc.h,
    'hbar': _sc.hbar,
    'k': _sc.k,
    'e': _sc.e,
    'R': _sc.R,
    'Na': _sc.N_A,
    'me': _sc.m_e,
    'mp': _sc.m_p,
    'mn': _sc.m_n,
    'eps0': _sc.epsilon_0,
    'mu0': _sc.mu_0,
    'sigma': _sc.Stefan_Boltzmann,
    'atm': _sc.atm,
    'g': _sc.g,
    'alpha': _sc.alpha,
})

# [FIX] Export as PhysicalConstants for global use
PhysicalConstants = constants_struct

# [FIX] Export common constants as modules globals for easy import
c = _sc.c
h = _sc.h
hbar = _sc.hbar
G = _sc.G
k = _sc.k
e = _sc.e
g = _sc.g


# =========================================================
# 2. UNIT CONVERTERS
# =========================================================

def _ensure_numpy(val):
    """Extract data from MatlabArray or use raw input."""
    if isinstance(val, MatlabArray):
        return val._data
    return np.array(val)

def convtemp(val, from_unit, to_unit):
    """
    Convert temperature.
    Units: 'C', 'F', 'K', 'R' (Rankine)
    """
    v = _ensure_numpy(val)
    res = _sc.convert_temperature(v, from_unit, to_unit)
    return MatlabArray(res)

def convlength(val, from_unit, to_unit):
    """
    Convert length.
    Units: 'm', 'km', 'cm', 'mm', 'nm', 'in', 'ft', 'yd', 'mi', 'nmi' (nautical mile)
    """
    multipliers = {
        'm': 1.0, 'km': 1000.0, 'cm': 0.01, 'mm': 0.001, 'nm': 1e-9,
        'in': _sc.inch, 'ft': _sc.foot, 'yd': _sc.yard, 'mi': _sc.mile,
        'nmi': _sc.nautical_mile, 'au': _sc.astronomical_unit, 'ly': _sc.light_year
    }
    v = _ensure_numpy(val)
    base_m = v * multipliers[from_unit]
    return MatlabArray(base_m / multipliers[to_unit])

def convmass(val, from_unit, to_unit):
    """
    Convert mass.
    Units: 'kg', 'g', 'mg', 'lb', 'oz', 'slug', 'ton' (metric), 'amu'
    """
    multipliers = {
        'kg': 1.0, 'g': 0.001, 'mg': 1e-6, 'ton': 1000.0,
        'lb': _sc.lb, 'oz': _sc.oz, 'slug': _sc.slug, 'amu': _sc.atomic_mass
    }
    v = _ensure_numpy(val)
    base_kg = v * multipliers[from_unit]
    return MatlabArray(base_kg / multipliers[to_unit])

def convforce(val, from_unit, to_unit):
    """
    Convert force.
    Units: 'N', 'kN', 'lbf', 'dyne', 'kgf'
    """
    multipliers = {
        'N': 1.0, 'kN': 1000.0, 'dyne': _sc.dyne,
        'lbf': _sc.lbf, 'kgf': _sc.kgf
    }
    v = _ensure_numpy(val)
    base_n = v * multipliers[from_unit]
    return MatlabArray(base_n / multipliers[to_unit])

def convpres(val, from_unit, to_unit):
    """
    Convert pressure.
    Units: 'Pa', 'kPa', 'MPa', 'bar', 'atm', 'psi', 'torr'
    """
    multipliers = {
        'Pa': 1.0, 'kPa': 1000.0, 'MPa': 1e6, 'bar': _sc.bar,
        'atm': _sc.atm, 'psi': _sc.psi, 'torr': _sc.torr
    }
    v = _ensure_numpy(val)
    base_pa = v * multipliers[from_unit]
    return MatlabArray(base_pa / multipliers[to_unit])

def convenergy(val, from_unit, to_unit):
    """
    Convert energy.
    Units: 'J', 'kJ', 'cal', 'kcal', 'eV', 'keV', 'MeV', 'kWh', 'BTU'
    """
    multipliers = {
        'J': 1.0, 'kJ': 1000.0, 
        # Upgraded to International Table Calories (IT) for engineering precision
        'cal': _sc.calorie_IT, 'kcal': _sc.calorie_IT * 1000.0, 
        'eV': _sc.eV, 'keV': _sc.eV*1e3, 'MeV': _sc.eV*1e6,
        'kWh': 3.6e6, 'BTU': _sc.Btu 
    }
    v = _ensure_numpy(val)
    base_j = v * multipliers[from_unit]
    return MatlabArray(base_j / multipliers[to_unit])