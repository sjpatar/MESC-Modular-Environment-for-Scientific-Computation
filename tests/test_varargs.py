import textwrap
from ides.mathex.kernel.session import KernelSession
from ides.mathex.kernel.executor import execute

def test_varargin_nargin():
    """Verify varargin handling and nargin counting."""
    s = KernelSession()
    code = textwrap.dedent("""
    function y = test_args(a, varargin)
        if nargin == 1
            y = a;
        elseif nargin == 3
            % varargin is now a cell array (MatlabArray), so (1) indexing works!
            y = a + varargin(1) + varargin(2); 
        else
            y = -1;
        end
    end
    
    res1 = test_args(10);
    res2 = test_args(10, 20, 30);
    """)
    
    execute(code, s)
    
    # 1. Verify nargin == 1 case
    assert s.globals['res1'] == 10
    
    # 2. Verify nargin == 3 and varargin unpacking
    # 10 + 20 + 30 = 60
    # If this passes, your transpiler change is a success!
    assert s.globals['res2'] == 60