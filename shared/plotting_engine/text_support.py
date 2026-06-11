from __future__ import annotations

from functools import lru_cache

from matplotlib.font_manager import FontProperties, findfont


ASSAMESE_FONT_CANDIDATES = (
    "Nirmala UI",
    "Noto Sans Bengali",
    "Noto Serif Bengali",
    "Vrinda",
    "Kalpurush",
    "Lohit Assamese",
)


def contains_assamese(text) -> bool:
    value = str(text)
    return any("\u0980" <= ch <= "\u09FF" for ch in value)


@lru_cache(maxsize=1)
def _resolve_assamese_font_path() -> str | None:
    for family in ASSAMESE_FONT_CANDIDATES:
        try:
            path = findfont(FontProperties(family=family), fallback_to_default=False)
        except Exception:
            continue

        if path:
            return path

    return None


def get_assamese_font_properties() -> FontProperties | None:
    path = _resolve_assamese_font_path()
    if not path:
        return None
    return FontProperties(fname=path)


def apply_script_font_kwargs(text, kwargs: dict | None = None) -> dict:
    kw = dict(kwargs or {})

    if not contains_assamese(text):
        return kw

    if "fontproperties" in kw or "fontfamily" in kw:
        return kw

    font_props = get_assamese_font_properties()
    if font_props is not None:
        kw["fontproperties"] = font_props

    return kw


def apply_script_font_to_artist(artist, text=None) -> None:
    if artist is None:
        return

    value = text
    if value is None and hasattr(artist, "get_text"):
        try:
            value = artist.get_text()
        except Exception:
            value = None

    if value is None or not contains_assamese(value):
        return

    font_props = get_assamese_font_properties()
    if font_props is None:
        return

    if hasattr(artist, "set_fontproperties"):
        try:
            artist.set_fontproperties(font_props)
        except Exception:
            pass
