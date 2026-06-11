# mathex/ui/editor/syntax.py
import re

from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat

from ...language.phonetics import ASSAMESE_BUILTIN_MAP, ASSAMESE_KEYWORD_MAP


WORD_CHARS = r"A-Za-z0-9_\u0980-\u09FF"
CORE_KEYWORDS = [
    "function",
    "end",
    "if",
    "else",
    "elseif",
    "for",
    "while",
    "switch",
    "case",
    "otherwise",
    "try",
    "catch",
    "return",
    "break",
    "continue",
    "global",
    "persistent",
    "classdef",
    "properties",
    "methods",
    "events",
]
CORE_BUILTINS = [
    "disp",
    "clc",
    "plot",
    "pause",
    "size",
    "length",
    "numel",
    "who",
    "whos",
    "help",
    "title",
    "xlabel",
    "ylabel",
    "legend",
    "grid",
    "drawnow",
    "clear",
    "true",
    "false",
    "nan",
    "inf",
    "pi",
    "i",
    "j",
]


class MatlabHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = []
        self._build_rules()

    def _build_rules(self):
        self.rules = []

        keyword_fmt = QTextCharFormat()
        keyword_fmt.setForeground(QColor("#569cd6"))
        keyword_fmt.setFontWeight(QFont.Bold)
        keyword_words = CORE_KEYWORDS + list(ASSAMESE_KEYWORD_MAP.keys())
        self.add_rule(self._word_pattern(keyword_words), keyword_fmt)

        builtin_fmt = QTextCharFormat()
        builtin_fmt.setForeground(QColor("#4ec9b0"))
        builtin_words = CORE_BUILTINS + list(ASSAMESE_BUILTIN_MAP.keys())
        self.add_rule(self._word_pattern(builtin_words), builtin_fmt)

        number_fmt = QTextCharFormat()
        number_fmt.setForeground(QColor("#b5cea8"))
        self.add_rule(r"\b\d+(\.\d*)?([eE][+-]?\d+)?\b", number_fmt)

        op_fmt = QTextCharFormat()
        op_fmt.setForeground(QColor("#d4d4d4"))
        self.add_rule(r"[\+\-\*/\^=<>!&|~]", op_fmt)

        string_fmt = QTextCharFormat()
        string_fmt.setForeground(QColor("#ce9178"))
        self.add_rule(r"'[^']*'", string_fmt)
        self.add_rule(r'"[^"]*"', string_fmt)

        comment_fmt = QTextCharFormat()
        comment_fmt.setForeground(QColor("#6a9955"))
        self.add_rule(r"%.*", comment_fmt)

    def _word_pattern(self, words: list[str]) -> str:
        escaped = sorted({re.escape(word) for word in words if word}, key=len, reverse=True)
        return rf"(?<![{WORD_CHARS}])(?:{'|'.join(escaped)})(?![{WORD_CHARS}])"

    def add_rule(self, pattern, fmt):
        self.rules.append((re.compile(pattern), fmt))

    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            for match in pattern.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, fmt)
