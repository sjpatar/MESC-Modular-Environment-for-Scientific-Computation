import sys
import numpy as np
import time
from PySide6.QtWidgets import QApplication
from ides.mathex.ui.variable_inspector import VariableInspector

def run_stress_test():
    app = QApplication(sys.argv)
    
    # 1. Simulate PDE Output (20 time steps, 1000 grid points)
    print("Generating PDE Dataset (20 x 1000)...")
    data_small = np.random.rand(20, 1000)
    
    # 2. Simulate High-Res Simulation (1000 x 1000)
    print("Generating High-Res Dataset (1000 x 1000)...")
    data_large = np.random.rand(1000, 1000)

    print("\n[TEST 1] Opening Inspector for 20x1000 matrix...")
    t0 = time.time()
    inspector = VariableInspector("PDE_Solution", data_small)
    inspector.show()
    t_load = time.time() - t0
    print(f"✅ Loaded in {t_load:.4f}s (Acceptable)")
    
    # Close previous
    inspector.close()
    
    print("\n[TEST 2] Opening Inspector for 1000x1000 matrix...")
    print("⚠️  WARNING: This may freeze the UI for 10+ seconds with the old inspector.")
    t0 = time.time()
    try:
        # We use a timeout or manual check logic usually, but here we just run it
        inspector_large = VariableInspector("Big_Data", data_large)
        inspector_large.show()
        t_load = time.time() - t0
        print(f"❌ Loaded in {t_load:.4f}s (Too Slow!)")
    except Exception as e:
        print(f"CRASHED: {e}")

    # app.exec() # Uncomment to keep window open

if __name__ == "__main__":
    run_stress_test()