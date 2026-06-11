import numpy as np
import pytest
from shared.symbolic_core.arrays import MatlabArray

def test_lazy_copy_behavior():
    # 1. Setup Data
    data = np.array([1, 2, 3, 4])
    A = MatlabArray(data)
    
    # 2. Assignment (Should be Lazy)
    # This triggers the "copy=False" path in your new transpiler logic
    B = MatlabArray(A, copy=False)
    
    # CHECK: Internal numpy arrays must be the EXACT SAME object
    assert B._data is A._data, "FAIL: Assignment created a deep copy immediately!"
    print("\n[PASS] B shares memory with A initially.")
    
    # 3. Mutation (Should Trigger Copy-on-Write)
    # [FIX] Use [0, 0] to modify the specific element, not the whole row
    B[0, 0] = 99
    
    # CHECK: Now they must be DIFFERENT
    assert B._data is not A._data, "FAIL: Mutation did not trigger a copy! A was modified!"
    
    # [FIX] Use [0, 0] to check the scalar value. 
    # A[0] returns the row [1, 2, 3, 4], which != 1 in boolean context.
    assert A[0, 0] == 1, f"FAIL: Modifying B changed A (Safety check failed). A[0,0] is {A[0,0]}"
    assert B[0, 0] == 99
    print("[PASS] Mutation triggered Copy-on-Write successfully.")

if __name__ == "__main__":
    test_lazy_copy_behavior()