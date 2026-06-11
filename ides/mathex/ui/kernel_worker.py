# mathex/ui/kernel_worker.py
"""
KernelWorker
============

Executes KernelSession code in a background Qt thread.

HARD GUARANTEES:
- User code NEVER runs on UI thread
- Full Python tracebacks ALWAYS go to terminal
- Console gets clean MATLAB-style output
- finished() is ALWAYS emitted
"""

from PySide6.QtCore import QObject, QThread, Signal, Slot
import traceback
import sys
import io
from contextlib import redirect_stdout


class KernelWorker(QObject):
    """
    Worker object that runs inside a QThread.
    One execution per instance.
    """

    # lifecycle signals
    started = Signal()
    finished = Signal()
    failed = Signal(str)        # user-facing error
    output = Signal(str)        # user-facing stdout

    def __init__(self, session):
        super().__init__()
        self._session = session
        self._code = ""
        self._breakpoints = None  # [UPGRADE] Store breakpoints

    # ---------------------------------------------------------
    # API
    # ---------------------------------------------------------

    def set_code(self, code: str, breakpoints: list = None):
        """
        Sets the code and optional breakpoints for execution.
        """
        self._code = code or ""
        self._breakpoints = breakpoints

    # ---------------------------------------------------------
    # Execution entry point (WORKER THREAD)
    # ---------------------------------------------------------

    @Slot()
    def run(self):
        self.started.emit()

        stdout_buf = io.StringIO()

        try:
            if self._code.strip():
                # -----------------------------------------
                # Redirect ONLY stdout → buffer
                # -----------------------------------------
                with redirect_stdout(stdout_buf):
                    # [UPGRADE] Pass breakpoints to session if they exist
                    if self._breakpoints:
                        # This triggers the DebugContext in executor.py
                        self._session.execute(self._code, breakpoints=self._breakpoints)
                    else:
                        # Standard execution
                        self._session.execute(self._code)

        except Exception as e:
            # -----------------------------------------
            # FULL TRACEBACK → TERMINAL (developer)
            # -----------------------------------------
            tb = traceback.format_exc()
            print("\n[Mathex Kernel Traceback]", file=sys.stderr)
            print(tb, file=sys.stderr)
            print("[End Kernel Traceback]\n", file=sys.stderr)

            # -----------------------------------------
            # SHORT MESSAGE → CONSOLE
            # -----------------------------------------
            self.failed.emit(f"{type(e).__name__}: {e}")

        finally:
            # -----------------------------------------
            # Flush captured stdout to UI console
            # -----------------------------------------
            out = stdout_buf.getvalue()
            
            # [CRITICAL FIX] 
            # Do NOT use out.strip() here. 
            # 'clc' prints '\f' which is whitespace.
            # strip() would make it empty, preventing the signal from firing.
            if out:
                self.output.emit(out)

            # -----------------------------------------
            # ALWAYS notify UI that execution is done
            # -----------------------------------------
            self.finished.emit()


# ============================================================
# Thread bootstrap helper
# ============================================================

def start_kernel_worker(
    session,
    code,
    *,
    breakpoints=None,  # [UPGRADE] New argument
    on_started=None,
    on_finished=None,
    on_error=None,
    on_output=None,
):
    """
    Start kernel execution in a background QThread.

    Args:
        session: The KernelSession instance.
        code: String of code to run.
        breakpoints: (Optional) List of line numbers to pause at.
    
    UI MUST connect:
      - output   -> console.write_output
      - failed   -> console.write_error
      - finished -> console.execution_finished
    """

    thread = QThread()
    worker = KernelWorker(session)

    # [UPGRADE] Pass breakpoints to the worker
    worker.set_code(code, breakpoints)
    
    worker.moveToThread(thread)

    # thread lifecycle
    thread.started.connect(worker.run)

    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)

    # UI hooks
    if on_started:
        worker.started.connect(on_started)

    if on_output:
        worker.output.connect(on_output)

    if on_error:
        worker.failed.connect(on_error)

    if on_finished:
        worker.finished.connect(on_finished)

    thread.start()
    return thread, worker