# mathex/ui/console.py
from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtGui import (
    QTextCursor, QFont, QColor,
    QTextCharFormat, QKeySequence
)
from PySide6.QtCore import Qt, Signal, QEvent
from shared.config import AppConfig

# [FIX] Import the algorithmic engine instead of the hardcoded map
from ..language.phonetics import get_assamese_suggestions
from ..language.locale import tr


class ConsoleWidget(QPlainTextEdit):
    command_entered = Signal(str)

    COLOR_BG = "#181818"
    COLOR_TRANSCRIPT = "#ffffff"  
    COLOR_PROMPT = "#ffffff"      
    COLOR_INPUT = "#aaaaaa"       
    COLOR_ERROR = "#ff5555"

    PROMPT = ">> "
    CONTINUATION = "... "

    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._reset_state()
        self._init_console()

    def initialize(self, text=""):
        self.clear()
        if text:
            self._append_transcript(text)
        self._insert_prompt()

    def _setup_ui(self):
        self.setUndoRedoEnabled(False)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setFrameShape(QPlainTextEdit.NoFrame)

        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)
        self.document().setDefaultFont(font) 

        self.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {self.COLOR_BG};
                color: {self.COLOR_TRANSCRIPT};
                border: none;
                padding: 4px;
                selection-background-color: #264f78;
                selection-color: #ffffff;
            }}
        """)

    def _reset_state(self):
        self.history = []
        self.history_index = -1
        self.multi_line_buffer = []
        self.locked_pos = 0 

    def _fmt(self, color):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        return fmt

    def _init_console(self):
        self.clear()
        self._append_transcript(tr("console_banner") + "\n")
        self._insert_prompt()

    def changeEvent(self, event):
        if event.type() == QEvent.Type.LanguageChange and self.document().characterCount() <= 2:
            self._init_console()
        super().changeEvent(event)

    def _insert_prompt(self, continuation=False):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)

        prompt = self.CONTINUATION if continuation else self.PROMPT
        cursor.insertText(prompt, self._fmt(self.COLOR_PROMPT))

        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)
        self.setCurrentCharFormat(self._fmt(self.COLOR_INPUT))
        self.locked_pos = cursor.position()

    def _append_transcript(self, text, color=None):
        if color is None:
            color = self.COLOR_TRANSCRIPT

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)

        if self.document().characterCount() > 1 and not self.document().toPlainText().endswith("\n"):
            cursor.insertText("\n")

        cursor.insertText(text.rstrip("\n") + "\n", self._fmt(color))
        self.setTextCursor(cursor)

    def _enforce_boundary(self):
        cursor = self.textCursor()

        if cursor.position() < self.locked_pos:
            cursor.setPosition(self.locked_pos)
            self.setTextCursor(cursor)

        if cursor.hasSelection() and cursor.selectionStart() < self.locked_pos:
            cursor.setPosition(self.locked_pos)
            cursor.setPosition(cursor.selectionEnd(), QTextCursor.KeepAnchor)
            self.setTextCursor(cursor)
        
        if cursor.position() >= self.locked_pos:
            self.setCurrentCharFormat(self._fmt(self.COLOR_INPUT))

    def keyPressEvent(self, event):
        cursor = self.textCursor()

        in_transcript = cursor.position() < self.locked_pos
        selection_crosses = (
            cursor.hasSelection() and cursor.selectionStart() < self.locked_pos
        )

        if event.matches(QKeySequence.SelectAll) or event.matches(QKeySequence.Undo) or event.matches(QKeySequence.Redo):
            return

        if event.matches(QKeySequence.Copy):
            super().keyPressEvent(event)
            return

        if event.matches(QKeySequence.Paste):
            if in_transcript or selection_crosses:
                cursor.clearSelection()
                cursor.movePosition(QTextCursor.End)
                self.setTextCursor(cursor)
            self.setCurrentCharFormat(self._fmt(self.COLOR_INPUT))
            super().keyPressEvent(event)
            return

        if event.matches(QKeySequence.Cut):
            if selection_crosses:
                return
            super().keyPressEvent(event)
            return

        if event.key() == Qt.Key_Home and not event.modifiers():
            cursor.setPosition(self.locked_pos)
            self.setTextCursor(cursor)
            self.setCurrentCharFormat(self._fmt(self.COLOR_INPUT))
            return

        if event.modifiers() & Qt.ControlModifier and event.key() == Qt.Key_L:
            self.clear()
            self._insert_prompt()
            return

        if event.key() in (Qt.Key_Up, Qt.Key_Down):
            self._handle_history(event.key())
            return

        # ---- PHONETIC TRANSLITERATION ----
        if AppConfig.get_language() == "as":
            if event.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter) and not (in_transcript or selection_crosses):
                temp_cursor = self.textCursor()
                temp_cursor.select(QTextCursor.WordUnderCursor)
                word = temp_cursor.selectedText()
                
                # [FIX]: Use algorithmic suggestions and auto-insert the highest confidence match
                if word.isalpha():
                    suggestions = get_assamese_suggestions(word)
                    if suggestions:
                        temp_cursor.insertText(suggestions[0], self._fmt(self.COLOR_INPUT))

        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._handle_enter()
            return

        if event.key() in (Qt.Key_Backspace, Qt.Key_Delete):
            if in_transcript or selection_crosses:
                return
            if event.key() == Qt.Key_Backspace and cursor.position() == self.locked_pos:
                return

        if event.text() and (in_transcript or selection_crosses):
            cursor.clearSelection()
            cursor.movePosition(QTextCursor.End)
            self.setTextCursor(cursor)

        if event.text() and not event.modifiers():
             self.setCurrentCharFormat(self._fmt(self.COLOR_INPUT))

        super().keyPressEvent(event)
        self._enforce_boundary()

    def keyReleaseEvent(self, event):
        super().keyReleaseEvent(event)
        self._enforce_boundary()

    def _handle_enter(self):
        cursor = self.textCursor()
        cursor.setPosition(self.locked_pos)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        cmd = cursor.selectedText().strip()

        cursor.clearSelection()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)
        self.appendPlainText("")

        if cmd.endswith("..."):
            self.multi_line_buffer.append(cmd[:-3])
            self._insert_prompt(continuation=True)
            return

        full_cmd = cmd
        if self.multi_line_buffer:
            self.multi_line_buffer.append(cmd)
            full_cmd = " ".join(self.multi_line_buffer)
            self.multi_line_buffer.clear()

        if full_cmd:
            self._push_history(full_cmd)
            self.command_entered.emit(full_cmd)
        else:
            self._insert_prompt()

    def _push_history(self, cmd):
        if not self.history or self.history[-1] != cmd:
            self.history.append(cmd)
        self.history_index = len(self.history)

    def _handle_history(self, key):
        if not self.history:
            return

        if key == Qt.Key_Up and self.history_index > 0:
            self.history_index -= 1
        elif key == Qt.Key_Down and self.history_index < len(self.history):
            self.history_index += 1

        text = (
            self.history[self.history_index]
            if 0 <= self.history_index < len(self.history)
            else ""
        )

        cursor = self.textCursor()
        cursor.setPosition(self.locked_pos)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        cursor.insertText(text, self._fmt(self.COLOR_INPUT))
        self.setTextCursor(cursor) 

    def write_output(self, text):
        if "\f" in text:
            self.clear()
            text = text.replace("\f", "")
        
        if text:
            self._append_transcript(text, self.COLOR_TRANSCRIPT)
            
        self._insert_prompt()

    def write_error(self, text):
        self._append_transcript(text, self.COLOR_ERROR)
        self._insert_prompt()

    def _print_text(self, text, color):
        self._append_transcript(text, color)
        self._insert_prompt()

    def execution_finished(self):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)

        block_text = self.document().lastBlock().text()
        if not (block_text.startswith(self.PROMPT) or block_text.startswith(self.CONTINUATION)):
            self._insert_prompt()
            
    def _prompt_end_pos(self):
        return self.locked_pos

    def is_at_prompt(self) -> bool:
        cursor = self.textCursor()
        return cursor.position() >= self._prompt_end_pos()

    def move_cursor_to_prompt(self):
        cursor = self.textCursor()
        cursor.setPosition(self._prompt_end_pos())
        self.setTextCursor(cursor)

    def get_current_input(self) -> str:
        cursor = self.textCursor()
        cursor.setPosition(self._prompt_end_pos())
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        return cursor.selectedText()

    def clear_input_only(self):
        cursor = self.textCursor()
        cursor.setPosition(self._prompt_end_pos())
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
        self.setTextCursor(cursor)

    def reset_input_line(self):
        self.clear_input_only()
        self.move_cursor_to_prompt()

    def echo_command(self, cmd: str):
        self.write_output(cmd)

    def show_busy(self):
        self.busy = True

    def show_ready(self):
        self.busy = False

    def write_warning(self, text):
        self._print_text(f"{tr('console_warning_prefix')}: {text}", QColor("#ffaa00"))

    def write_info(self, text):
        self._print_text(f"{tr('console_info_prefix')}: {text}", QColor("#7aa2f7"))

    def repeat_last_command(self):
        if not self.history:
            return
        self.reset_input_line()
        self.setCurrentCharFormat(self._fmt(self.COLOR_INPUT))
        self.insertPlainText(self.history[-1])
