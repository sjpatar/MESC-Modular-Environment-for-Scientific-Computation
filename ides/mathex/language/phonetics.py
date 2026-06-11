try:
    from indic_transliteration import sanscript
except Exception:
    sanscript = None


ASSAMESE_KEYWORD_MAP = {
    "যদি": "if",
    "নহলেযদি": "elseif",
    "অন্যথা": "else",
    "সমাপ্ত": "end",
    "বাবে": "for",
    "যেতিয়ালৈকে": "while",
    "বিৰতি": "break",
    "অব্যাহত": "continue",
    "ফলন": "function",
    "উভতাওক": "return",
    "স্বিচ": "switch",
    "কেছ": "case",
    "নহলে": "otherwise",
    "চেষ্টা": "try",
    "ধৰা": "catch",
    "গ্লোবেল": "global",
    "শ্ৰেণী": "classdef",
    "গুণ": "properties",
    "পদ্ধতি": "methods",
    "ঘটনা": "events",
}


ASSAMESE_BUILTIN_MAP = {
    "দেখুওৱা": "disp",
    "মচিদিয়া": "clc",
    "আকা": "plot",
    "ৰৈযোৱা": "pause",
    "আকাৰ": "size",
    "দৈৰ্ঘ্য": "length",
    "শিৰোনামা": "title",
    "xলেবেল": "xlabel",
    "yলেবেল": "ylabel",
    "সংকেত": "legend",
    "গ্ৰিড": "grid",
    "সহায়": "help",
}


PHONETIC_FAST_PATH = {
    "jodi": "যদি",
    "zodi": "যদি",
    "noholejodi": "নহলেযদি",
    "noholezodi": "নহলেযদি",
    "onnotha": "অন্যথা",
    "anyatha": "অন্যথা",
    "somapto": "সমাপ্ত",
    "samapto": "সমাপ্ত",
    "babe": "বাবে",
    "zetialoike": "যেতিয়ালৈকে",
    "jetialoike": "যেতিয়ালৈকে",
    "biroti": "বিৰতি",
    "obbahot": "অব্যাহত",
    "avyahat": "অব্যাহত",
    "folon": "ফলন",
    "pholon": "ফলন",
    "ubhotaok": "উভতাওক",
    "ubhataok": "উভতাওক",
    "swich": "স্বিচ",
    "switch": "স্বিচ",
    "kes": "কেছ",
    "case": "কেছ",
    "nohole": "নহলে",
    "notuba": "নহলে",
    "sesta": "চেষ্টা",
    "sestha": "চেষ্টা",
    "try": "চেষ্টা",
    "dhora": "ধৰা",
    "catch": "ধৰা",
    "global": "গ্লোবেল",
    "sreni": "শ্ৰেণী",
    "gun": "গুণ",
    "poddhoti": "পদ্ধতি",
    "ghotona": "ঘটনা",
    "dekhua": "দেখুওৱা",
    "dekhuowa": "দেখুওৱা",
    "mosidia": "মচিদিয়া",
    "mocidia": "মচিদিয়া",
    "aka": "আকা",
    "roijua": "ৰৈযোৱা",
    "roizua": "ৰৈযোৱা",
    "akar": "আকাৰ",
    "doirgho": "দৈৰ্ঘ্য",
    "sironama": "শিৰোনামা",
    "xironama": "শিৰোনামা",
    "xlabel": "xলেবেল",
    "ylabel": "yলেবেল",
    "songket": "সংকেত",
    "grid": "গ্ৰিড",
    "sohai": "সহায়",
    "sahay": "সহায়",
    "help": "সহায়",
}


ENGLISH_CANONICAL_WORDS = (
    set(ASSAMESE_KEYWORD_MAP.values()) | set(ASSAMESE_BUILTIN_MAP.values())
)


def is_english_canonical_word(text: str) -> bool:
    return bool(text) and text.lower() in ENGLISH_CANONICAL_WORDS


def has_assamese_phonetic_prefix(roman_text: str) -> bool:
    if not roman_text or not roman_text.isascii() or not roman_text.isalpha():
        return False

    roman_lower = roman_text.lower()
    return any(key.startswith(roman_lower) for key in PHONETIC_FAST_PATH)


def should_auto_commit_assamese(roman_text: str) -> bool:
    if not roman_text or not roman_text.isascii() or not roman_text.isalpha():
        return False

    roman_lower = roman_text.lower()
    return (
        roman_lower in PHONETIC_FAST_PATH
        and roman_lower not in ENGLISH_CANONICAL_WORDS
    )


def transliterate_assamese_word(roman_text: str) -> str | None:
    if not roman_text or not roman_text.isascii() or not roman_text.isalpha():
        return None
    if sanscript is None:
        return None

    roman_lower = roman_text.lower()

    try:
        proxy_roman = roman_lower.replace("w", ".D").replace("v", ".D")
        proxy_roman = proxy_roman.replace("y", "Y")
        proxy_roman = proxy_roman.replace("z", "j")
        proxy_roman = proxy_roman.replace("x", "S")
        proxy_roman = proxy_roman.replace("f", "ph")

        bengali_script = sanscript.transliterate(
            proxy_roman,
            sanscript.ITRANS,
            sanscript.BENGALI,
        )

        assamese_script = bengali_script.replace("ড়", "ৱ")
        assamese_script = assamese_script.replace("র", "ৰ")
        return assamese_script if assamese_script and assamese_script != roman_text else None
    except Exception as exc:
        print(f"Transliteration Error for '{roman_text}': {exc}")
        return None


def get_assamese_suggestions(roman_text: str) -> list[str]:
    if not roman_text or not roman_text.isascii() or not roman_text.isalpha():
        return []

    roman_lower = roman_text.lower()
    suggestions = []

    prefix_matches = sorted(
        (
            (key, value)
            for key, value in PHONETIC_FAST_PATH.items()
            if key.startswith(roman_lower)
        ),
        key=lambda item: (item[0] != roman_lower, len(item[0]), item[0]),
    )

    for _, suggestion in prefix_matches:
        if suggestion not in suggestions:
            suggestions.append(suggestion)

    transliterated = transliterate_assamese_word(roman_text)
    if transliterated and transliterated not in suggestions:
        suggestions.append(transliterated)

    return suggestions
