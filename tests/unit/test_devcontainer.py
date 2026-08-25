"""Unit tests for tasks/devcontainer.py's _discover_candidates (candidate discovery against a
fabricated $HOME) and _render_mounts_json (devcontainer.json fragment rendering) — no real
filesystem/env touched outside a tmp_path fixture. See tests/README.md.
"""

import json
import re
from pathlib import Path
from typing import Any, cast

from tasks.devcontainer import MountCandidate, _discover_candidates, _render_mounts_json

_REPO_ROOT = Path(__file__).parent.parent.parent


def test_bootstrap_devcontainer_runs_setup_with_pulse_assume_yes():
    # The one behavior change in the deploy-writer conversion that can break something that works:
    # tasks/deploy.py leaves a pre-existing destination alone when stdin isn't a terminal and
    # nothing said yes, so an unattended `inv setup` that doesn't set PULSE_ASSUME_YES would build
    # an image that looks fine and is silently missing a dotfile. docker/Dockerfile and the
    # devcontainer.json postCreateCommand both reach `inv setup` only through this script.
    script = (_REPO_ROOT / "bootstrap-devcontainer.sh").read_text()

    setup_lines = [line for line in script.splitlines() if re.search(r"\binv setup\b", line)]
    assert setup_lines, "bootstrap-devcontainer.sh no longer runs `inv setup`?"
    assert all("PULSE_ASSUME_YES=1" in line for line in setup_lines), setup_lines


def _ids(home, identity_toml=None, ssh_auth_sock=None, *, is_wsl=False):
    return [c.id for c in _discover_candidates(home, identity_toml, ssh_auth_sock, is_wsl=is_wsl)]


def test_discover_candidates_empty_home_yields_nothing(tmp_path):
    assert _discover_candidates(tmp_path, None, None) == []


def test_discover_candidates_ssh_agent_offered_when_socket_exists(tmp_path):
    sock = tmp_path / "agent.sock"
    sock.write_text("")
    assert "ssh-agent" in _ids(tmp_path, ssh_auth_sock=str(sock))


def test_discover_candidates_ssh_agent_not_offered_when_socket_missing(tmp_path):
    assert "ssh-agent" not in _ids(tmp_path, ssh_auth_sock=str(tmp_path / "nonexistent.sock"))


def test_discover_candidates_ssh_agent_not_offered_when_env_unset(tmp_path):
    assert "ssh-agent" not in _ids(tmp_path, ssh_auth_sock=None)


def test_discover_candidates_ssh_dir_offered_when_present(tmp_path):
    (tmp_path / ".ssh").mkdir()
    assert "ssh-dir" in _ids(tmp_path)


def test_discover_candidates_ssh_dir_not_offered_when_absent(tmp_path):
    assert "ssh-dir" not in _ids(tmp_path)


def test_discover_candidates_ssh_dir_defaults_true_when_no_agent_socket(tmp_path):
    (tmp_path / ".ssh").mkdir()
    candidates = _discover_candidates(tmp_path, None, None)
    ssh_dir = next(c for c in candidates if c.id == "ssh-dir")
    assert ssh_dir.default is True


def test_discover_candidates_ssh_dir_defaults_false_when_agent_socket_present(tmp_path):
    (tmp_path / ".ssh").mkdir()
    sock = tmp_path / "agent.sock"
    sock.write_text("")
    candidates = _discover_candidates(tmp_path, None, str(sock))
    ssh_dir = next(c for c in candidates if c.id == "ssh-dir")
    assert ssh_dir.default is False


def test_discover_candidates_ssh_agent_gets_wsl_caveat_only_when_is_wsl(tmp_path):
    sock = tmp_path / "agent.sock"
    sock.write_text("")
    without_wsl = _discover_candidates(tmp_path, None, str(sock), is_wsl=False)
    with_wsl = _discover_candidates(tmp_path, None, str(sock), is_wsl=True)
    assert next(c for c in without_wsl if c.id == "ssh-agent").caveat is None
    assert next(c for c in with_wsl if c.id == "ssh-agent").caveat is not None


def test_discover_candidates_pulse_identity_offered_when_present(tmp_path):
    (tmp_path / ".config" / "power-user-linux-setup").mkdir(parents=True)
    assert "pulse-identity" in _ids(tmp_path)


def test_discover_candidates_gitconfig_readonly_and_default_true(tmp_path):
    (tmp_path / ".gitconfig").write_text("")
    candidates = _discover_candidates(tmp_path, None, None)
    gitconfig = next(c for c in candidates if c.id == "gitconfig")
    assert gitconfig.readonly is True
    assert gitconfig.default is True


def test_discover_candidates_low_sensitivity_dirs_default_false(tmp_path):
    (tmp_path / ".aws").mkdir()
    (tmp_path / ".kube").mkdir()
    (tmp_path / ".config" / "gcloud").mkdir(parents=True)
    (tmp_path / ".config" / "gh").mkdir(parents=True)
    (tmp_path / ".gnupg").mkdir()
    candidates = _discover_candidates(tmp_path, None, None)
    by_id = {c.id: c for c in candidates}
    for cand_id in ("aws", "kube", "gcloud-config", "gh-config", "gnupg"):
        assert by_id[cand_id].default is False, cand_id


def test_discover_candidates_no_certs_bundle_when_identity_toml_missing(tmp_path):
    candidates = _discover_candidates(tmp_path, tmp_path / "identity.toml", None)
    assert not any(c.id.startswith("corporate-cert-bundle") for c in candidates)


def test_discover_candidates_certs_bundle_offered_when_configured_and_file_exists(tmp_path):
    bundle = tmp_path / "corp-ca.pem"
    bundle.write_text("-----BEGIN CERTIFICATE-----\n")
    identity_toml = tmp_path / "identity.toml"
    identity_toml.write_text(f'[certs]\nbundle = "{bundle}"\n')

    candidates = _discover_candidates(tmp_path, identity_toml, None)
    cert = next(c for c in candidates if c.id == "corporate-cert-bundle")
    assert cert.source == str(bundle)
    assert cert.target == str(bundle)
    assert cert.readonly is True


def test_discover_candidates_certs_bundle_not_offered_when_configured_file_missing(tmp_path):
    identity_toml = tmp_path / "identity.toml"
    identity_toml.write_text(f'[certs]\nbundle = "{tmp_path / "nonexistent.pem"}"\n')
    candidates = _discover_candidates(tmp_path, identity_toml, None)
    assert not any(c.id.startswith("corporate-cert-bundle") for c in candidates)


def test_discover_candidates_certs_bundle_list_yields_multiple_candidates(tmp_path):
    bundle1 = tmp_path / "corp-ca-1.pem"
    bundle2 = tmp_path / "corp-ca-2.pem"
    bundle1.write_text("cert1")
    bundle2.write_text("cert2")
    identity_toml = tmp_path / "identity.toml"
    identity_toml.write_text(f'[certs]\nbundle = ["{bundle1}", "{bundle2}"]\n')

    ids = _ids(tmp_path, identity_toml=identity_toml)
    assert "corporate-cert-bundle" in ids
    assert "corporate-cert-bundle-1" in ids


def test_render_mounts_json_renders_home_relative_target():
    cand = MountCandidate(
        id="ssh-dir",
        label="~/.ssh",
        source="${localEnv:HOME}/.ssh",
        target=None,
        target_suffix="/.ssh",
        readonly=False,
        default=True,
    )
    fragment = _render_mounts_json([cand], "/home/vscode")
    assert '"source=${localEnv:HOME}/.ssh,target=/home/vscode/.ssh,type=bind"' in fragment


def test_render_mounts_json_readonly_adds_flag():
    cand = MountCandidate(
        id="gitconfig",
        label="~/.gitconfig",
        source="${localEnv:HOME}/.gitconfig",
        target=None,
        target_suffix="/.gitconfig",
        readonly=True,
        default=True,
    )
    fragment = _render_mounts_json([cand], "/home/vscode")
    assert ",readonly" in fragment


def test_render_mounts_json_fixed_target_ignores_container_home():
    cand = MountCandidate(
        id="corporate-cert-bundle",
        label="corp CA",
        source="/etc/corp/ca.pem",
        target="/etc/corp/ca.pem",
        target_suffix=None,
        readonly=True,
        default=True,
    )
    fragment = _render_mounts_json([cand], "/home/vscode")
    assert "source=/etc/corp/ca.pem,target=/etc/corp/ca.pem" in fragment


def test_render_mounts_json_collects_remote_env_from_selected_candidates():
    cand = MountCandidate(
        id="ssh-agent",
        label="ssh agent",
        source="${localEnv:SSH_AUTH_SOCK}",
        target="/tmp/ssh-agent.sock",
        target_suffix=None,
        readonly=False,
        default=True,
        remote_env={"SSH_AUTH_SOCK": "/tmp/ssh-agent.sock"},
    )
    fragment = _render_mounts_json([cand], "/home/vscode")
    assert '"remoteEnv"' in fragment
    assert '"SSH_AUTH_SOCK": "/tmp/ssh-agent.sock"' in fragment


def test_render_mounts_json_omits_remote_env_when_none_selected():
    cand = MountCandidate(
        id="gitconfig",
        label="~/.gitconfig",
        source="${localEnv:HOME}/.gitconfig",
        target=None,
        target_suffix="/.gitconfig",
        readonly=True,
        default=True,
    )
    fragment = _render_mounts_json([cand], "/home/vscode")
    assert "remoteEnv" not in fragment


def test_render_mounts_json_is_valid_json():
    cand = MountCandidate(
        id="gitconfig",
        label="~/.gitconfig",
        source="${localEnv:HOME}/.gitconfig",
        target=None,
        target_suffix="/.gitconfig",
        readonly=True,
        default=True,
    )
    parsed = cast(dict[str, Any], json.loads(_render_mounts_json([cand], "/home/vscode")))
    assert parsed["mounts"] == ["source=${localEnv:HOME}/.gitconfig,target=/home/vscode/.gitconfig,type=bind,readonly"]
