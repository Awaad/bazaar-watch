from __future__ import annotations

import pytest

from bazaarwatch.core.text import SLUG_MAX_LENGTH, slugify, turkish_fold


def test_parts_join_in_order() -> None:
    """A branch slug is globally unique, so it carries its chain."""
    assert slugify("Lemar", "Girne Merkez") == "lemar-girne-merkez"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Şok Market", "sok-market"),
        ("Güneş Gıda", "gunes-gida"),
        ("Iğdır", "igdir"),
        ("İstanbul Marketi", "istanbul-marketi"),
        ("Çağrı", "cagri"),
        ("Öz Ürünler", "oz-urunler"),
    ],
)
def test_turkish_letters_fold_the_same_way_the_lexicon_folds_them(
    value: str, expected: str
) -> None:
    """One fold, not two. A second implementation is the drift ADR-0025
    exists to prevent."""
    assert slugify(value) == expected


def test_dotless_i_does_not_become_a_dotted_i() -> None:
    """`Iğdır` under Unicode default casing gives `iğdır`, and a slug built
    from it would carry the wrong letter. The fold handles it before any case
    operation runs."""
    assert slugify("IĞDIR") == "igdir"
    assert slugify("IĞDIR") == slugify("ığdır")


def test_diacritics_the_fold_leaves_alone_are_still_stripped() -> None:
    """The fold covers the twelve letters Turkish casing gets wrong. Open map
    data carries names from several scripts, and a slug must be ASCII."""
    assert turkish_fold("Café") == "café"
    assert slugify("Café Central") == "cafe-central"


def test_punctuation_and_runs_collapse_to_single_hyphens() -> None:
    assert slugify("  A&B   Market -- Ltd. Şti.  ") == "a-b-market-ltd-sti"


def test_no_leading_or_trailing_hyphen() -> None:
    assert slugify("!!! Market !!!") == "market"


def test_digits_survive() -> None:
    assert slugify("Market 24/7") == "market-24-7"


def test_text_with_no_ascii_form_raises_rather_than_returning_empty() -> None:
    """An empty slug on a UNIQUE NOT NULL column is a defect. Failing here is
    better than failing at insert, where the cause is much less obvious."""
    with pytest.raises(ValueError, match="no characters usable in a slug"):
        slugify("Λευκωσία")


def test_truncation_prefers_a_word_boundary() -> None:
    assert slugify("lemar", "girne merkez subesi", max_length=18) == "lemar-girne"


def test_truncation_falls_back_to_a_hard_cut_when_the_first_word_is_too_long() -> None:
    assert slugify("supermarketcilik", max_length=6) == "superm"


def test_truncation_never_leaves_a_trailing_hyphen() -> None:
    assert not slugify("ab cdefgh", max_length=3).endswith("-")


def test_default_budget_matches_the_slug_column() -> None:
    """Generating something longer than the column that stores it would fail at
    insert, one layer away from the cause."""
    assert len(slugify("x" * 200)) == SLUG_MAX_LENGTH


def test_zero_length_budget_is_rejected() -> None:
    with pytest.raises(ValueError, match="max_length must be positive"):
        slugify("market", max_length=0)


def test_output_is_deterministic_and_not_deduplicated() -> None:
    """Uniqueness is the caller's problem. This function will happily return
    the same slug twice, and the service resolves the collision."""
    assert slugify("Lemar", "Girne") == slugify("lemar", "girne")
