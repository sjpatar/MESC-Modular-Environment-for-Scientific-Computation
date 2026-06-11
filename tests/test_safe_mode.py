from ides.mathex.kernel.executor import execute
from ides.mathex.kernel.session import KernelSession


def test_safe_mode_blocks_python_escape():
    session = KernelSession(safe_mode=True)

    error = execute("__import__('os').system('echo unsafe')", session)

    assert isinstance(error, PermissionError)
    assert "disabled" in str(error).lower()


def test_safe_mode_blocks_filesystem_commands():
    session = KernelSession(safe_mode=True)

    error = execute("pwd", session)

    assert isinstance(error, PermissionError)
    assert "safe mode" in str(error).lower()
