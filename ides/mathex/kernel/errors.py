class MathexError(Exception):
    """Base class for all application errors."""
    pass

class TranspilationError(MathexError):
    """Raised when MATLAB code cannot be converted to Python."""
    pass

class ExecutionError(MathexError):
    """Raised when the Python code fails to run."""
    pass