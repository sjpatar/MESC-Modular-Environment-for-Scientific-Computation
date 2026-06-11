from ides.mathex.kernel.session import KernelSession

def test_index_vs_function():
    sess = KernelSession()
    
    # Scenario 1: Array Indexing A(2)
    # The transpiler generates: A(2)
    # Runtime: MatlabArray.__call__ handles it
    sess.execute("A = [10 20 30]; y = A(2);")
    assert sess.globals['y'] == 20
    print("\n[PASS] Array indexing A(2) works.")
    
    # Scenario 2: Function Call sin(0)
    # The transpiler generates: sin(0)
    # Runtime: Calls the python function 'sin'
    sess.execute("z = sin(0);")
    assert sess.globals['z'] == 0
    print("[PASS] Function call sin(0) works.")
    
    # Scenario 3: 2D Indexing A(1, 2)
    sess.execute("M = [1 2; 3 4]; val = M(2, 1);")
    assert sess.globals['val'] == 3
    print("[PASS] 2D Indexing M(2,1) works.")

if __name__ == "__main__":
    test_index_vs_function()