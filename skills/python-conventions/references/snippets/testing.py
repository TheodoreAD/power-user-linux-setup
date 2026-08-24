"""Fixture scope: construct expensive/shared objects at module or session
scope, but reset their *mutable* state via a function-scoped fixture — cheap
construction stays shared, isolation stays per-test. Setup mechanics (the
"how") are DRY; the scenario each test verifies (the "what") stays visible in
that test. parametrize a pure value matrix; write a new test when a new case
would change the test's logic. See ../rationale.md §7.
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
        if not item:
            raise ValueError("item name must not be empty")
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


@pytest.mark.parametrize(
    ("added", "expected"),
    [
        (["widget"], ["widget"]),
        (["widget", "widget"], ["widget", "widget"]),
        (["a", "b"], ["a", "b"]),
    ],
    ids=["single", "duplicate-kept", "order-kept"],
)
def test_add_keeps_every_item_in_order(cart: Cart, added: list[str], expected: list[str]) -> None:
    # A pure value matrix: every case runs the same logic against different
    # inputs, so a new case is a new row, not a new function. The table keeps
    # the "what" more visible than three copy-pasted bodies would — the
    # varying values sit apart from the fixed logic. `ids` name the cases
    # once the raw values stop being self-explanatory in a failure report.
    for item in added:
        cart.add(item)
    assert cart.items == expected


def test_add_rejects_empty_name(cart: Cart) -> None:
    # Not a fourth row above: this case has different logic (a raised error,
    # nothing added) — folding it into the table would put a branch on the
    # parameters inside the test body, which hides the scenario. A case that
    # changes the *logic* is its own test; a case that changes a *value* is
    # a row.
    with pytest.raises(ValueError, match="empty"):
        cart.add("")
    assert cart.items == []


def test_cart_state_does_not_leak_between_tests(cart: Cart) -> None:
    # Proves the function-scoped reset fixture above actually isolates
    # state — if it didn't, this test would see items left over from the
    # tests above.
    assert cart.items == []
