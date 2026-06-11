import numpy as np
import pytest

from ides.mathex.kernel.session import KernelSession
from ides.mathex.language.locale import tr
from ides.mathex.language.phonetics import (
    get_assamese_suggestions,
    has_assamese_phonetic_prefix,
    should_auto_commit_assamese,
)
from ides.mathex.language.tokenizer import Tokenizer
from shared.config import AppConfig


@pytest.fixture
def session():
    previous_lang = AppConfig.get_language()
    kernel = KernelSession()
    AppConfig.set_language("as")
    yield kernel
    AppConfig.set_language(previous_lang)


def test_assamese_math_execution(session):
    code_as = """
    x = zeros(2, 2)
    y = ones(2, 2)
    z = x + y
    """
    session.execute(code_as)

    assert "x" in session.globals
    assert "z" in session.globals
    np.testing.assert_array_equal(session.globals["z"]._data, np.ones((2, 2)))


def test_assamese_auto_call_transpilation(session, capsys):
    code = """
    দেখুওৱা('Hello')
    মচিদিয়া
    """
    session.execute(code)

    captured = capsys.readouterr()
    assert "Hello" in captured.out
    assert "\f" in captured.out


def test_assamese_runtime_error_translation(session, capsys):
    session.execute("err_val = 1 / 0")
    captured = capsys.readouterr()
    assert "শূন্যৰে হৰণ" in captured.out


def test_assamese_keyword_normalization():
    previous_lang = AppConfig.get_language()
    AppConfig.set_language("as")
    try:
        tokens = Tokenizer(
            """
            যদি x
                চেষ্টা
                    স্বিচ x
                        কেছ 1
                            y = 1
                        নহলে
                            y = 0
                    সমাপ্ত
                ধৰা err
                    y = -1
                সমাপ্ত
            সমাপ্ত
            """
        ).tokenize()

        keyword_values = [token.value for token in tokens if token.type == "KEYWORD"]
        assert "if" in keyword_values
        assert "try" in keyword_values
        assert "switch" in keyword_values
        assert "case" in keyword_values
        assert "otherwise" in keyword_values
        assert "catch" in keyword_values
    finally:
        AppConfig.set_language(previous_lang)


def test_assamese_class_keyword_normalization():
    previous_lang = AppConfig.get_language()
    AppConfig.set_language("as")
    try:
        tokens = Tokenizer(
            """
            শ্ৰেণী Point
                গুণ
                    X
                সমাপ্ত
                পদ্ধতি
                সমাপ্ত
            সমাপ্ত
            """
        ).tokenize()

        keyword_values = [token.value for token in tokens if token.type == "KEYWORD"]
        assert "classdef" in keyword_values
        assert "properties" in keyword_values
        assert "methods" in keyword_values
    finally:
        AppConfig.set_language(previous_lang)


def test_assamese_localized_error_prefixes():
    previous_lang = AppConfig.get_language()
    AppConfig.set_language("as")
    try:
        assert tr("err_prefix") == "ত্ৰুটি"
        assert tr("err_line_label") == "শাৰী"
    finally:
        AppConfig.set_language(previous_lang)


def test_assamese_phonetic_prefix_suggestions():
    suggestions = get_assamese_suggestions("jod")
    assert suggestions
    assert suggestions[0] == "যদি"
    assert has_assamese_phonetic_prefix("jod")


def test_assamese_phonetic_auto_commit_preserves_english_keywords():
    assert should_auto_commit_assamese("jodi")
    assert should_auto_commit_assamese("dekhua")
    assert not should_auto_commit_assamese("switch")
    assert not should_auto_commit_assamese("help")
