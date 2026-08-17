"""Fixture scope: construct expensive/shared objects at module or session
scope, but reset their *mutable* state via a function-scoped fixture — cheap
construction stays shared, isolation stays per-test. Test bodies stay DAMP
(duplicated, explicit) even when near-identical; only setup mechanics are
DRY. See ../rationale.md §7.
"""

from dataclasses import dataclass, field

import pytest


@dataclass
class Cart:
    """Stands in for an expensive-to-construct object with real mutable
    state — a module-singleton settings object or a pooled connection in a
    real project."""

    items: list[str] = field(default_factory=list)

    def add(self, item: str) -> None:
        self.items.append(item)


@pytest.fixture(scope="module")
def shared_cart() -> Cart:
    # Construct once per module — this is the "expensive setup" the module
    # scope is buying. If this constructed a real DB connection or read a
    # settings singleton, this is exactly where that would happen.
    return Cart()


@pytest.fixture
def cart(shared_cart: Cart) -> Cart:
    # Function-scoped: resets the *mutable* state of the shared object
    # before every test, so tests stay isolated without paying construction
    # cost again. Without this reset, item additions from one test would
    # leak into the next — the exact silent cross-test leak pytest's own
    # docs warn about for broad-scoped fixtures holding mutable state.
    shared_cart.items.clear()
    return shared_cart


def test_add_single_item(cart: Cart) -> None:
    # DAMP, not DRY: this scenario is spelled out explicitly rather than
    # merged with test_add_duplicate_item_keeps_both below, even though the
    # bodies look similar — each test should read top-to-bottom on its own.
    cart.add("widget")
    assert cart.items == ["widget"]


def test_add_duplicate_item_keeps_both(cart: Cart) -> None:
    cart.add("widget")
    cart.add("widget")
    assert cart.items == ["widget", "widget"]


def test_cart_state_does_not_leak_between_tests(cart: Cart) -> None:
    # Proves the function-scoped reset fixture above actually isolates
    # state — if it didn't, this test would see items left over from the
    # two tests above.
    assert cart.items == []
