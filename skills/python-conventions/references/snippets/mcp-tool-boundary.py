"""pip install fastmcp

MCP-server-specific conventions in one place: logging routed to stderr (never
stdout — it would corrupt the stdio JSON-RPC stream), an LLM-facing tool
docstring, per-parameter descriptions via Annotated[Field], annotations= for a
side-effecting tool, and ToolError at the boundary between an internal
exception and what the client sees. See ../rationale.md §9-11.
"""

import logging
import sys
from typing import Annotated

import pytest
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

# Configured once at server startup. Never let a bare print() or an
# unconfigured logging call reach stdout — the MCP stdio transport reserves
# stdout entirely for JSON-RPC framing (see ../rationale.md §9). FastMCP's own
# logger already defaults to stderr; this makes that explicit for anything
# this project's own code logs too.
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("example-polite-mcp")


class ListingNotFoundError(Exception):
    """Root exception for this module's lookups."""


def _lookup_listing_price(listing_url: str) -> float:
    """Plain, testable helper — the tool function below is a thin wrapper
    that decides what crosses the MCP boundary (see get_listing_price)."""
    if "example.invalid" in listing_url:
        raise ListingNotFoundError(f"no listing at {listing_url!r}")
    return 42.0


@mcp.tool(
    annotations={"readOnlyHint": True, "destructiveHint": False},
)
def get_listing_price(
    listing_url: Annotated[str, Field(description="A listing URL from a prior search_listings result.")],
) -> float:
    """Fetch the current asking price for one listing. Distinct from
    search_listings, which returns prices for many listings at once — use
    this only when you already have a specific listing_url and need a fresh,
    single-item price check.

    Pass listing_url exactly as returned by search_listings; a URL you
    construct yourself is not guaranteed to resolve. Returns a single float
    (site currency, no symbol) or raises if the listing no longer exists.
    """
    # The tool boundary is the one place that decides what's safe to expose
    # to the client — never let an arbitrary caught exception's str() reach
    # it unreviewed (see ../rationale.md §10). FastMCP's default already
    # unmasks plain exceptions, so an uncaught ListingNotFoundError would
    # reach the client anyway here; ToolError is used to give it a
    # deliberately worded, stable message instead of relying on that default.
    try:
        return _lookup_listing_price(listing_url)
    except ListingNotFoundError as e:
        raise ToolError(f"Listing not found: {listing_url}") from e


def test_lookup_returns_price_for_known_listing() -> None:
    assert _lookup_listing_price("https://example.com/listing/1") == 42.0


def test_lookup_raises_for_missing_listing() -> None:
    with pytest.raises(ListingNotFoundError):
        _lookup_listing_price("https://example.invalid/listing/1")
