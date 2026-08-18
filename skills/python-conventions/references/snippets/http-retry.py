"""pip install httpx tenacity

httpx for new HTTP fetch paths (requests-compatible, safer default timeouts,
async-ready), one Client reused for its lifetime, an explicit site-tuned
timeout, and tenacity for retry/backoff -- scoped to transient network
conditions and a narrow retryable-status set, never plain 4xx "real answers"
like 404. See ../rationale.md §13.
"""

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_random_exponential

REQUEST_TIMEOUT_SECONDS = 15.0
RETRYABLE_STATUS_CODES = {429, 502, 503, 504}


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRYABLE_STATUS_CODES
    return False


class PoliteFetcher:
    """One httpx.Client per instance, constructed once and reused -- fewer
    TCP/TLS handshakes is both a perf win and direct service to the
    'politeness' mission (less connection-setup load on the target site)."""

    def __init__(self, base_url: str) -> None:
        self._client = httpx.Client(base_url=base_url, timeout=REQUEST_TIMEOUT_SECONDS)

    def close(self) -> None:
        self._client.close()

    @retry(
        retry=retry_if_exception(_is_retryable),
        wait=wait_random_exponential(multiplier=1, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def get(self, path: str) -> httpx.Response:
        """Retries only transient network errors or a narrow retryable-status
        set -- a 404/403 is a real answer from the site, not a blip, and
        retrying it would just be hammering the site for no reason. A
        response's own Retry-After header, when present, should take
        precedence over the computed backoff delay (not modeled here --
        tenacity's `wait` callable receives retry state and can read the
        last raised exception's response headers to implement this)."""
        response = self._client.get(path)
        response.raise_for_status()
        return response


def _transport_for(behavior: list[int]) -> httpx.MockTransport:
    """Test helper: returns status codes from `behavior` in order, one per
    call, simulating a flaky-then-healthy or a permanently-4xx site."""
    calls = iter(behavior)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(next(calls), request=request)

    return httpx.MockTransport(handler)


def test_retries_on_transient_5xx_then_succeeds() -> None:
    fetcher = PoliteFetcher("https://example.com")
    fetcher._client = httpx.Client(base_url="https://example.com", transport=_transport_for([503, 200]))
    response = fetcher.get("/listing/1")
    assert response.status_code == 200


def test_does_not_retry_a_real_404() -> None:
    fetcher = PoliteFetcher("https://example.com")
    fetcher._client = httpx.Client(base_url="https://example.com", transport=_transport_for([404, 200]))
    try:
        fetcher.get("/listing/missing")
    except httpx.HTTPStatusError as e:
        assert e.response.status_code == 404
    else:
        raise AssertionError("expected a 404 to propagate, not retry")
