from matplotlib.font_manager import FontProperties

from shared.plotting_engine.text_support import (
    apply_script_font_kwargs,
    contains_assamese,
)


def test_contains_assamese_detects_plot_label_text():
    assert contains_assamese("প্ৰসাৰ")
    assert not contains_assamese("Amplitude")


def test_apply_script_font_kwargs_adds_font_for_assamese(monkeypatch):
    prop = FontProperties(family="Nirmala UI")

    monkeypatch.setattr(
        "shared.plotting_engine.text_support.get_assamese_font_properties",
        lambda: prop,
    )

    kw = apply_script_font_kwargs("প্ৰসাৰ", {"color": "white"})

    assert kw["color"] == "white"
    assert kw["fontproperties"] is prop


def test_apply_script_font_kwargs_leaves_english_unchanged():
    kw = apply_script_font_kwargs("Amplitude", {"color": "white"})

    assert kw == {"color": "white"}
