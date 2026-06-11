import io

class StdoutBuffer(io.StringIO):
    """
    Thread-safe buffer for capturing stdout if we move to multi-threading.
    For Phase 1 (Single Thread), io.StringIO is sufficient, 
    but this keeps the architecture extensible.
    """
    pass