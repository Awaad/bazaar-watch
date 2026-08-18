"""Money.

Integer minor units with an explicit currency. Never float, and never a bare
number crossing a boundary.

Float accumulates error and produces comparisons that are wrong without ever
raising, which is the worst failure shape available in a price database. See
ADR-0004.

Currency is carried, not assumed. Observations record the currency they were
observed in and are never converted on write; conversion happens at read time
against a recorded rate, so a corrected rate changes derived views without
touching facts.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Self

# ISO 4217 exponents for the currencies this system handles. Not every currency
# has two minor digits, and assuming so is a classic source of silent error.
_MINOR_UNIT_EXPONENT: dict[str, int] = {
    "TRY": 2,
    "GBP": 2,
    "EUR": 2,
    "USD": 2,
}


class CurrencyMismatchError(ValueError):
    """Arithmetic across currencies. Always a bug: conversion is explicit and
    happens at read time against a recorded rate."""


def minor_unit_exponent(currency: str) -> int:
    try:
        return _MINOR_UNIT_EXPONENT[currency]
    except KeyError:
        raise ValueError(f"unknown currency: {currency}") from None


@dataclass(frozen=True, slots=True, order=False)
class Money:
    amount_minor: int
    currency: str

    def __post_init__(self) -> None:
        if not isinstance(self.amount_minor, int) or isinstance(self.amount_minor, bool):
            raise TypeError("amount_minor must be an int")
        minor_unit_exponent(self.currency)  # validates

    @classmethod
    def from_major(cls, amount: Decimal | str | int, currency: str) -> Self:
        """Parse a major-unit amount. Accepts Decimal, str or int, never float:
        `float("45.90")` is already wrong before it arrives.
        """
        # Positive check rather than a float guard: untyped callers exist
        # (JSON bodies, database rows), and `float("45.90")` is already wrong
        # before it arrives here.
        if isinstance(amount, bool) or not isinstance(amount, Decimal | str | int):
            raise TypeError(f"unacceptable money input: {type(amount).__name__}")
        exponent = minor_unit_exponent(currency)
        scaled = Decimal(amount).scaleb(exponent)
        quantized = scaled.quantize(Decimal(1), rounding=ROUND_HALF_UP)
        return cls(amount_minor=int(quantized), currency=currency)

    def to_major(self) -> Decimal:
        """For display and export only. Never for arithmetic."""
        return Decimal(self.amount_minor).scaleb(-minor_unit_exponent(self.currency))

    def _check(self, other: Money) -> None:
        if self.currency != other.currency:
            raise CurrencyMismatchError(f"cannot combine {self.currency} and {other.currency}")

    def __add__(self, other: Money) -> Money:
        self._check(other)
        return Money(self.amount_minor + other.amount_minor, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._check(other)
        return Money(self.amount_minor - other.amount_minor, self.currency)

    def __neg__(self) -> Money:
        return Money(-self.amount_minor, self.currency)

    def __mul__(self, factor: int) -> Money:
        """Integer multiplication only. Scaling by a ratio is `scale`, which
        makes the rounding decision visible at the call site."""
        if not isinstance(factor, int) or isinstance(factor, bool):
            raise TypeError("multiply by an int; use scale() for a ratio")
        return Money(self.amount_minor * factor, self.currency)

    def scale(self, factor: Decimal, *, rounding: str = ROUND_HALF_UP) -> Money:
        """Scale by a ratio, rounding to whole minor units.

        Rounding is explicit because it is a decision, not an implementation
        detail: unit prices, promotional discounts and FX conversion each want
        it stated rather than inherited.
        """
        if not isinstance(factor, Decimal):
            raise TypeError(f"scale factor must be Decimal, got {type(factor).__name__}")
        scaled = (Decimal(self.amount_minor) * Decimal(factor)).quantize(
            Decimal(1), rounding=rounding
        )
        return Money(int(scaled), self.currency)

    def __lt__(self, other: Money) -> bool:
        self._check(other)
        return self.amount_minor < other.amount_minor

    def __le__(self, other: Money) -> bool:
        self._check(other)
        return self.amount_minor <= other.amount_minor

    def __gt__(self, other: Money) -> bool:
        self._check(other)
        return self.amount_minor > other.amount_minor

    def __ge__(self, other: Money) -> bool:
        self._check(other)
        return self.amount_minor >= other.amount_minor

    def __str__(self) -> str:
        return f"{self.to_major()} {self.currency}"


def zero(currency: str) -> Money:
    return Money(0, currency)
