"""Identifier generation.

UUIDv7 per RFC 9562: a 48-bit big-endian Unix timestamp in milliseconds, then
the version and variant bits, then randomness.

Time ordering matters because `price_observations` and `receipt_lines` are
append-only and the most insert-heavy tables in the system. Random v4 keys would
scatter inserts across the B-tree. Ordering also makes keyset pagination on
`(created_at, id)` both correct and index-friendly.

Clients never call this. A client generates an opaque v4 idempotency key, never
a primary key: a device with a skewed clock would mint a v7 whose embedded
timestamp destroys the ordering that justified choosing v7. See ADR-0003.

Python 3.13 has no `uuid.uuid7`, so this implements it. The monotonic counter is
not decoration: without it, identifiers minted in the same millisecond have no
defined order and "time-ordered" would hold only at millisecond granularity.
"""

from __future__ import annotations

import secrets
import threading
import time
from collections.abc import Callable
from uuid import UUID

UUID_VERSION = 7

_UNIX_TS_MS_BITS = 48
_RAND_A_BITS = 12
_RAND_B_BITS = 62
_MAX_RAND_A = (1 << _RAND_A_BITS) - 1


def _now_ms() -> int:
    return time.time_ns() // 1_000_000


class Uuid7Generator:
    """Monotonic UUIDv7 source.

    Encapsulated rather than module-level, so tests can drive an isolated
    instance with a controlled clock instead of mutating process state.
    """

    __slots__ = ("_counter", "_last_ms", "_lock", "_now_ms")

    def __init__(self, *, clock: Callable[[], int] | None = None) -> None:
        self._now_ms = clock or _now_ms
        self._lock = threading.Lock()
        self._last_ms = -1
        self._counter = 0

    def __call__(self) -> UUID:
        with self._lock:
            timestamp_ms = self._now_ms()

            if timestamp_ms > self._last_ms:
                self._last_ms = timestamp_ms
                # Seed below the ceiling so a burst inside one millisecond has
                # room to count upward without rolling over.
                self._counter = secrets.randbits(_RAND_A_BITS) >> 1
            else:
                # Same millisecond, or a clock that moved backwards. Keep
                # counting rather than emit an identifier that sorts before its
                # predecessor.
                self._counter += 1
                if self._counter > _MAX_RAND_A:
                    # Counter exhausted inside one millisecond. Borrow from the
                    # next millisecond rather than wrap, which would break
                    # ordering.
                    self._last_ms += 1
                    self._counter = 0
                timestamp_ms = self._last_ms

            rand_a = self._counter

        rand_b = secrets.randbits(_RAND_B_BITS)

        value = timestamp_ms << (128 - _UNIX_TS_MS_BITS)
        value |= UUID_VERSION << 76
        value |= rand_a << 64
        value |= 0b10 << 62  # RFC 9562 variant
        value |= rand_b
        return UUID(int=value)


_default = Uuid7Generator()


def new_id() -> UUID:
    """A time-ordered UUIDv7, monotonic within the process."""
    return _default()


def timestamp_ms(value: UUID) -> int:
    """The embedded millisecond timestamp.

    For tests and diagnostics. Not a substitute for `created_at`: this is when
    the identifier was minted, not when the row was committed.
    """
    if value.version != UUID_VERSION:
        raise ValueError(f"not a UUIDv{UUID_VERSION}: version {value.version}")
    return value.int >> (128 - _UNIX_TS_MS_BITS)
