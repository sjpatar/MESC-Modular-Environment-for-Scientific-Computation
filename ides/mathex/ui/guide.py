import os
from PySide6.QtWidgets import QDialog, QVBoxLayout
from PySide6.QtCore import Qt, QEvent
from PySide6.QtWebEngineWidgets import QWebEngineView
from ides.mathex.language.locale import tr

# Replace your existing GuideDialog with this one!
class GuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("guide_title"))
        self.resize(950, 750)
        
        self.setStyleSheet("QDialog { background-color: #252526; }")
        
        # Zero-margin layout to strip away the dialog borders
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.browser = QWebEngineView()
        
        # Resolve path exactly like we did for Mathematica
        current_dir = os.path.dirname(__file__)
        doc_path = os.path.abspath(os.path.join(current_dir, "..", "..", "..", "docs", "MATHEX_GUIDE.html"))
        
        if os.path.exists(doc_path):
            with open(doc_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            self.browser.setHtml(html_content)
        else:
            error_html = f"""
            <div style="color: #d4d4d4; font-family: sans-serif; padding: 20px; background-color: #1e1e1e; height: 100vh; margin: 0;">
                <h2 style="color: #e06c75;">{tr("guide_missing_title")}</h2>
                <p>{tr("guide_missing_body")}</p>
                <pre style="background: #252526; padding: 10px; border: 1px solid #555;">{doc_path}</pre>
                <p>{tr("guide_missing_filename", filename="MATHEX_GUIDE.html")}</p>
            </div>
            """
            self.browser.setHtml(error_html)
            
        layout.addWidget(self.browser)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.LanguageChange:
            self.setWindowTitle(tr("guide_title"))
        super().changeEvent(event)

# (If you have an AboutDialog down here, leave it alone!)
