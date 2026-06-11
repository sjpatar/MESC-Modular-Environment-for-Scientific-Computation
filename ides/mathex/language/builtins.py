# mathex/language/builtins.py
import numpy as np
import os
import time
from shared.symbolic_core.arrays import MatlabArray
from shared.symbolic_core.structs import MatlabStruct
from shared.plotting_engine.state import plot_manager
from .locale import tr, get_doc

# ==========================================================
# MATLAB Built-ins
# ==========================================================

def num2str(x, format_spec=None):
    if isinstance(x, MatlabArray):
        val = x._data
    else:
        val = x
        
    if np.isscalar(val) or (isinstance(val, np.ndarray) and val.size == 1):
        if isinstance(val, np.ndarray): val = val.item()
        
        if isinstance(val, (complex, np.complex128, np.complex64)):
            s = str(val).replace('j', 'i')
        elif format_spec:
            s = "{:.4f}".format(val)
        else:
            s = str(val)
        
        return MatlabArray(np.array(s))
        
    return MatlabArray(np.array(str(val)))

def sprintf(format_spec, *args):
    """
    MATLAB-style sprintf implementation using Python's % string formatting.
    """
    try:
        vals = []
        for a in args:
            # Extract underlying values from MatlabArrays for string formatting
            if isinstance(a, MatlabArray):
                if hasattr(a._data, "size") and a._data.size == 1:
                    vals.append(a._data.item())
                else:
                    vals.append(a._data)
            else:
                vals.append(a)
        
        # Apply the format specification
        if not vals:
            res = str(format_spec)
        elif len(vals) == 1:
            res = str(format_spec) % vals[0]
        else:
            res = str(format_spec) % tuple(vals)
            
        return MatlabArray(np.array(res))
    except Exception:
        # Fallback in case of a formatting mismatch
        return MatlabArray(np.array(str(format_spec)))
    
def deal(*args):
    if len(args) == 0:
        return None
    if len(args) == 1:
        return args[0]
    return args


def disp(x=None):
    if x is None:
        print()
    else:
        print(x)

disp.__mathex_command__ = True


def clc():
    print("\f", end="")

clc.__mathex_command__ = True


def drawnow():
    plot_manager.request_draw(immediate=True, wait=True)

drawnow.__mathex_command__ = True


def pause(n=None):
    drawnow()
    
    if n is None:
        time.sleep(0.01)
        return
    
    sec = float(n)
    if sec > 0:
        time.sleep(sec)

pause.__mathex_command__ = True


def size(x, dim=None):
    if not hasattr(x, "shape"):
        return MatlabArray([1, 1])

    shape = x.shape

    if dim is not None:
        d = int(dim)
        if d < 1 or d > len(shape):
            return MatlabArray(1)
        return MatlabArray(shape[d - 1])

    return MatlabArray(list(shape))


def length(x):
    if not hasattr(x, "shape"):
        return MatlabArray(1)
    return MatlabArray(max(x.shape) if x.shape else 1)


def numel(x):
    if not hasattr(x, "shape"):
        return MatlabArray(1)
    return MatlabArray(int(np.prod(x.shape)))


def who(namespace):
    print(tr("who_header"))
    names = sorted(
        k for k, v in namespace.items()
        if not k.startswith("__") and not callable(v)
    )
    if names:
        print("  " + "  ".join(names))
    else:
        print(tr("who_none"))
    print()

who.__mathex_command__ = True


def whos(namespace):
    header = f"{tr('whos_name'):<12} {tr('whos_size'):<16} {tr('whos_class')}"
    print(header)
    print("-" * 40)

    for name, val in sorted(namespace.items()):
        if name.startswith("__") or callable(val):
            continue

        if hasattr(val, "shape"):
            dims = "x".join(str(d) for d in val.shape)
            size_str = dims
        else:
            size_str = "1x1"

        if isinstance(val, MatlabArray):
            cls = "double" 
            if val.is_sparse:
                cls = "sparse double"
            elif val._data.dtype == object:
                cls = "struct array"
        elif isinstance(val, (int, float, complex)):
            cls = "double"
        elif isinstance(val, str):
            cls = "char"
        elif isinstance(val, MatlabStruct):
            cls = "struct"
        else:
            cls = type(val).__name__

        print(f"{name:<12} {size_str:<16} {cls}")

    print()
    
whos.__mathex_command__ = True


def exist(name, kind=None, namespace=None):
    if not isinstance(name, str):
        return 0

    if (kind == 'var' or kind is None) and namespace is not None:
        if name in namespace:
            return 1
            
    if kind == 'file' or kind == 'dir' or kind is None:
        if os.path.exists(name):
            if os.path.isdir(name):
                return 7
            return 2
        if os.path.exists(name + ".m"):
            return 2
            
    return 0


def struct(*args):
    if len(args) % 2 != 0:
        raise ValueError("struct requires field-value pairs.")
    
    keys = []
    values = []
    max_len = 1
    has_cells = False

    for i in range(0, len(args), 2):
        key = args[i]
        if isinstance(key, MatlabArray): key = str(key._data)
        if not isinstance(key, str): raise ValueError("Field names must be strings.")
        
        val = args[i+1]
        
        if isinstance(val, MatlabArray) and val._data.dtype == object:
             val = val._data.flatten().tolist()
        
        if isinstance(val, (list, tuple)):
            has_cells = True
            max_len = max(max_len, len(val))
        
        keys.append(key)
        values.append(val)

    if not has_cells or max_len == 0:
        data = {k: v for k, v in zip(keys, values)}
        return MatlabStruct(**data)

    struct_list = []
    for idx in range(max_len):
        data = {}
        for k, v in zip(keys, values):
            if isinstance(v, (list, tuple)):
                if idx < len(v):
                    data[k] = v[idx]
                else:
                    data[k] = None
            else:
                data[k] = v
        struct_list.append(MatlabStruct(**data))

    return MatlabArray(np.array(struct_list, dtype=object).reshape(1, max_len))


# ==========================================================
# Assamese Aliases for Built-ins
# ==========================================================
দেখুওৱা = disp
মচিদিয়া = clc
ৰৈযোৱা = pause
আকাৰ = size
দৈৰ্ঘ্য = length

দেখুওৱা.__mathex_command__ = True
মচিদিয়া.__mathex_command__ = True
ৰৈযোৱা.__mathex_command__ = True

# ==========================================================
# Help System Interceptor
# ==========================================================
def mathex_help(topic=None):
    if topic is None:
        print(tr("help_default"))
        return
        
    # Extract the true name whether passed as a function object or a string
    if callable(topic):
        name = getattr(topic, "__name__", str(topic))
    else:
        name = str(topic)
        
    doc = get_doc(name)
    if doc:
        print(f"\n{doc}\n")
    else:
        print(tr("err_undefined", name=name))
        
mathex_help.__mathex_command__ = True