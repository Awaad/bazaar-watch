from __future__ import annotations

from decimal import ROUND_DOWN, Decimal

import pytest

from bazaarwatch.core.money import CurrencyMismatchError, Money, zero


def test_construction_requires_a_known_currency() -> None:
    with pytest.raises(ValueError, match="unknown currency"):
        Money(100, "XXX")


def test_bool_is_not_an_amount() -> None:
    """bool is a subclass of int, so a naive isinstance check lets True through
    as 1."""
    with pytest.raises(TypeError):
        Money(True, "TRY")  # type: ignore[arg-type]


def test_from_major_parses_without_float() -> None:
    assert Money.from_major("45.90", "TRY") == Money(4590, "TRY")
    assert Money.from_major(Decimal("45.90"), "TRY") == Money(4590, "TRY")
    assert Money.from_major(45, "TRY") == Money(4500, "TRY")


def test_from_major_rejects_float() -> None:
    """float('45.90') is already wrong before it arrives."""
    with pytest.raises(TypeError, match="unacceptable money input"):
        Money.from_major(45.90, "TRY")  # type: ignore[arg-type]


def test_from_major_rounds_half_up() -> None:
    assert Money.from_major("0.005", "TRY").amount_minor == 1
    assert Money.from_major("0.004", "TRY").amount_minor == 0


def test_round_trip_through_major_is_lossless() -> None:
    original = Money(4590, "TRY")
    assert Money.from_major(original.to_major(), "TRY") == original


def test_arithmetic_across_currencies_raises() -> None:
    with pytest.raises(CurrencyMismatchError):
        Money(100, "TRY") + Money(100, "EUR")
    with pytest.raises(CurrencyMismatchError):
        _ = Money(100, "TRY") < Money(100, "EUR")


def test_addition_and_subtraction_stay_exact() -> None:
    total = sum((Money.from_major("0.10", "TRY") for _ in range(10)), zero("TRY"))
    assert total == Money.from_major("1.00", "TRY")


def test_multiplication_is_integer_only() -> None:
    assert Money(4590, "TRY") * 3 == Money(13770, "TRY")
    with pytest.raises(TypeError, match="use scale"):
        Money(4590, "TRY") * Decimal("1.5")  # type: ignore[operator]
    with pytest.raises(TypeError):
        Money(4590, "TRY") * True  # type: ignore[operator]


def test_scale_requires_decimal_and_states_its_rounding() -> None:
    price = Money(4590, "TRY")
    assert price.scale(Decimal("0.5")) == Money(2295, "TRY")
    assert price.scale(Decimal("0.333")) == Money(1528, "TRY")
    assert price.scale(Decimal("0.333"), rounding=ROUND_DOWN) == Money(1528, "TRY")
    with pytest.raises(TypeError, match="must be Decimal"):
        price.scale(0.5)  # type: ignore[arg-type]


def test_money_is_immutable() -> None:
    price = Money(4590, "TRY")
    with pytest.raises(AttributeError):
        price.amount_minor = 1  # type: ignore[misc]


def test_ordering_within_one_currency() -> None:
    assert Money(100, "TRY") < Money(200, "TRY")
    assert Money(200, "TRY") >= Money(200, "TRY")
    assert -Money(100, "TRY") == Money(-100, "TRY")
