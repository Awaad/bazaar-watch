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

# Matches the `slug` columns. Kept here rather than at each model, so a slug
# cannot be generated longer than the column that stores it.
SLUG_MAX_LENGTH = 64

_NON_SLUG = re.compile(r"[^a-z0-9]+")


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


def slugify(*parts: str, max_length: int = SLUG_MAX_LENGTH) -> str:
    """Build a public identifier from one or more text parts.

    Slugs go in URLs, so they are ASCII and typeable on any keyboard. They are
    folded through `turkish_fold` rather than through a second implementation,
    because two folds drift and this one is already the thing lexicon keys
    depend on. See docs/15-repo-structure-standards.md section 8.

    Parts are joined in order, which is how a globally unique branch slug
    carries its chain: `slugify("Lemar", "Girne Merkez")` is
    `lemar-girne-merkez`.

    Beyond the fold, this strips the diacritics the fold leaves alone. The fold
    handles the twelve letters Turkish casing gets wrong and nothing else, and
    open map data contains names from several scripts.

    Uniqueness is not this function's problem. It is deterministic and will
    happily return the same slug twice; the caller resolves collisions.

    Raises:
        ValueError: if nothing survives, which happens when every part is in a
            script with no ASCII form. An empty slug on a `UNIQUE NOT NULL`
            column is a defect, so it fails here rather than at insert.
    """
    if max_length < 1:
        raise ValueError(f"max_length must be positive, got {max_length}")

    folded = turkish_fold(" ".join(parts))
    # Decompose, then drop the combining marks. `é` becomes `e`; `λ` has no
    # ASCII form and is removed by the substitution below.
    decomposed = unicodedata.normalize("NFKD", folded)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))

    slug = _NON_SLUG.sub("-", stripped).strip("-")
    if not slug:
        raise ValueError(f"{parts!r} contains no characters usable in a slug")

    if len(slug) > max_length:
        cut = slug[:max_length]
        # Prefer a word boundary, so a truncated slug still reads. Falls back
        # to the hard cut when the first word alone is longer than the budget.
        boundary = cut.rfind("-")
        slug = (cut[:boundary] if boundary > 0 else cut).rstrip("-")

    return slug


def sql_function_definition() -> str:
    """The mirrored SQL, for the migration that installs it."""
    return SQL_FUNCTION_PATH.read_text(encoding="utf-8")
