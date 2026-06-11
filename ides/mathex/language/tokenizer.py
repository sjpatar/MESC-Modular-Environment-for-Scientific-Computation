# mathex/language/tokenizer.py

from dataclasses import dataclass
from typing import List
from shared.config import AppConfig

# [FIX]: Only import the Keyword Map. Phonetics are now handled by the UI.
from .phonetics import ASSAMESE_KEYWORD_MAP 
from .locale import tr


@dataclass
class Token:
    type: str
    value: str
    line: int = 0


# MATLAB keywords (lowercase compare)
KEYWORDS = {
    'if', 'elseif', 'else', 'end', 'for', 'while', 'break', 'continue',
    'global', 'switch', 'case', 'otherwise', 'try', 'catch',
    'function', 'return',
    'classdef', 'properties', 'methods', 'events'
}


class Tokenizer:
    """
    MATLAB-style lexical scanner with Assamese normalization.
    """
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1

    def tokenize(self) -> List[Token]:
        tokens: List[Token] = []
        space_skipped = True 

        while self.pos < len(self.text):
            ch = self.text[self.pos]

            # whitespace / newline
            if ch.isspace():
                if ch == '\n':
                    tokens.append(Token('NEWLINE', '\n', self.line))
                    self.line += 1
                self.pos += 1
                space_skipped = True
                continue

            # comment %
            if ch == '%':
                self._skip_comment()
                space_skipped = True
                continue

            # continuation ...
            if ch == '.' and self._peek(1) == '.' and self._peek(2) == '.':
                self._skip_line_continuation()
                space_skipped = True
                continue
            
            # Signed Numbers
            if ch in ('+', '-') and space_skipped:
                nxt = self._peek(1)
                is_digit = nxt.isdigit()
                is_float = (nxt == '.' and self._peek(2).isdigit())
                
                if is_digit or is_float:
                    tokens.append(self._read_number())
                    space_skipped = False
                    continue

            # Identifiers & keywords (Supports Unicode & Assamese Matras natively)
            if ch.isalpha() or ch == '_' or ('\u0980' <= ch <= '\u09FF'):
                tok = self._read_identifier()

                # [ROBUST FIX]: Always map Assamese keywords regardless of UI state!
                if tok.value in ASSAMESE_KEYWORD_MAP:
                    tok.type = 'KEYWORD'
                    tok.value = ASSAMESE_KEYWORD_MAP[tok.value]
                elif tok.value.lower() in KEYWORDS:
                    tok.type = 'KEYWORD'
                    
                tokens.append(tok)
                space_skipped = False
                continue

            # numbers, decimals, sci, 3i
            if ch.isdigit() or (ch == '.' and self._peek().isdigit()):
                tokens.append(self._read_number())
                space_skipped = False
                continue

            # Transpose vs String (Supports Single and Double Quotes)
            if ch in ("'", '"'):
                is_transpose = False
                # Transpose is only valid for single quotes!
                if ch == "'" and tokens and not space_skipped:
                    prev = tokens[-1]
                    if prev.type in ('ID', 'NUMBER') or prev.value in (')', ']', '}', "'"):
                        is_transpose = True
                
                if is_transpose:
                    tokens.append(Token('OP', "'", self.line))
                    self.pos += 1
                else:
                    tokens.append(self._read_string(quote_char=ch))
                space_skipped = False
                continue

            # anonymous function @
            if ch == '@':
                tokens.append(Token('AT', '@', self.line))
                self.pos += 1
                space_skipped = False
                continue

            # cell { } handled literally
            if ch in "{}":
                tokens.append(Token(ch, ch, self.line))
                self.pos += 1
                space_skipped = False
                continue

            # operators / punctuation / symbols
            if ch in "+-*/^=<>:;(),[]\\.~&|":
                tokens.append(self._read_operator())
                space_skipped = False
                continue

            # [LOCALE FIX] Output localized syntax errors
            raise SyntaxError(tr("err_syntax", ch=ch, line=self.line))

        tokens.append(Token('EOF', '', self.line))
        return tokens

    # ---------------------------------------------------
    # Helpers
    # ---------------------------------------------------
    def _peek(self, offset: int = 1) -> str:
        p = self.pos + offset
        return self.text[p] if p < len(self.text) else ''

    def _skip_comment(self):
        while self.pos < len(self.text) and self.text[self.pos] != '\n':
            self.pos += 1

    def _skip_line_continuation(self):
        self.pos += 3
        while self.pos < len(self.text) and self.text[self.pos] != '\n':
            self.pos += 1

    def _read_identifier(self) -> Token:
        start = self.pos
        while self.pos < len(self.text):
            c = self.text[self.pos]
            if c.isalnum() or c == '_' or ('\u0980' <= c <= '\u09FF'):
                self.pos += 1
            else:
                break
        return Token('ID', self.text[start:self.pos], self.line)

    def _read_number(self) -> Token:
        start = self.pos
        if self.text[self.pos] in ('+', '-'):
            self.pos += 1

        while self.pos < len(self.text) and self.text[self.pos].isdigit():
            self.pos += 1

        if self.pos < len(self.text) and self.text[self.pos] == '.':
            if not (self._peek(1) == '.' and self._peek(2) == '.'):
                self.pos += 1
                while self.pos < len(self.text) and self.text[self.pos].isdigit():
                    self.pos += 1

        if self.pos < len(self.text) and self.text[self.pos] in ('e', 'E'):
            p = self.pos + 1
            if p < len(self.text) and self.text[p] in ('+', '-'):
                p += 1
            if p < len(self.text) and self.text[p].isdigit():
                self.pos = p
                while self.pos < len(self.text) and self.text[self.pos].isdigit():
                    self.pos += 1

        if self.pos < len(self.text) and self.text[self.pos] in ('i', 'j'):
            nxt = self._peek(1)
            if not nxt.isalnum() and nxt != '_':
                num = self.text[start:self.pos] + 'j'
                self.pos += 1
                return Token('NUMBER', num, self.line)

        return Token('NUMBER', self.text[start:self.pos], self.line)

    def _read_string(self, quote_char="'") -> Token:
        self.pos += 1
        start = self.pos
        while self.pos < len(self.text) and self.text[self.pos] != quote_char:
            self.pos += 1
        val = self.text[start:self.pos]
        if self.pos < len(self.text):
            self.pos += 1
        return Token('STRING', val, self.line)

    def _read_operator(self) -> Token:
        ch = self.text[self.pos]
        nxt = self._peek()

        if ch == '.' and nxt in ('*', '/', '\\', '^', "'"): 
            op = ch + nxt
            self.pos += 2
            return Token('OP', op, self.line)

        if ch in ('=', '~', '<', '>') and nxt == '=':
            op = ch + nxt
            self.pos += 2
            return Token('OP', op, self.line)

        if ch in ('&', '|') and nxt == ch:
            op = ch + nxt
            self.pos += 2
            return Token('OP', op, self.line)

        self.pos += 1
        if ch in "()[]{}.,;":
            return Token(ch, ch, self.line)

        return Token('OP', ch, self.line)