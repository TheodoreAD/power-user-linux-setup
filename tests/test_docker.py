"""Unit tests for tasks/docker.py's pure helpers _is_subset/_merge — the only part of that module
that doesn't shell out to docker/systemctl or touch /etc/docker/daemon.json. See tests/README.md.
"""

from tasks.docker import _is_subset, _merge


def test_is_subset_true_when_all_default_keys_match():
    assert _is_subset({"log-driver": "json-file"}, {"log-driver": "json-file", "extra": "x"}) is True


def test_is_subset_false_when_a_key_differs():
    assert _is_subset({"log-driver": "json-file"}, {"log-driver": "journald"}) is False


def test_is_subset_false_when_a_key_is_missing():
    assert _is_subset({"log-driver": "json-file"}, {}) is False


def test_is_subset_recurses_into_nested_dicts():
    defaults = {"log-opts": {"max-size": "50m", "max-file": "3"}}
    existing = {"log-opts": {"max-size": "50m", "max-file": "3", "extra": "x"}}
    assert _is_subset(defaults, existing) is True


def test_is_subset_false_when_nested_value_differs():
    defaults = {"log-opts": {"max-size": "50m"}}
    existing = {"log-opts": {"max-size": "10m"}}
    assert _is_subset(defaults, existing) is False


def test_merge_adds_new_keys():
    assert _merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}


def test_merge_overwrites_scalar_values():
    assert _merge({"a": 1}, {"a": 2}) == {"a": 2}


def test_merge_recursively_merges_nested_dicts():
    base = {"log-opts": {"max-size": "50m"}}
    updates = {"log-opts": {"max-file": "3"}}
    assert _merge(base, updates) == {"log-opts": {"max-size": "50m", "max-file": "3"}}


def test_merge_does_not_mutate_inputs():
    base = {"a": {"x": 1}}
    updates = {"a": {"y": 2}}
    _merge(base, updates)
    assert base == {"a": {"x": 1}}
    assert updates == {"a": {"y": 2}}
