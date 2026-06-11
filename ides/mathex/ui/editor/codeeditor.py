from PySide6.QtCore import QRect, Qt, QStringListModel
from PySide6.QtGui import QColor, QFont, QPainter, QTextCursor, QTextFormat
from PySide6.QtWidgets import QCompleter, QPlainTextEdit, QTextEdit

from shared.config import AppConfig

from ...language.phonetics import (
    get_assamese_suggestions,
    has_assamese_phonetic_prefix,
    is_english_canonical_word,
    should_auto_commit_assamese,
)
from .gutter import LineNumberArea
from .syntax import MatlabHighlighter


class CodeEditor(QPlainTextEdit):
    ASSAMESE_COMMIT_TEXT = {" ", "(", ")", "[", "]", "{", "}", ",", ";", ":"}

    def __init__(self):
        super().__init__()

        font = self._build_editor_font()
        self.setFont(font)
        self.document().setDefaultFont(font)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

        self.highlighter = MatlabHighlighter(self.document())
        self.breakpoints = set()
        self.error_lines = set()

        self.setStyleSheet(
            """
            QPlainTextEdit {
                background-color: #181818;
                color: #d4d4d4;
                border: none;
                selection-background-color: #264f78;
            }
        """
        )

        self.lineNumberArea = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_lines)

        self.completer = QCompleter(self)
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setMaxVisibleItems(8)
        self.completer.activated.connect(self.insert_completion)
        self.completer.popup().setFont(font)
        self.completer.popup().setStyleSheet(
            """
            QListView {
                background-color: #252526;
                color: #cccccc;
                border: 1px solid #454545;
                font-size: 11pt;
            }
            QListView::item:selected {
                background-color: #062f4a;
            }
        """
        )

        self.update_line_number_area_width()
        self.highlight_lines()

    def _build_editor_font(self) -> QFont:
        font = QFont()
        if hasattr(font, "setFamilies"):
            font.setFamilies(
                [
                    "Cascadia Mono",
                    "Consolas",
                    "Nirmala UI",
                    "Noto Sans Bengali",
                    "Segoe UI",
                ]
            )
        else:
            font.setFamily("Consolas")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(11)
        return font

    @staticmethod
    def _is_word_char(ch: str) -> bool:
        return ch.isalnum() or ch == "_" or ("\u0980" <= ch <= "\u09FF")

    def _word_bounds_at_cursor(self) -> tuple[int, int, str]:
        cursor = self.textCursor()
        block = cursor.block()
        block_text = block.text()
        relative_pos = cursor.position() - block.position()

        start = relative_pos
        end = relative_pos

        while start > 0 and self._is_word_char(block_text[start - 1]):
            start -= 1
        while end < len(block_text) and self._is_word_char(block_text[end]):
            end += 1

        absolute_start = block.position() + start
        absolute_end = block.position() + end
        return absolute_start, absolute_end, block_text[start:end]

    def _replace_word_at_cursor(self, replacement: str):
        start, end, _ = self._word_bounds_at_cursor()
        cursor = self.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        cursor.insertText(replacement)
        self.setTextCursor(cursor)
        self.completer.popup().hide()

    def insert_completion(self, completion):
        if self.completer.widget() is not self:
            return
        self._replace_word_at_cursor(completion)

    def text_under_cursor(self):
        _, _, word = self._word_bounds_at_cursor()
        return word

    def _show_assamese_completer(self, force: bool = False):
        completion_prefix = self.text_under_cursor()
        if (
            AppConfig.get_language() != "as"
            or len(completion_prefix) < 2
            or not completion_prefix.isascii()
            or not completion_prefix.isalpha()
            or (not force and not has_assamese_phonetic_prefix(completion_prefix))
        ):
            self.completer.popup().hide()
            return

        suggestions = get_assamese_suggestions(completion_prefix)
        if not suggestions:
            self.completer.popup().hide()
            return

        model = QStringListModel(suggestions, self.completer)
        self.completer.setModel(model)
        self.completer.setCompletionPrefix(completion_prefix)
        self.completer.setCurrentRow(0)

        cr = self.cursorRect()
        popup = self.completer.popup()
        popup_width = popup.sizeHintForColumn(0)
        if popup.verticalScrollBar() is not None:
            popup_width += popup.verticalScrollBar().sizeHint().width()
        cr.setWidth(max(220, popup_width + 16))
        self.completer.complete(cr)

    def _commit_assamese_completion(self, event) -> bool:
        if AppConfig.get_language() != "as":
            return False

        key = event.key()
        text = event.text()
        popup_visible = self.completer.popup().isVisible()
        current_word = self.text_under_cursor()

        if popup_visible and key == Qt.Key_Escape:
            self.completer.popup().hide()
            return True

        if popup_visible and key in (Qt.Key_Tab, Qt.Key_Backtab, Qt.Key_Return, Qt.Key_Enter):
            completion = self.completer.currentCompletion()
            if completion:
                self.insert_completion(completion)
            return True

        if popup_visible and text in self.ASSAMESE_COMMIT_TEXT:
            if current_word and len(current_word) >= 3 and not is_english_canonical_word(current_word):
                completion = self.completer.currentCompletion()
                if completion:
                    self.insert_completion(completion)
                    super().keyPressEvent(event)
                    return True

        if current_word and should_auto_commit_assamese(current_word):
            if key in (Qt.Key_Tab, Qt.Key_Backtab, Qt.Key_Return, Qt.Key_Enter):
                suggestions = get_assamese_suggestions(current_word)
                if suggestions:
                    self.insert_completion(suggestions[0])
                    return True

            if text in self.ASSAMESE_COMMIT_TEXT:
                suggestions = get_assamese_suggestions(current_word)
                if suggestions:
                    self.insert_completion(suggestions[0])
                    super().keyPressEvent(event)
                    return True

        return False

    def keyPressEvent(self, event):
        if (
            AppConfig.get_language() == "as"
            and event.modifiers() == Qt.ControlModifier
            and event.key() == Qt.Key_Space
        ):
            self._show_assamese_completer(force=True)
            return

        if self._commit_assamese_completion(event):
            return

        super().keyPressEvent(event)

        ctrl_or_shift = event.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier)
        if ctrl_or_shift and not event.text():
            return

        has_modifier = (event.modifiers() != Qt.NoModifier) and not ctrl_or_shift
        completion_prefix = self.text_under_cursor()

        if (
            AppConfig.get_language() == "as"
            and not has_modifier
            and completion_prefix.isascii()
            and completion_prefix.isalpha()
        ):
            self._show_assamese_completer()
        else:
            self.completer.popup().hide()

    def set_error_line(self, lineno: int):
        self.error_lines.clear()
        self.error_lines.add(lineno)
        self.highlight_lines()
        block = self.document().findBlockByNumber(lineno - 1)
        cursor = self.textCursor()
        cursor.setPosition(block.position())
        self.setTextCursor(cursor)
        self.centerCursor()

    def clear_errors(self):
        if self.error_lines:
            self.error_lines.clear()
            self.highlight_lines()

    def get_breakpoints(self) -> list[int]:
        return sorted(list(self.breakpoints))

    def line_number_area_width(self):
        digits = len(str(self.blockCount()))
        return 10 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_line_number_area_width(self):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor("#252526"))
        block = self.firstVisibleBlock()
        block_num = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor("#787878"))
                painter.drawText(
                    0,
                    top,
                    self.lineNumberArea.width() - 4,
                    self.fontMetrics().height(),
                    Qt.AlignRight,
                    str(block_num + 1),
                )
                if (block_num + 1) in self.breakpoints:
                    radius = 5
                    painter.setBrush(QColor("#c74e39"))
                    painter.setPen(Qt.NoPen)
                    painter.drawEllipse(
                        6,
                        top + self.fontMetrics().ascent() - radius,
                        radius * 2,
                        radius * 2,
                    )
            block = block.next()
            block_num += 1
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())

    def highlight_lines(self):
        selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(QColor("#2a2d2e"))
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            selections.append(selection)
        for line in self.error_lines:
            block = self.document().findBlockByNumber(line - 1)
            if block.isValid():
                err_sel = QTextEdit.ExtraSelection()
                err_sel.format.setBackground(QColor(255, 0, 0, 40))
                err_sel.format.setProperty(QTextFormat.FullWidthSelection, True)
                cursor = self.textCursor()
                cursor.setPosition(block.position())
                err_sel.cursor = cursor
                selections.append(err_sel)
        self.setExtraSelections(selections)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.pos().x() < self.line_number_area_width():
            cursor = self.cursorForPosition(event.pos())
            block = cursor.block()
            line = block.blockNumber() + 1
            if line in self.breakpoints:
                self.breakpoints.remove(line)
            else:
                self.breakpoints.add(line)
            self.lineNumberArea.update()
            return
        super().mousePressEvent(event)
