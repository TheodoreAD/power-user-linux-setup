"""pip install pydantic

Data modeling defaults: frozen dataclass for internal records, Pydantic v2
for boundary/settings validation. NamedTuple only for the narrow escalation
cases documented in ../rationale.md §1.
"""

from dataclasses import FrozenInstanceError, dataclass
from typing import NamedTuple

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError


@dataclass(frozen=True)
class OrderLine:
    """Internal record — no external validation needed."""

    sku: str
    quantity: int


class ApiOrderRequest(BaseModel):
    """Boundary data — parsing untrusted external input."""

    model_config = ConfigDict(frozen=True)

    sku: str
    quantity: int


class Point(NamedTuple):
    """Small, closed, order-is-the-meaning — the NamedTuple escalation case."""

    x: float
    y: float


def test_dataclass_is_frozen() -> None:
    line = OrderLine(sku="widget", quantity=2)
    with pytest.raises(FrozenInstanceError):
        line.quantity = 3  # type: ignore[misc]


def test_pydantic_model_validates_and_freezes() -> None:
    request = ApiOrderRequest.model_validate({"sku": "widget", "quantity": 2})
    assert request.quantity == 2
    with pytest.raises(ValidationError):
        request.quantity = 3


def test_namedtuple_unpacks_positionally() -> None:
    point = Point(1.0, 2.0)
    x, y = point
    assert (x, y) == (1.0, 2.0)
