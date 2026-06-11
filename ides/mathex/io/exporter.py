import numpy as np
from shared.symbolic_core.arrays import MatlabArray
from shared.plotting_engine.state import plot_manager

def writematrix(M, filename):
    """
    Exports a matrix to a CSV/Text file.
    """
    if isinstance(M, MatlabArray):
        M = M._data
        
    try:
        np.savetxt(filename, M, delimiter=",", fmt="%.6g")
        print(f"Matrix exported to {filename}")
    except Exception as e:
        print(f"Export failed: {e}")

def saveas(filename):
    """
    Saves the current figure to an image file (png, jpg, pdf).
    """
    fig = plot_manager.widget.figure if plot_manager.widget else None
    if fig:
        try:
            fig.savefig(filename)
            print(f"Figure saved to {filename}")
        except Exception as e:
            print(f"Error saving figure: {e}")
    else:
        print("No active figure to save.")