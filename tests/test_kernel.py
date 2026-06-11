from ides.mathex.kernel.session import KernelSession
from ides.mathex.kernel.executor import execute
import threading


def test_basic_expression():
    s = KernelSession()
    err = execute("2+3", s)
    assert err is None
    assert s.globals["ans"] == 5


def test_semicolon_suppression():
    s = KernelSession()
    execute("4+6;", s)
    assert s.globals["ans"] == 10


def test_assignment():
    s = KernelSession()
    execute("a=7", s)
    execute("b=8", s)
    execute("a+b", s)
    assert s.globals["ans"] == 15


def test_undefined_variable():
    s = KernelSession()
    err = execute("x", s)
    assert err is not None


def test_after_execute_skips_process_events_off_main_thread(monkeypatch):
    calls = []

    class FakeApplication:
        @staticmethod
        def processEvents():
            calls.append("called")

    monkeypatch.setattr("ides.mathex.kernel.session.QApplication", FakeApplication)

    session = KernelSession()
    worker = threading.Thread(target=session._after_execute)
    worker.start()
    worker.join()

    assert calls == []
