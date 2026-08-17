"""pip install pydantic-settings

The globals.py pattern: a pydantic-settings base class plus per-environment
subclasses, selected once by an env var and assigned to a module-level name.
Plain class, not a GoF Singleton — tests construct their own instance instead
of fighting shared global state. See ../rationale.md §2 and §5.
"""

from functools import cached_property
from typing import Literal

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Production-safe defaults; subclasses override only what differs."""

    model_config = SettingsConfigDict(frozen=True)

    environment: Literal["production", "development", "test"] = "production"
    api_base_url: str = "https://api.example.com"
    request_timeout_seconds: float = 10.0

    # @computed_field + @cached_property is pydantic's own documented,
    # frozen-safe combo for a lazy, idempotent, side-effect-free field —
    # cached_property writes straight into instance.__dict__, bypassing the
    # model's overridden __setattr__, so it works even with frozen=True.
    # The ignore comment below is pydantic's own documented workaround for a
    # real static-checker limitation with this decorator stack, scoped to
    # one rule rather than blanket-silenced (see ../rationale.md §8).
    @computed_field  # type: ignore[prop-decorator]
    @cached_property
    def user_agent(self) -> str:
        # Idempotent and side-effect-free — the case cached_property is
        # actually for. Note the 3.11->3.12 thread-safety change: pre-3.12
        # this was guaranteed to run exactly once under concurrent first
        # access; 3.12+ it can run redundantly. Fine here because it's pure;
        # it would NOT be fine for a getter with a side effect (opening a
        # connection, writing a file) — use eager __init__ loading or an
        # explicit method for those instead.
        return f"power-user-linux-setup/{self.environment}"


class DevelopmentSettings(Settings):
    environment: Literal["production", "development", "test"] = "development"
    api_base_url: str = "http://localhost:8000"


class TestSettings(Settings):
    environment: Literal["production", "development", "test"] = "test"
    request_timeout_seconds: float = 1.0


def _select_settings(environment: str | None) -> Settings:
    match environment:
        case "development":
            return DevelopmentSettings()
        case "test":
            return TestSettings()
        case _:
            return Settings()


# Wired at the top of the package's __init__.py in a real project, driven by
# os.environ["ENVIRONMENT"] rather than a function argument. Kept as a plain
# module-level instance (the Global Object Pattern), not a GoF Singleton, so
# the tests below can construct their own independent instance freely.
settings = _select_settings(None)


def test_default_settings_is_production() -> None:
    assert settings.environment == "production"


def test_environment_subclass_overrides_only_named_fields() -> None:
    dev = DevelopmentSettings()
    assert dev.api_base_url == "http://localhost:8000"
    assert dev.request_timeout_seconds == Settings().request_timeout_seconds


def test_test_settings_is_a_fresh_isolated_instance() -> None:
    test_settings = TestSettings()
    assert test_settings is not settings
    assert test_settings.request_timeout_seconds == 1.0
