from __future__ import annotations

import itertools
import threading
import time
from uuid import UUID

import pytest

from bazaarwatch.core.ids import UUID_VERSION, Uuid7Generator, new_id, timestamp_ms


def test_version_and_variant_bits() -> None:
    value = new_id()
    assert value.version == UUID_VERSION
    # RFC 9562 variant is the two high bits of the clock_seq_hi octet.
    assert (value.int >> 62) & 0b11 == 0b10


def test_embedded_timestamp_is_current() -> None:
    before = time.time_ns() // 1_000_000
    value = new_id()
    after = time.time_ns() // 1_000_000
    assert before <= timestamp_ms(value) <= after


def test_timestamp_rejects_other_versions() -> None:
    with pytest.raises(ValueError, match="not a UUIDv7"):
        timestamp_ms(UUID("00000000-0000-4000-8000-000000000000"))


def test_ids_are_monotonic_within_one_millisecond() -> None:
    """Without the counter, identifiers minted in the same millisecond have no
    defined order and the ordering guarantee holds only at millisecond
    granularity."""
    generator = Uuid7Generator(clock=lambda: 1_700_000_000_000)
    values = [generator() for _ in range(1000)]
    assert values == sorted(values, key=lambda u: u.int)
    assert len(set(values)) == len(values)


def test_counter_exhaustion_borrows_the_next_millisecond() -> None:
    """4096 identifiers in one millisecond exhausts rand_a. Ordering must
    survive rather than wrap."""
    generator = Uuid7Generator(clock=lambda: 1_700_000_000_000)
    values = [generator() for _ in range(9000)]
    assert values == sorted(values, key=lambda u: u.int)
    assert len(set(values)) == len(values)


def test_backwards_clock_does_not_produce_out_of_order_ids() -> None:
    """NTP correction, a suspended laptop, a container clock jump. An
    identifier that sorts before its predecessor would break keyset
    pagination."""
    times = itertools.chain([1_700_000_000_000] * 5, [1_699_999_999_000] * 5)
    generator = Uuid7Generator(clock=lambda: next(times))  # type: ignore[arg-type]
    values = [generator() for _ in range(10)]
    assert values == sorted(values, key=lambda u: u.int)


def test_concurrent_generation_is_unique_and_ordered_per_thread() -> None:
    generator = Uuid7Generator()
    results: list[list[UUID]] = []
    lock = threading.Lock()

    def worker() -> None:
        local = [generator() for _ in range(200)]
        with lock:
            results.append(local)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    flat = [value for batch in results for value in batch]
    assert len(set(flat)) == len(flat)
    for batch in results:
        assert batch == sorted(batch, key=lambda u: u.int)
