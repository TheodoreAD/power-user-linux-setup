"""Structured concurrency for a fan-out orchestrator: asyncio.TaskGroup over
gather() (cancels siblings on first failure instead of leaving them running
orphaned), with a Semaphore capping how many sites are queried at once. See
../rationale.md §12.
"""

import asyncio
import contextlib
from dataclasses import dataclass


@dataclass(frozen=True)
class SiteResult:
    site: str
    price: float


class SiteQueryError(Exception):
    """Raised when a single site's query fails; caught per-child so one
    site's failure doesn't cancel the whole fan-out (see below)."""


async def _query_site(site: str, *, fail: bool = False) -> SiteResult:
    """Stand-in for an async fastmcp.client call to one site MCP."""
    await asyncio.sleep(0)
    if fail:
        raise SiteQueryError(f"{site} did not respond")
    return SiteResult(site=site, price=10.0)


async def query_sites_tolerant(sites: list[str], *, max_concurrent: int = 3) -> list[SiteResult]:
    """Fan out to several sites concurrently, capped at max_concurrent in
    flight. A single site failing is recorded and skipped rather than
    aborting the whole batch -- the catch happens inside each child task, so
    TaskGroup's cancel-on-uncaught-exception guarantee still applies to any
    genuinely unexpected error."""
    semaphore = asyncio.Semaphore(max_concurrent)
    results: list[SiteResult] = []

    async def _bounded_query(site: str) -> None:
        async with semaphore, contextlib.suppress(SiteQueryError):
            results.append(await _query_site(site))

    async with asyncio.TaskGroup() as tg:
        for site in sites:
            tg.create_task(_bounded_query(site))

    return results


async def query_sites_fail_fast(sites: list[str]) -> list[SiteResult]:
    """The other real shape: any site erroring should abort the whole
    fan-out and cancel the rest, e.g. a caller that needs all-or-nothing
    results. Let the exception propagate into the group uncaught -- this is
    what TaskGroup gives you for free that gather() does not."""
    results: list[SiteResult] = []

    async def _collect(site: str) -> None:
        results.append(await _query_site(site))

    async with asyncio.TaskGroup() as tg:
        for site in sites:
            tg.create_task(_collect(site))

    return results


def test_tolerant_fan_out_skips_failed_sites() -> None:
    results = asyncio.run(query_sites_tolerant(["a", "b"]))
    assert {r.site for r in results} == {"a", "b"}


def test_fail_fast_cancels_siblings_on_error() -> None:
    async def _run() -> None:
        async def _bad(site: str) -> SiteResult:
            if site == "bad":
                raise SiteQueryError("boom")
            await asyncio.sleep(0.05)
            return await _query_site(site)

        async with asyncio.TaskGroup() as tg:
            tg.create_task(_bad("bad"))
            tg.create_task(_bad("slow"))

    try:
        asyncio.run(_run())
    except* SiteQueryError:
        pass
    else:
        raise AssertionError("expected SiteQueryError to propagate via ExceptionGroup")
