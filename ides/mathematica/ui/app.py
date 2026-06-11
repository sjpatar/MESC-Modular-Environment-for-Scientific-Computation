import os
import base64
import json
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel,
                               QDialog, QTableWidget, QTableWidgetItem,
                               QHeaderView, QSizePolicy, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt, QSize, QSettings, QTimer, QUrl
from PySide6.QtGui import QColor
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage

from .toolbar import MathematicaToolbar
from .palettes import BasicMathAssistant, SpecialCharacters
from shared.config import AppConfig

QT_SCROLLBAR_STYLE = """
    QScrollBar:vertical { border: none; background: #1e1e1e; width: 10px; margin: 0px; }
    QScrollBar::handle:vertical { background: #424242; min-height: 20px; border-radius: 5px; margin: 2px; }
    QScrollBar::handle:vertical:hover { background: #4f4f4f; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }

    QScrollBar:horizontal { border: none; background: #1e1e1e; height: 10px; margin: 0px; }
    QScrollBar::handle:horizontal { background: #424242; min-width: 20px; border-radius: 5px; margin: 2px; }
    QScrollBar::handle:horizontal:hover { background: #4f4f4f; }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }
"""

class NotebookPage(QWebEnginePage):
    def __init__(self, app_parent, parent=None):
        super().__init__(parent)
        self.app_parent = app_parent

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        if message.startswith("EXECUTE:"):
            try:
                parts = message.split(":", 2)
                if len(parts) == 3:
                    cell_id = int(parts[1])
                    code = base64.b64decode(parts[2]).decode('utf-8')
                    QTimer.singleShot(0, lambda c=cell_id, txt=code: self.app_parent.execute_cell(c, txt))
            except Exception as e: print(f"Cell Execution Error: {e}")
            
        elif message.startswith("MANIPULATE:"):
            try:
                parts = message.split(":", 4)
                cell_id = int(parts[1])
                var_name = parts[2]
                var_val = float(parts[3])
                expr = base64.b64decode(parts[4]).decode('utf-8')
                QTimer.singleShot(0, lambda c=cell_id, vn=var_name, vv=var_val, ex=expr: self.app_parent.update_manipulate(c, vn, vv, ex))
            except Exception as e: print(f"Manipulate Update Error: {e}")
            
        elif message == "TRIGGER_AUTOSAVE":
            QTimer.singleShot(0, self.app_parent.trigger_auto_save)
            
        else:
            super().javaScriptConsoleMessage(level, message, lineNumber, sourceID)

class VariableInspectorDialog(QDialog):
    def __init__(self, variables, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Variable Inspector"))
        self.resize(400, 500)
        self.setStyleSheet(f"""
            QDialog {{ background-color: #252526; color: white; }}
            QTableWidget {{ background-color: #1e1e1e; color: #d4d4d4; border: 1px solid #333; gridline-color: #333; }}
            QHeaderView::section {{ background-color: #333; color: white; padding: 4px; border: none; }}
            {QT_SCROLLBAR_STYLE}
        """)
        
        layout = QVBoxLayout(self)
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels([self.tr("Variable"), self.tr("Value / Expression")])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setRowCount(len(variables))
        for i, (name, val) in enumerate(sorted(variables.items())):
            self.table.setItem(i, 0, QTableWidgetItem(name))
            self.table.setItem(i, 1, QTableWidgetItem(str(val)))
            
        layout.addWidget(self.table)
        btn = QPushButton(self.tr("Close"))
        btn.clicked.connect(self.accept)
        btn.setStyleSheet("background: #007acc; color: white; border: none; padding: 8px; border-radius: 4px;")
        layout.addWidget(btn)

class DocumentationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("MESC-Mathematica IDE Documentation"))
        self.resize(900, 750)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.browser = QWebEngineView()
        
        current_dir = os.path.dirname(__file__)
        doc_path = os.path.abspath(os.path.join(current_dir, "..", "..", "..", "docs", "MATHEMATICA_IDE.html"))
        
        if os.path.exists(doc_path):
            with open(doc_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            self.browser.setHtml(html_content)
        else:
            error_html = f"""
            <div style="color: #d4d4d4; font-family: sans-serif; padding: 20px; background-color: #1e1e1e; height: 100vh;">
                <h2 style="color: #e06c75;">{self.tr("Documentation File Not Found")}</h2>
                <p>{self.tr("The system looked for the documentation file at:")}</p>
                <pre style="background: #252526; padding: 10px; border: 1px solid #555;">{doc_path}</pre>
                <p>{self.tr("Please ensure you saved the HTML file exactly as 'MATHEMATICA_IDE.html' in the 'docs' folder.")}</p>
            </div>
            """
            self.browser.setHtml(error_html)
            
        layout.addWidget(self.browser)

class SyntaxGuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("MESC-Mathematica Syntax & User Guide"))
        self.resize(950, 750)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.browser = QWebEngineView()
        
        current_dir = os.path.dirname(__file__)
        doc_path = os.path.abspath(os.path.join(current_dir, "..", "..", "..", "docs", "MATHEMATICA_SYNTAX.html"))
        
        if os.path.exists(doc_path):
            with open(doc_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            self.browser.setHtml(html_content)
        else:
            error_html = f"""
            <div style="color: #d4d4d4; font-family: sans-serif; padding: 20px; background-color: #1e1e1e; height: 100vh;">
                <h2 style="color: #e06c75;">{self.tr("Syntax Guide Not Found")}</h2>
                <p>{self.tr("The system looked for the file at:")}</p>
                <pre style="background: #252526; padding: 10px; border: 1px solid #555;">{doc_path}</pre>
                <p>{self.tr("Please ensure you saved the file exactly as 'MATHEMATICA_SYNTAX.html' in the 'docs' folder.")}</p>
            </div>
            """
            self.browser.setHtml(error_html)
            
        layout.addWidget(self.browser)

class MathematicaApp(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.backend = None
        self.current_save_path = ""
        self.palettes = {} 
        self.setStyleSheet(f"QWidget {{ background-color: #1e1e1e; }} {QT_SCROLLBAR_STYLE}")
        self._init_ui()
        
        self.browser.loadFinished.connect(self._on_browser_ready)

    def _on_browser_ready(self, ok):
        if not ok: return
        
        if not self.backend:
            from ..kernel.engine import MathematicaBackend
            self.backend = MathematicaBackend()
            self.output_display_message(f"<b style='color: #98c379;'>{self.tr('Kernel Ready.')}</b>")
            
        self._restore_auto_state(True)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.toolbar = MathematicaToolbar(self)
        layout.addWidget(self.toolbar)

        self.browser = QWebEngineView()
        self.browser.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.browser.setStyleSheet("background-color: #1e1e1e;")
        
        self.page = NotebookPage(self, self.browser)
        self.page.setBackgroundColor(QColor("#1e1e1e"))
        self.browser.setPage(self.page)

        current_dir = os.path.dirname(__file__)
        mathjax_local_path = os.path.abspath(os.path.join(current_dir, "..", "..", "..", "resources", "mathjax", "tex-mml-svg.js"))
        if os.path.exists(mathjax_local_path):
            mathjax_src = QUrl.fromLocalFile(mathjax_local_path).toString()
        else:
            mathjax_src = "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-svg.js"

        # FIX: Link the local Plotly engine globally in the header
        plotly_local_path = os.path.abspath(os.path.join(current_dir, "..", "..", "..", "resources", "plotly", "plotly.min.js"))
        if os.path.exists(plotly_local_path):
            plotly_src = QUrl.fromLocalFile(plotly_local_path).toString()
        else:
            plotly_src = "https://cdn.plot.ly/plotly-2.32.0.min.js"

        if AppConfig.get_language() == "as":
            body_font = "'Nirmala UI', 'Noto Sans Bengali', 'Segoe UI', sans-serif"
            code_font = "'Nirmala UI', 'Cascadia Mono', 'Consolas', monospace"
            cell_placeholder = "গণিত লিখক... (Shift+Enter চলাবলৈ) | Mathematica / Assamese dual syntax"
        else:
            body_font = "'Segoe UI', sans-serif"
            code_font = "Consolas, monospace"
            cell_placeholder = "Type math here... (Shift+Enter to run) | Mathematica / dual syntax"
        
        self.base_html = r"""
        <!DOCTYPE html>
        <html>
        <head>
            <script src="__PLOTLY_SRC__"></script>
            <script>
                window.MathJax = {
                    options: { enableMenu: false, renderActions: { assistiveMml: [] } },
                    tex: { inlineMath: [['\\(', '\\)']], displayMath: [['\\[', '\\]']] },
                    svg: { fontCache: 'global' }
                };
            </script>
            <script id="MathJax-script" async src="__MATHJAX_SRC__"></script>
            <style>
                ::-webkit-scrollbar { width: 10px; height: 10px; }
                ::-webkit-scrollbar-track { background: #1e1e1e; }
                ::-webkit-scrollbar-thumb { background: #424242; border-radius: 5px; }
                ::-webkit-scrollbar-thumb:hover { background: #4f4f4f; }
                ::-webkit-scrollbar-corner { background: #1e1e1e; }

                body { background-color: #1e1e1e; color: #d4d4d4; font-family: __BODY_FONT__; margin: 0; padding: 15px; padding-bottom: 250px; }
                
                .cell { position: relative; background-color: #252526; border: 1px solid #3e3e42; border-radius: 6px; padding: 10px 15px; margin-bottom: 15px; transition: border 0.2s, box-shadow 0.2s; }
                .cell:focus-within { border: 1px solid #007acc; box-shadow: 0 0 8px rgba(0, 122, 204, 0.2); }
                
                .cell-controls { position: absolute; top: 6px; right: 6px; z-index: 10; opacity: 0; transition: opacity 0.2s ease-in-out; }
                .cell:hover .cell-controls { opacity: 1; }
                .cell-controls button { background: transparent; border: none; color: #cccccc; cursor: pointer; font-size: 18px; line-height: 1; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-family: sans-serif; }
                .cell-controls button:hover { color: #ffffff; background-color: #e06c75; }

                .row { display: flex; gap: 10px; align-items: flex-start; }
                .row-out { margin-top: 10px; display: none; border-top: 1px dashed #3e3e42; padding-top: 10px; } 
                
                .prompt { font-family: Consolas; font-weight: bold; font-size: 13px; width: 65px; text-align: right; flex-shrink: 0; padding-top: 6px; user-select: none; }
                .prompt-in { color: #61afef; }
                .prompt-out { color: #7f8c8d; }
                
                textarea { box-sizing: border-box; flex-grow: 1; background-color: transparent; color: #dcdcaa; border: none; padding: 4px 8px; font-family: __CODE_FONT__; font-size: 14px; font-weight: bold; resize: none; overflow: hidden; outline: none; line-height: 1.5; transition: opacity 0.3s; }
                textarea[readonly] { cursor: default; }
                .output-container { flex-grow: 1; overflow-x: auto; padding-top: 6px; font-family: __BODY_FONT__;}
            </style>
        </head>
        <body>
            <div id="notebook"></div>
            <script>
                function utf8_to_b64(str) {
                    const bytes = new TextEncoder().encode(str);
                    let binary = '';
                    for (let i = 0; i < bytes.byteLength; i++) {
                        binary += String.fromCharCode(bytes[i]);
                    }
                    return window.btoa(binary);
                }

                function b64_to_utf8(str) {
                    const binary = window.atob(str);
                    const bytes = new Uint8Array(binary.length);
                    for (let i = 0; i < binary.length; i++) {
                        bytes[i] = binary.charCodeAt(i);
                    }
                    return new TextDecoder().decode(bytes);
                }
                
                // FIX: Foolproof script cloner. Forces Chromium to execute Plotly code injected via innerHTML.
                function injectScriptableHTML(container, htmlContent) {
                    container.innerHTML = htmlContent;
                    Array.from(container.querySelectorAll("script")).forEach(oldScript => {
                        const newScript = document.createElement("script");
                        Array.from(oldScript.attributes).forEach(attr => newScript.setAttribute(attr.name, attr.value));
                        newScript.appendChild(document.createTextNode(oldScript.innerHTML));
                        oldScript.parentNode.replaceChild(newScript, oldScript);
                    });
                }

                let maxCellId = 0;
                let activeCellId = 1;

                const txObserver = new ResizeObserver(entries => {
                    window.requestAnimationFrame(() => {
                        if (!Array.isArray(entries) || !entries.length) return;
                        for (let entry of entries) {
                            autoResize(entry.target);
                        }
                    });
                });

                function autoResize(el) {
                    el.style.height = '1px'; 
                    el.style.height = (el.scrollHeight) + 'px';
                }

                function handleKey(e, id) {
                    if (e.key === 'Enter' && e.shiftKey) {
                        e.preventDefault();
                        let code = e.target.value;
                        if (code.trim() === '') return;
                        
                        e.target.readOnly = true;
                        e.target.style.opacity = '0.7'; 
                        e.target.blur(); 
                        
                        console.log("EXECUTE:" + id + ":" + utf8_to_b64(code));
                    }
                }

                function createCell(id) {
                    if (id > maxCellId) maxCellId = id;
                    activeCellId = id;
                    
                    let html = `
                    <div class='cell' id='cell-${id}'>
                        <div class='cell-controls' id='controls-${id}' style='display: none;'>
                            <button onclick="deleteCell(${id})" title="Delete Cell">×</button>
                        </div>
                        <div class='row'>
                            <div class='prompt prompt-in'>In[${id}]:=</div>
                            <textarea id='input-${id}' rows='1' placeholder='__CELL_PLACEHOLDER__' 
                                      oninput='autoResize(this)' onfocus='activeCellId = ${id}' 
                                      onblur='autoSave()' onkeydown='handleKey(event, ${id})'
                                      ondblclick='this.readOnly=false; this.style.opacity="1"; this.focus();'
                                      title='Double-click to unlock cell for editing'></textarea>
                        </div>
                        <div class='row row-out' id='row-out-${id}'>
                            <div class='prompt prompt-out'>Out[${id}]=</div>
                            <div class='output-container' id='output-${id}'></div>
                        </div>
                    </div>
                    `;
                    
                    document.getElementById('notebook').insertAdjacentHTML('beforeend', html);
                    let ta = document.getElementById(`input-${id}`);
                    if (ta) {
                        txObserver.observe(ta);
                        ta.focus();
                    }
                    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
                }

                function deleteCell(id) {
                    let cell = document.getElementById(`cell-${id}`);
                    if (cell) {
                        cell.remove();
                        let maxFound = 0;
                        document.querySelectorAll('.cell').forEach(c => {
                            let idMatch = c.id ? c.id.match(/cell-(\d+)/) : null;
                            if (idMatch) {
                                let curId = parseInt(idMatch[1]);
                                if (curId > maxFound) maxFound = curId;
                            }
                        });
                        maxCellId = maxFound;
                        
                        if (maxCellId === 0) createCell(1);
                        autoSave();
                    }
                }

                function autoSave() {
                    console.log("TRIGGER_AUTOSAVE");
                }

                function setOutput(id, b64_html) {
                    try {
                        const html = b64_to_utf8(b64_html);
                        const outDiv = document.getElementById(`output-${id}`);
                        const rowOut = document.getElementById(`row-out-${id}`);
                        
                        if (outDiv) {
                            injectScriptableHTML(outDiv, html);
                            outDiv.setAttribute('data-raw', b64_html); 
                        }
                        if (rowOut) rowOut.style.display = 'flex';
                        
                        const controls = document.getElementById(`controls-${id}`);
                        if (controls) controls.style.display = 'block';
                        
                        if (id === maxCellId) {
                            if (!document.getElementById(`cell-${maxCellId + 1}`)) {
                                createCell(maxCellId + 1);
                            }
                        }

                        if (typeof MathJax !== 'undefined' && typeof MathJax.typesetPromise === 'function') {
                            MathJax.typesetPromise([outDiv]).then(() => {
                                if (id >= maxCellId - 1) window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
                                autoSave();
                            }).catch(err => {
                                console.error("MathJax Render Error:", err);
                                autoSave();
                            });
                        } else {
                            autoSave();
                        }
                    } catch (e) {
                        console.error("Output Display Error:", e);
                        autoSave();
                    }
                }

                function appendSystemMessage(b64_html) {
                    const html = b64_to_utf8(b64_html);
                    const uniqueId = 'sys-' + Date.now() + '-' + Math.floor(Math.random()*1000);
                    let sysHtml = `
                    <div class='cell' style='border-color: #569cd6; background-color: #1e1e1e;'>
                        <div class='row'>
                            <div class='prompt' style='color: #569cd6;'>Sys:</div>
                            <div class='output-container' id='${uniqueId}' style='display: block;' data-raw='${b64_html}'></div>
                        </div>
                    </div>
                    `;
                    let activeCell = document.getElementById(`cell-${maxCellId}`);
                    if (activeCell) activeCell.insertAdjacentHTML('beforebegin', sysHtml);
                    else document.getElementById('notebook').insertAdjacentHTML('beforeend', sysHtml);
                    
                    let container = document.getElementById(uniqueId);
                    if (container) {
                        injectScriptableHTML(container, html);
                    }
                    
                    if (typeof MathJax !== 'undefined' && typeof MathJax.typesetPromise === 'function') {
                        MathJax.typesetPromise().then(autoSave).catch(e => { console.error(e); autoSave(); });
                    } else {
                        autoSave();
                    }
                }

                function updateManipulate(value, cellId, varName, b64Expr) {
                    let lbl = document.getElementById(`val-${varName}-${cellId}`);
                    if(lbl) lbl.innerText = parseFloat(value).toFixed(2);
                    console.log(`MANIPULATE:${cellId}:${varName}:${value}:${b64Expr}`);
                    autoSave();
                }

                function clearNotebook() {
                    document.getElementById('notebook').innerHTML = "";
                    maxCellId = 0;
                    activeCellId = 1;
                    createCell(1);
                    autoSave();
                }

                function getNotebookState() {
                    let cells = [];
                    document.querySelectorAll('.cell').forEach(cell => {
                        let idMatch = cell.id ? cell.id.match(/cell-(\d+)/) : null;
                        if (idMatch) {
                            let id = parseInt(idMatch[1]);
                            let ta = document.getElementById(`input-${id}`);
                            let outDiv = document.getElementById(`output-${id}`);
                            let rowOut = document.getElementById(`row-out-${id}`);

                            let rawOutput = "";
                            if (outDiv) {
                                let b64 = outDiv.getAttribute('data-raw');
                                rawOutput = b64 ? b64_to_utf8(b64) : outDiv.innerHTML;
                            }

                            cells.push({
                                type: 'code',
                                id: id,
                                input: ta ? ta.value : "",
                                output: rawOutput,
                                hasOutput: rowOut ? (rowOut.style.display !== 'none' && rowOut.style.display !== '') : false
                            });
                        } else if (cell.querySelector('.prompt') && cell.querySelector('.prompt').innerText === 'Sys:') {
                            let outContainer = cell.querySelector('.output-container');
                            let rawOutput = "";
                            if (outContainer) {
                                let b64 = outContainer.getAttribute('data-raw');
                                rawOutput = b64 ? b64_to_utf8(b64) : outContainer.innerHTML;
                            }
                            cells.push({
                                type: 'system',
                                content: rawOutput
                            });
                        }
                    });

                    let globalCacheHTML = "";
                    let globalCache = document.getElementById("MathJax_SVG_global_cache");
                    if (globalCache && globalCache.closest('svg')) {
                        globalCacheHTML = globalCache.closest('svg').outerHTML;
                    }

                    return JSON.stringify({
                        maxCellId: maxCellId,
                        cells: cells,
                        globalCache: globalCacheHTML
                    });
                }

                function getNotebookInputs() {
                    let cells = [];
                    document.querySelectorAll('.cell').forEach(cell => {
                        let idMatch = cell.id ? cell.id.match(/cell-(\d+)/) : null;
                        if (!idMatch) return;

                        let id = parseInt(idMatch[1]);
                        let ta = document.getElementById(`input-${id}`);
                        if (!ta) return;

                        cells.push({
                            id: id,
                            input: ta.value || ""
                        });
                    });

                    return JSON.stringify(cells);
                }

                function restoreNotebookState(b64_state) {
                    const state = JSON.parse(b64_to_utf8(b64_state));
                    
                    if (state.globalCache) {
                        let existing = document.getElementById("MathJax_SVG_global_cache");
                        if (existing && existing.closest('svg')) {
                            existing.closest('svg').remove();
                        }
                        document.body.insertAdjacentHTML('afterbegin', state.globalCache);
                    }
                    
                    document.getElementById('notebook').innerHTML = "";
                    maxCellId = state.maxCellId || 0;
                    activeCellId = maxCellId || 1;
                    
                    if (state.cells && state.cells.length > 0) {
                        state.cells.forEach(c => {
                            if (c.type === 'system') {
                                let b64 = utf8_to_b64(c.content || "");
                                const uniqueId = 'sys-restored-' + Date.now() + '-' + Math.floor(Math.random()*10000);
                                let sysHtml = `
                                <div class='cell' style='border-color: #569cd6; background-color: #1e1e1e;'>
                                    <div class='row'>
                                        <div class='prompt' style='color: #569cd6;'>Sys:</div>
                                        <div class='output-container' id='${uniqueId}' style='display: block;' data-raw='${b64}'></div>
                                    </div>
                                </div>
                                `;
                                document.getElementById('notebook').insertAdjacentHTML('beforeend', sysHtml);
                                let container = document.getElementById(uniqueId);
                                if (container) injectScriptableHTML(container, c.content || "");
                            } else {
                                let id = c.id;
                                let displayStyle = c.hasOutput ? "display: flex;" : "display: none;";
                                let btnStyle = c.hasOutput ? "display: block;" : "display: none;";
                                let b64 = utf8_to_b64(c.output || "");
                                
                                let html = `
                                <div class='cell' id='cell-${id}'>
                                    <div class='cell-controls' id='controls-${id}' style='${btnStyle}'>
                                        <button onclick="deleteCell(${id})" title="Delete Cell">×</button>
                                    </div>
                                    <div class='row'>
                                        <div class='prompt prompt-in'>In[${id}]:=</div>
                                        <textarea id='input-${id}' rows='1' placeholder='__CELL_PLACEHOLDER__' 
                                                  oninput='autoResize(this)' onfocus='activeCellId = ${id}' 
                                                  onblur='autoSave()' onkeydown='handleKey(event, ${id})'
                                                  ondblclick='this.readOnly=false; this.style.opacity="1"; this.focus();'
                                                  title='Double-click to unlock cell for editing'></textarea>
                                    </div>
                                    <div class='row row-out' id='row-out-${id}' style='${displayStyle}'>
                                        <div class='prompt prompt-out'>Out[${id}]=</div>
                                        <div class='output-container' id='output-${id}' data-raw='${b64}'></div>
                                    </div>
                                </div>
                                `;
                                document.getElementById('notebook').insertAdjacentHTML('beforeend', html);
                                
                                let outContainer = document.getElementById(`output-${id}`);
                                if (outContainer && c.output) {
                                    injectScriptableHTML(outContainer, c.output);
                                }
                                
                                let ta = document.getElementById(`input-${id}`);
                                if (ta) {
                                    ta.value = c.input || "";
                                    txObserver.observe(ta);
                                    
                                    if (c.hasOutput) {
                                        ta.readOnly = true;
                                        ta.style.opacity = '0.7';
                                    }
                                }
                            }
                        });
                    } else if (state.html) {
                        document.getElementById('notebook').innerHTML = state.html;
                        document.querySelectorAll('textarea').forEach(ta => {
                            if (ta.hasAttribute('data-value')) {
                                ta.value = ta.getAttribute('data-value');
                                txObserver.observe(ta);
                            }
                        });
                    } else {
                        createCell(1);
                    }
                    
                    if (typeof MathJax !== 'undefined' && typeof MathJax.typesetPromise === 'function') {
                        MathJax.typesetPromise().catch(e => console.error(e));
                    }
                    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
                }

                createCell(1);
            </script>
        </body>
        </html>
        """
        self.base_html = (
            self.base_html
            .replace("__BODY_FONT__", body_font)
            .replace("__CODE_FONT__", code_font)
            .replace("__CELL_PLACEHOLDER__", cell_placeholder)
            .replace("__MATHJAX_SRC__", mathjax_src)
            .replace("__PLOTLY_SRC__", plotly_src)
        )
        self.browser.setHtml(self.base_html, QUrl.fromLocalFile(current_dir + os.sep))
        layout.addWidget(self.browser)

    def trigger_auto_save(self):
        self.browser.page().runJavaScript("getNotebookState();", self._save_auto_state)

    def _save_auto_state(self, ui_state_json_str):
        if not self.backend: return
        try:
            settings = QSettings("Mathematica", "IDE")
            settings.setValue("auto_ui_state", ui_state_json_str)
            vars_dict = self.backend.get_user_variables() if hasattr(self.backend, 'get_user_variables') else self.backend.session_vars
            backend_state = {k: str(v) for k, v in vars_dict.items()}
            settings.setValue("auto_backend_state", json.dumps(backend_state))
        except Exception as e: print(f"Failed to auto-save: {e}")

    def _restore_auto_state(self, ok):
        if not ok: return
        
        def do_restore():
            if not self.backend:
                QTimer.singleShot(100, do_restore)
                return
                
            try:
                import sympy
                if hasattr(self.backend, '_ensure_loaded'):
                    self.backend._ensure_loaded()
                    
                settings = QSettings("Mathematica", "IDE")
                backend_state_json = settings.value("auto_backend_state", None)
                if backend_state_json:
                    state = json.loads(backend_state_json)
                    self.backend.command_mapping.update({k: sympy.sympify(v_str) for k, v_str in state.items()})
                ui_state_json_str = settings.value("auto_ui_state", None)
                if ui_state_json_str:
                    b64_state = base64.b64encode(ui_state_json_str.encode('utf-8')).decode('utf-8')
                    self.browser.page().runJavaScript(f"restoreNotebookState('{b64_state}');")
            except Exception as e: 
                print(f"Failed to auto-restore: {e}")
                
        do_restore()

    def execute_cell(self, cell_id, code):
        if not self.backend:
            self.output_display_message(f"<b style='color: #e06c75;'>{self.tr('Kernel loading, please wait...')}</b>")
            return
            
        result_html = self.backend.execute(code, cell_id=cell_id)
        if not result_html or not str(result_html).strip():
            result_html = f"<span style='color: #666;'><i>({self.tr('No output')})</i></span>"
        b64_html = base64.b64encode(result_html.encode('utf-8')).decode('utf-8')
        self.browser.page().runJavaScript(f"setOutput({cell_id}, '{b64_html}');")

    def update_manipulate(self, cell_id, var_name, var_value, expr_str):
        if not self.backend: return
        old_val = self.backend.command_mapping.get(var_name, None)
        try:
            self.backend.command_mapping[var_name] = var_value
            res_html = self.backend.execute(expr_str, cell_id=cell_id)
            if not res_html or not str(res_html).strip(): res_html = f"<i>({self.tr('No output')})</i>"
            b64_html = base64.b64encode(res_html.encode('utf-8')).decode('utf-8')
            
            js = f"""
            (function() {{
                const display = document.getElementById('manipulate-display-{cell_id}');
                if (display) {{
                    injectScriptableHTML(display, b64_to_utf8('{b64_html}'));
                    if (typeof MathJax !== 'undefined' && typeof MathJax.typesetPromise === 'function') {{
                        MathJax.typesetPromise([display]).catch(e => console.error(e));
                    }}
                }}
            }})();
            """
            self.browser.page().runJavaScript(js)
        except Exception as e:
            print(f"Manipulate Error: {e}")
        finally:
            if old_val is not None:
                self.backend.command_mapping[var_name] = old_val
            else:
                self.backend.command_mapping.pop(var_name, None)

    def show_palette(self, name):
        if name == "basic":
            if "basic" not in self.palettes:
                self.palettes["basic"] = BasicMathAssistant(self)
            self.palettes["basic"].show()
            self.palettes["basic"].raise_()
        elif name == "special":
            if "special" not in self.palettes:
                self.palettes["special"] = SpecialCharacters(self)
            self.palettes["special"].show()
            self.palettes["special"].raise_()

    def insert_template(self, text):
        b64_text = base64.b64encode(text.encode('utf-8')).decode('utf-8')
        js = f"""
            (function() {{
                let ta = document.getElementById(`input-${{activeCellId}}`);
                if (!ta) {{
                    ta = document.getElementById(`input-${{maxCellId}}`);
                }}
                if (ta) {{
                    let insertText = b64_to_utf8('{b64_text}');
                    let start = ta.selectionStart;
                    let end = ta.selectionEnd;
                    
                    if (start === undefined || start === null) {{
                        start = ta.value.length;
                        end = ta.value.length;
                    }}
                    
                    ta.value = ta.value.substring(0, start) + insertText + ta.value.substring(end);
                    ta.selectionStart = ta.selectionEnd = start + insertText.length;
                    ta.focus();
                    
                    autoResize(ta); 
                }}
            }})();
        """
        self.browser.page().runJavaScript(js)

    def evaluate_notebook(self):
        self.browser.page().runJavaScript("getNotebookInputs();", self._finish_evaluate_notebook)

    def _finish_evaluate_notebook(self, cells_json):
        try:
            cells = json.loads(cells_json) if cells_json else []
        except Exception as e:
            self.output_display_message(f"<b style='color: #e06c75;'>{self.tr('Notebook evaluation failed:')} {str(e)}</b>")
            return

        ran_any = False
        for cell in cells:
            code = (cell.get("input") or "").strip()
            if not code:
                continue
            ran_any = True
            self.execute_cell(int(cell["id"]), code)

        if not ran_any:
            self.output_display_message(f"<i>{self.tr('No executable cells found in the notebook.')}</i>")
        else:
            self.output_display_message(f"<i>{self.tr('Notebook evaluation completed.')}</i>")
        
    def quit_kernel(self):
        from ..kernel.engine import MathematicaBackend
        self.backend = MathematicaBackend()
        self.output_display_message(f"<b style='color: #e06c75;'>{self.tr('Kernel has been restarted. All variables and definitions have been cleared.')}</b>")
        self.browser.page().runJavaScript("autoSave();")

    def show_message(self, title, msg):
        QMessageBox.information(self, title, msg)
        
    def show_documentation(self):
        dlg = DocumentationDialog(self)
        dlg.exec()
        
    def show_syntax_guide(self):
        dlg = SyntaxGuideDialog(self)
        dlg.exec()

    def save_session_dialog(self):
        file_path, _ = QFileDialog.getSaveFileName(self, self.tr("Save Mathematica Notebook"), "", self.tr("Math Notebook (*.mathnotebook);;All Files (*)"))
        if file_path:
            self.current_save_path = file_path
            self.browser.page().runJavaScript("getNotebookState();", self._finish_save_session)

    def _finish_save_session(self, ui_state_json_str):
        if not self.backend: return
        if hasattr(self.backend, '_ensure_loaded'):
            self.backend._ensure_loaded()
            
        try:
            ui_state = json.loads(ui_state_json_str)
            user_vars = self.backend.get_user_variables()
            backend_state = {k: str(v) for k, v in user_vars.items()}
            with open(self.current_save_path, 'w', encoding='utf-8') as f:
                json.dump({"ui_state": ui_state, "backend_state": backend_state}, f, indent=4)
            QMessageBox.information(self, self.tr("Success"), self.tr("Notebook saved successfully!"))
        except Exception as e: QMessageBox.critical(self, self.tr("Error"), f"{self.tr('Failed to save notebook:')} {str(e)}")

    def load_session_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, self.tr("Load Mathematica Notebook"), "", self.tr("Math Notebook (*.mathnotebook);;All Files (*)"))
        if file_path:
            try:
                import sympy
                if not self.backend: return
                if hasattr(self.backend, '_ensure_loaded'):
                    self.backend._ensure_loaded()
                    
                with open(file_path, 'r', encoding='utf-8') as f: data = json.load(f)
                if "backend_state" in data:
                    self.backend.command_mapping.update({k: sympy.sympify(v_str) for k, v_str in data["backend_state"].items()})
                if "ui_state" in data:
                    b64_state = base64.b64encode(json.dumps(data["ui_state"]).encode('utf-8')).decode('utf-8')
                    self.browser.page().runJavaScript(f"restoreNotebookState('{b64_state}');")
                self.output_display_message(f"<i>{self.tr('Loaded notebook from:')} {os.path.basename(file_path)}</i>")
            except Exception as e: QMessageBox.critical(self, self.tr("Error"), f"{self.tr('Failed to load notebook:')} {str(e)}")

    def export_pdf_dialog(self):
        file_path, _ = QFileDialog.getSaveFileName(self, self.tr("Export Notebook to PDF"), "", self.tr("PDF Document (*.pdf)"))
        if file_path:
            self.page.pdfPrintingFinished.connect(self._on_pdf_finished)
            self.page.printToPdf(file_path)

    def _on_pdf_finished(self, file_path, success):
        try: self.page.pdfPrintingFinished.disconnect(self._on_pdf_finished)
        except: pass
        if success: QMessageBox.information(self, self.tr("Success"), f"{self.tr('Notebook exported to PDF:')}\n{file_path}")

    def output_display_message(self, html_msg):
        b64_html = base64.b64encode(html_msg.encode('utf-8')).decode('utf-8')
        self.browser.page().runJavaScript(f"appendSystemMessage('{b64_html}');")

    def clear_history(self):
        self.browser.page().runJavaScript("clearNotebook();")

    def show_variables(self):
        if not self.backend: return
        if hasattr(self.backend, '_ensure_loaded'):
            self.backend._ensure_loaded()
        vars_dict = self.backend.get_user_variables() if hasattr(self.backend, 'get_user_variables') else self.backend.session_vars 
        VariableInspectorDialog(vars_dict, self).exec()
        
    def set_simple_mode(self, enabled):
        if not self.backend: return
        self.backend.simple_mode = enabled
        state_msg = self.tr("ON") if enabled else self.tr("OFF")
        color = "#98c379" if enabled else "#e06c75"
        self.output_display_message(f"<b style='color: {color};'>{self.tr('Simple Mode is now')} {state_msg}.</b>")