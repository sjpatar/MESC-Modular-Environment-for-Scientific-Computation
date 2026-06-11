from __future__ import annotations

import re

COMMAND_HEAD_ALIASES = {
    "solve": "Solve",
    "nsolve": "NSolve",
    "steps": "Steps",
    "nsteps": "NSteps",
    "diff": "D",
    "d": "D",
    "integrate": "Integrate",
    "limit": "Limit",
    "sum": "Sum",
    "product": "Product",
    "simplify": "Simplify",
    "fullsimplify": "FullSimplify",
    "expand": "Expand",
    "factor": "Factor",
    "apart": "Apart",
    "together": "Together",
    "matrix": "Matrix",
    "identitymatrix": "IdentityMatrix",
    "inverse": "Inverse",
    "det": "Det",
    "eigenvalues": "Eigenvalues",
    "eigenvectors": "Eigenvectors",
    "plot": "Plot",
    "plot3d": "Plot3D",
    "manipulate": "Manipulate",
    
    # Assamese Native Aliases 
    "সমাধান": "Solve",
    "সমাধানকৰক": "Solve",
    "সংখ্যাসমাধান": "NSolve",
    "পদক্ষেপ": "Steps",
    "সংখ্যাপদক্ষেপ": "NSteps",
    "অৱকলন": "D",
    "অৱকলনকৰক": "D",
    "সমাকলন": "Integrate",
    "সমাকলনকৰক": "Integrate",
    "সীমা": "Limit",
    "যোগফল": "Sum",
    "গুণফল": "Product",
    "সৰলীকৰণ": "Simplify",
    "সৰলকৰক": "Simplify",
    "পূৰ্ণসৰলীকৰণ": "FullSimplify",
    "বিস্তাৰ": "Expand",
    "বিস্তাৰকৰক": "Expand",
    "গুণনীয়ক": "Factor",
    "আংশিকভগ্নাংশ": "Apart",
    "একত্ৰ": "Together",
    "মেট্ৰিক্স": "Matrix",
    "কক্ষ": "Matrix",
    "একমেট্ৰিক্স": "IdentityMatrix",
    "উল্টো": "Inverse",
    "নিৰ্ণায়ক": "Det",
    "স্বমমান": "Eigenvalues",
    "স্বভেক্টৰ": "Eigenvectors",
    "আঁকা": "Plot",
    "আকা": "Plot",
    "লেখচিত্ৰ": "Plot",
    "লেখচিত্ৰ3ডি": "Plot3D",
    "লেখচিত্ৰ3D": "Plot3D",
    "লেখচিত্ৰ৩ডি": "Plot3D",
    "চলমান": "Manipulate",
    "সজাওক": "Manipulate",
}

CONSTANT_ALIASES = {
    "pi": "Pi",
    "infinity": "Infinity",
    "inf": "Infinity",
    "পাই": "Pi",
    "অসীম": "Infinity",
    "ই": "E",
    "আই": "I",
}

def _replace_word_aliases(command: str, mapping: dict[str, str], *, require_brackets: bool) -> str:
    result = command
    sorted_items = sorted(mapping.items(), key=lambda item: len(item[0]), reverse=True)

    for source, target in sorted_items:
        escaped = re.escape(source)
        if require_brackets:
            # FIX: Added (?i) for case-insensitive matching
            pattern = rf"(?i)(?<![\w\u0980-\u09FF]){escaped}(?=\s*\[)"
        else:
            pattern = rf"(?i)(?<![\w\u0980-\u09FF]){escaped}(?![\w\u0980-\u09FF])"
        result = re.sub(pattern, target, result)

    return result

def normalize_dual_syntax(command: str) -> str:
    # 1. Translate Assamese Numerals to Latin Numerals
    # This prevents the SymPy parser from choking on numbers like '২x' or '৩'
    assamese_numerals = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
    normalized = command.translate(assamese_numerals)
    
    # 2. Replace Aliases safely
    normalized = _replace_word_aliases(normalized, COMMAND_HEAD_ALIASES, require_brackets=True)
    normalized = _replace_word_aliases(normalized, CONSTANT_ALIASES, require_brackets=False)
    
    return normalized