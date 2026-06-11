import sys
import os
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from app_platform.ui_shell.app_shell import StemShell

# --- Imports ---
from ides.mathex.ide_plugin import MatlabTool
from ides.mathematica.ide_plugin import MathematicaTool
from ides.geogebra.ide_plugin import GeogebraTool  

os.environ["QT_LOGGING_RULES"] = "qt.text.font.db=false"

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

def get_app_icon_path():
    """Prefer the Windows .ico for taskbar integration and fall back to the PNG."""
    candidates = []
    if sys.platform == "win32":
        candidates.append(os.path.join("ides", "mathex", "resources", "icon.ico"))
    candidates.append(os.path.join("ides", "mathex", "resources", "logo.png"))

    for relative_path in candidates:
        absolute_path = get_resource_path(relative_path)
        if os.path.exists(absolute_path):
            if not QIcon(absolute_path).isNull():
                return absolute_path
    return None

def run():
    # 1. THE ULTIMATE CACHE BUSTER
    if sys.platform == "win32":
        import ctypes
        dynamic_id = f"mesc.mathematical.environment.dev.{int(time.time())}" 
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(ctypes.c_wchar_p(dynamic_id))
        
    app = QApplication(sys.argv)
    app.setApplicationName("MESC")
    app.setApplicationDisplayName("MESC")
    app.setOrganizationName("MESC")
    
    icon_path = get_app_icon_path()
    
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))
    else:
        print("CRITICAL WARNING: No valid application icon resource was found.")
    
    shell = StemShell()
    
    # --- Register Tools ---
    shell.register_tool(MatlabTool())
    shell.register_tool(MathematicaTool())
    shell.register_tool(GeogebraTool()) 
    
    shell.switch_tool(0)
    shell.show()

    # 2. BRUTE FORCE WIN32 OVERRIDE (Instance + Window Class)
    if icon_path and sys.platform == "win32":
        app.processEvents()
        
        try:
            import ctypes
            from ctypes import wintypes
            
            hwnd = int(shell.winId())
            user32 = ctypes.windll.user32
            
            c_path = ctypes.c_wchar_p(icon_path)
            # Load the icon natively
            hicon = user32.LoadImageW(None, c_path, 1, 0, 0, 0x00000010)
            
            if hicon != 0:
                # A. Set the Instance Icon (Titlebar / Alt-Tab)
                user32.SendMessageW(hwnd, 0x0080, 0, hicon) # ICON_SMALL
                user32.SendMessageW(hwnd, 0x0080, 1, hicon) # ICON_BIG
                
                # B. Set the Window Class Icon (Forces the Taskbar to update)
                GCLP_HICON = -14
                GCLP_HICONSM = -34
                
                # Windows API requires different functions based on 32-bit vs 64-bit Python
                if sys.maxsize > 2**32: # 64-bit
                    user32.SetClassLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.HANDLE]
                    user32.SetClassLongPtrW.restype = wintypes.HANDLE
                    user32.SetClassLongPtrW(hwnd, GCLP_HICON, hicon)
                    user32.SetClassLongPtrW(hwnd, GCLP_HICONSM, hicon)
                else: # 32-bit
                    user32.SetClassLongW.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.HANDLE]
                    user32.SetClassLongW.restype = wintypes.HANDLE
                    user32.SetClassLongW(hwnd, GCLP_HICON, hicon)
                    user32.SetClassLongW(hwnd, GCLP_HICONSM, hicon)
                    
                print("SUCCESS: Instance AND Window Class Taskbar Icons forcefully overridden.")
            else:
                print(f"CRITICAL: Windows rejected the icon format. Error: {ctypes.GetLastError()}")
                
        except Exception as e:
            print(f"Native Win32 Class override exception: {e}")

    sys.exit(app.exec())

if __name__ == "__main__":
    run()