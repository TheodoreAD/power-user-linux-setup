"""Unit tests for tasks/docker.py's pure helpers _is_subset/_merge — the only part of that module
that doesn't shell out to docker/systemctl or touch /etc/docker/daemon.json. See tests/README.md.

Plus the credential-store task, which is testable without a keyring because the two things that can
go wrong are both observable at this level: the config merge must not lose the credentials and
settings docker owns in the same file, and the round-trip probe must treat a store that answers
wrongly exactly like one that fails. DOCKER_CONFIG is redirected under tmp_path throughout — the
real one holds a live registry credential.
"""

import json
import re
from typing import cast

import pytest
from invoke import Exit, MockContext, Result

from tasks import docker, util
from tasks.docker import _is_subset, _merge


def test_is_subset_true_when_all_default_keys_match():
    assert _is_subset({"log-driver": "json-file"}, {"log-driver": "json-file", "extra": "x"}) is True


def test_is_subset_false_when_a_key_differs():
    assert _is_subset({"log-driver": "json-file"}, {"log-driver": "journald"}) is False


def test_is_subset_false_when_a_key_is_missing():
    assert _is_subset({"log-driver": "json-file"}, {}) is False


def test_is_subset_recurses_into_nested_dicts():
    defaults: util.JsonObject = {"log-opts": {"max-size": "50m", "max-file": "3"}}
    existing: util.JsonObject = {"log-opts": {"max-size": "50m", "max-file": "3", "extra": "x"}}
    assert _is_subset(defaults, existing) is True


def test_is_subset_false_when_nested_value_differs():
    defaults: util.JsonObject = {"log-opts": {"max-size": "50m"}}
    existing: util.JsonObject = {"log-opts": {"max-size": "10m"}}
    assert _is_subset(defaults, existing) is False


def test_merge_adds_new_keys():
    assert _merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}


def test_merge_overwrites_scalar_values():
    assert _merge({"a": 1}, {"a": 2}) == {"a": 2}


def test_merge_recursively_merges_nested_dicts():
    base: util.JsonObject = {"log-opts": {"max-size": "50m"}}
    updates: util.JsonObject = {"log-opts": {"max-file": "3"}}
    assert _merge(base, updates) == {"log-opts": {"max-size": "50m", "max-file": "3"}}


def test_merge_does_not_mutate_inputs():
    base: util.JsonObject = {"a": {"x": 1}}
    updates: util.JsonObject = {"a": {"y": 2}}
    _merge(base, updates)
    assert base == {"a": {"x": 1}}
    assert updates == {"a": {"y": 2}}


@pytest.fixture
def docker_config(tmp_path, monkeypatch):
    """Never the real ~/.docker/config.json — it holds a live registry credential."""
    path = tmp_path / "config.json"
    monkeypatch.setattr(docker, "DOCKER_CONFIG", path)
    monkeypatch.setattr(util, "DRY_RUN", False)
    return path


def _round_trip_context(*, secret: str = docker._PROBE_SECRET, store_ok: bool = True, get_ok: bool = True):
    """A context answering the helper's three verbs. Matched on the trailing verb rather than on
    the whole command, since each one is a pipeline carrying a JSON payload nobody should have to
    spell twice — and MockContext's dict keys are either exact strings or compiled patterns."""
    return MockContext(
        run={
            re.compile(rf".*{docker.CREDENTIAL_HELPER} store$"): Result(
                exited=0 if store_ok else 1, stderr="store refused"
            ),
            re.compile(rf".*{docker.CREDENTIAL_HELPER} get$"): Result(
                stdout=json.dumps({"Secret": secret}), exited=0 if get_ok else 1, stderr="get refused"
            ),
            re.compile(rf".*{docker.CREDENTIAL_HELPER} erase$"): Result(exited=0),
        },
        repeat=True,
    )


def test_write_creds_store_keeps_every_other_key(docker_config):
    """The whole risk of this write: the same file holds docker's own `auths` and settings, so a
    replace rather than a merge silently destroys a credential."""
    docker_config.write_text(json.dumps({"auths": {"registry.example": {"auth": "x"}}, "HttpHeaders": {"a": "b"}}))

    assert docker._write_creds_store() is True

    written = cast(util.JsonObject, json.loads(docker_config.read_text()))
    assert written["credsStore"] == docker.CREDS_STORE
    assert written["auths"] == {"registry.example": {"auth": "x"}}
    assert written["HttpHeaders"] == {"a": "b"}


def test_write_creds_store_creates_the_file_unreadable_by_anyone_else(docker_config):
    assert docker._write_creds_store() is True
    assert docker_config.stat().st_mode & 0o777 == 0o600


def test_write_creds_store_reports_no_change_when_already_set(docker_config):
    docker_config.write_text(json.dumps({"credsStore": docker.CREDS_STORE}))
    assert docker._write_creds_store() is False


def test_plaintext_auth_count_counts_but_never_names():
    assert docker._plaintext_auth_count({"auths": {"a.example": {}, "b.example": {}}}) == 2
    assert docker._plaintext_auth_count({}) == 0


def test_round_trip_passes_when_the_store_returns_what_was_stored():
    assert docker._credential_round_trip(_round_trip_context()) is None


def test_round_trip_fails_when_the_store_returns_a_different_secret():
    """The failure a `which` check cannot see: the helper runs, the store answers, and what comes
    back is not what went in."""
    reason = docker._credential_round_trip(_round_trip_context(secret="something-else"))
    assert reason is not None
    assert "different secret" in reason


def test_round_trip_fails_when_the_store_refuses():
    assert "store" in str(docker._credential_round_trip(_round_trip_context(store_ok=False)))
    assert "get" in str(docker._credential_round_trip(_round_trip_context(get_ok=False)))


def test_configure_credential_store_writes_nothing_when_the_helper_is_missing(docker_config, monkeypatch):
    """A headless machine legitimately has no helper — the `workstation` tag excludes the package.
    Saying so is the requirement; silently leaving credentials in a file is what this task ends."""
    monkeypatch.setattr(util, "command_exists", lambda _cmd: False)

    docker.configure_credential_store(MockContext())

    assert not docker_config.exists()


def test_configure_credential_store_refuses_to_write_when_the_store_does_not_answer(docker_config, monkeypatch):
    """Fails loudly rather than degrading: oras selects a secretservice store without checking that
    it works, so a half-configured machine fails every registry push as though the password were
    wrong."""
    monkeypatch.setattr(util, "command_exists", lambda _cmd: True)

    with pytest.raises(Exit):
        docker.configure_credential_store(_round_trip_context(store_ok=False))

    assert not docker_config.exists()


def test_configure_credential_store_sets_the_key_when_the_store_answers(docker_config, monkeypatch):
    monkeypatch.setattr(util, "command_exists", lambda _cmd: True)

    docker.configure_credential_store(_round_trip_context())

    assert json.loads(docker_config.read_text())["credsStore"] == docker.CREDS_STORE
