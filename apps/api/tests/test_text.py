from __future__ import annotations

import pytest

from bazaarwatch.core.text import sql_function_definition, turkish_fold


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # The dotted and dotless i, in both directions. This is the pair that
        # Unicode default casing gets wrong for Turkish, and the reason this
        # function exists at all.
        ("İSTANBUL", "istanbul"),
        ("istanbul", "istanbul"),
        ("ISTANBUL", "istanbul"),
        ("ıstanbul", "istanbul"),
        # Every Turkish-specific letter.
        ("ŞEKER", "seker"),
        ("şeker", "seker"),
        ("KARABUĞDAY", "karabugday"),
        ("ÇAY", "cay"),
        ("ÖZ SÜT", "oz sut"),
        ("ÜLKER", "ulker"),
        # Whitespace collapse and trim, because receipt text is ragged.
        ("  CC   KOLA  1LT  PET ", "cc kola 1lt pet"),
        ("", ""),
        ("   ", ""),
        # Non-Turkish scripts pass through, lowercased by Unicode default
        # rules, which are correct once the Turkish pairs are gone.
        ("МОЛОКО", "молоко"),
        ("Käse", "käse"),
    ],
)
def test_fold(raw: str, expected: str) -> None:
    assert turkish_fold(raw) == expected


def test_variants_of_one_word_converge() -> None:
    """The point of the fold: every casing and diacritic variant of a receipt
    string must produce one lexicon key, or resolution silently misses."""
    assert len({turkish_fold(v) for v in ("Işık", "ışık", "IŞIK", "isik", "ISIK")}) == 1


def test_composed_and_decomposed_forms_agree() -> None:
    """A receipt extracted by one provider may carry NFD where another carries
    NFC. Without normalisation those are different keys."""
    assert turkish_fold("Ç") == turkish_fold("C\u0327")
    assert turkish_fold("ü") == turkish_fold("u\u0308")


def test_fold_is_idempotent() -> None:
    for raw in ("İSTANBUL", "  ÜLKER  SÜT ", "ŞEKER"):
        once = turkish_fold(raw)
        assert turkish_fold(once) == once


def test_sql_mirror_exists_and_is_immutable() -> None:
    """An index expression requires IMMUTABLE. If this ever stops being true,
    the lexicon index cannot be built."""
    sql = sql_function_definition()
    assert "CREATE OR REPLACE FUNCTION turkish_fold(input text)" in sql
    assert "IMMUTABLE" in sql
    assert "PARALLEL SAFE" in sql


def test_sql_mirror_translates_before_lowering() -> None:
    """Postgres lower() maps I to i regardless of locale, which is wrong for
    Turkish. translate() must come first, inside lower()."""
    sql = sql_function_definition()
    lower_at = sql.index("lower(")
    translate_at = sql.index("translate(")
    assert lower_at < translate_at, "translate must be nested inside lower"
