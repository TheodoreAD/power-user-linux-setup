"""Minimal exception hierarchy: one root per package, deeper leaves only
once a caller actually needs to discriminate. Mirrors requests/click's own
shallow (2-3 level) shape. See ../rationale.md §3.
"""

import pytest


class PackageError(Exception):
    """Root of this package's exception hierarchy — catch this to catch
    anything this package itself raises deliberately."""


class ConfigurationError(PackageError):
    """A caller-fixable setup problem: bad/missing config, invalid env var."""


class UpstreamError(PackageError):
    """The dependency this package talks to (an API, a subprocess) failed."""


class UpstreamTimeoutError(UpstreamError, TimeoutError):
    """Multiply inherits the matching stdlib type too, so callers can catch
    either `UpstreamError` (this package's own granularity) or the stdlib
    `TimeoutError` (generic granularity) — the same shape as
    `requests.MissingSchema` also inheriting `ValueError`."""


def _raise_upstream_timeout() -> None:
    raise UpstreamTimeoutError("upstream did not respond")


def test_configuration_error_is_catchable_as_package_error() -> None:
    with pytest.raises(PackageError):
        raise ConfigurationError("missing API_KEY")


def test_specific_exception_is_catchable_at_every_relevant_level() -> None:
    with pytest.raises(PackageError):
        _raise_upstream_timeout()

    with pytest.raises(TimeoutError):
        _raise_upstream_timeout()
