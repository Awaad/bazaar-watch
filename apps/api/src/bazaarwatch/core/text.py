"""Turkish text handling.

The single most dangerous class of silent bug in this system.

Turkish casing is locale-dependent: `i` uppercases to `İ` and `I` lowercases to
`ı`. Unicode default casing maps `I` to `i`, which is wrong for Turkish. A
lexicon key built with the wrong casing silently fails to match, and nothing
raises.

The fold has exactly two consumers: lexicon keys and trigram matching. It is
deliberately lossy. It is **never** applied to embedding input, because
stripping diacritics degrades a model trained on natural text; that is why
`product_search_docs` carries `lexical_text` and `semantic_text` as separate
columns.

A mirrored SQL function lives beside this file in `sql/turkish_fold.sql`, so
index expressions and application code compute the same value. Their parity is
asserted by test. See ADR-0025.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

# Explicit mappings for the letters Unicode default casing gets wrong for
# Turkish, plus the diacritics the fold removes. Order does not matter: this is
# a character-for-character translation, applied before any case operation.
_FOLD_MAP: dict[str, str] = {
    "İ": "I",
    "I": "I",
    "ı": "i",
    "Ş": "S",
    "ş": "s",
    "Ğ": "G",
    "ğ": "g",
    "Ç": "C",
    "ç": "c",
    "Ö": "O",
    "ö": "o",
    "Ü": "U",
    "ü": "u",
}

_TRANSLATION = str.maketrans(_FOLD_MAP)
_WHITESPACE = re.compile(r"\s+")

SQL_FUNCTION_PATH = Path(__file__).parent / "sql" / "turkish_fold.sql"


def turkish_fold(value: str) -> str:
    """Fold text for exact-match lexicon keys and trigram search.

    Steps, in the same order as the SQL mirror:

    1. Normalise to NFC, so composed and decomposed forms of one letter fold
       identically.
    2. Translate the Turkish-specific letters to ASCII explicitly.
    3. Lowercase. Safe now, because the pairs Unicode gets wrong for Turkish
       have already been removed.
    4. Collapse internal whitespace runs and trim.
    """
    normalised = unicodedata.normalize("NFC", value)
    translated = normalised.translate(_TRANSLATION)
    # Turkish-specific pairs are gone by this point, so Unicode default casing
    # is correct for whatever remains. gate-ignore: naive-casing
    lowered = translated.lower()  # gate-ignore: naive-casing
    return _WHITESPACE.sub(" ", lowered).strip()


def sql_function_definition() -> str:
    """The mirrored SQL, for the migration that installs it."""
    return SQL_FUNCTION_PATH.read_text(encoding="utf-8")
