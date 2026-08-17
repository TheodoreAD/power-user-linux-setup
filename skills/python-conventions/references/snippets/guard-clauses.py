"""Guard clauses validate a caller's contract; EAFP handles runtime
operations Python already fails loudly on. See ../rationale.md §3.
"""

import pytest


class OrderError(Exception):
    """Root exception for this module — see exceptions.py for the full
    hierarchy shape this would grow into in a real package."""


def apply_discount(price: float, percent: float) -> float:
    """Guard clause: validates the caller's own contract (argument range) —
    the asymmetric happy-path/rare-early-out case a guard clause is for."""
    if not 0 <= percent <= 100:
        raise OrderError(f"percent must be 0-100, got {percent}")
    return price * (1 - percent / 100)


def read_cached_total(cache: dict[str, float], key: str) -> float:
    """EAFP: a dict lookup is a runtime operation Python already fails
    loudly on — checking `key in cache` first (LBYL) would be a needless
    check-then-act split, not a contract check."""
    try:
        return cache[key]
    except KeyError as e:
        raise OrderError(f"no cached total for {key!r}") from e


def find_order(orders: dict[str, float], order_id: str) -> float:
    """Fail-fast: never return None/a sentinel on failure — it makes 'not
    found' and 'found, total happens to be falsy' ambiguous to the caller.
    Raise instead."""
    if order_id not in orders:
        raise OrderError(f"unknown order {order_id!r}")
    return orders[order_id]


def test_guard_clause_rejects_out_of_range_input() -> None:
    with pytest.raises(OrderError):
        apply_discount(100.0, 150.0)


def test_guard_clause_allows_valid_input() -> None:
    assert apply_discount(100.0, 10.0) == 90.0


def test_eafp_wraps_the_real_runtime_error() -> None:
    with pytest.raises(OrderError):
        read_cached_total({}, "missing")


def test_fail_fast_raises_instead_of_returning_none() -> None:
    with pytest.raises(OrderError):
        find_order({}, "missing")
