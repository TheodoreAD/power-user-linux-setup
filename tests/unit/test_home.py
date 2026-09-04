"""Unit tests for tasks/home.py — the registry of every claim this repo has on ~.

What matters here is that the registry stays *derived*: the whole-file third must come from
`deploy.managed_paths()` rather than be restated, an installer's destination must come from
setup.toml rather than be listed, and a writer with no notion of "dirty" must report that rather
than borrow one. See tests/README.md.
"""

import json
from pathlib import Path
from typing import cast

import pytest
from invoke import MockContext

from tasks import deploy, home, util


def _stub_config(monkeypatch, packages: dict[str, util.PackageConfig]) -> None:
    monkeypatch.setattr(util, "load_config", lambda: {"packages": packages})
    monkeypatch.setattr(util, "enabled_packages", lambda: packages)
    monkeypatch.setattr(
        util,
        "packages_by_method",
        lambda method: {n: c for n, c in packages.items() if c.get("method") == method},
    )


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    """Move the whole registry's idea of `~` into tmp_path.

    Both constants have to move together: `_LOCAL_BIN` is computed at import from the real home, so
    patching `_HOME` alone would leave every `~/.local/bin` claim pointing at the real machine and
    then filtered out as "not under home".
    """
    monkeypatch.setattr(home, "_HOME", tmp_path)
    monkeypatch.setattr(home, "_LOCAL_BIN", tmp_path / ".local" / "bin")
    return tmp_path


# ---------------------------------------------------------------------------
# whole-file — derived from deploy.py, never restated
# ---------------------------------------------------------------------------


def test_whole_file_claims_are_exactly_the_deploy_registry(fake_home, monkeypatch):
    _stub_config(
        monkeypatch,
        {
            "agents-md": {
                "method": "wrapper-script",
                "dest": str(fake_home / "AGENTS.md"),
                "content_file": "config/statusline-command.sh",
            },
            "wezterm": {
                "method": "archive",
                "config_files": [{"src": "config/wezterm.lua", "dst": str(fake_home / "wezterm.lua")}],
            },
        },
    )

    claimed = {c.path for c in home._whole_file_claims()}

    assert claimed == set(deploy.managed_paths())


def test_a_seeded_destination_is_user_authority_and_a_managed_one_is_pulse(fake_home, monkeypatch):
    _stub_config(
        monkeypatch,
        {
            "agents-md": {
                "method": "wrapper-script",
                "dest": str(fake_home / "AGENTS.md"),
                "content_file": "config/statusline-command.sh",
            },
            "wezterm": {
                "method": "archive",
                "config_files": [{"src": "config/w.lua", "dst": str(fake_home / "w.lua")}],
            },
        },
    )

    by_path = {c.path: c for c in home._whole_file_claims()}

    assert by_path[fake_home / "AGENTS.md"].authority == home.Authority.PULSE
    assert by_path[fake_home / "w.lua"].authority == home.Authority.USER


def test_a_symlink_dest_is_its_own_claim(fake_home, monkeypatch):
    _stub_config(
        monkeypatch,
        {
            "agents-md": {
                "method": "wrapper-script",
                "dest": str(fake_home / "AGENTS.md"),
                "content_file": "config/statusline-command.sh",
                "symlink_dest": [str(fake_home / ".claude" / "CLAUDE.md")],
            }
        },
    )

    claims = list(home._symlink_claims())

    assert [c.path for c in claims] == [fake_home / ".claude" / "CLAUDE.md"]
    assert claims[0].writer == home.Writer.SYMLINK


def test_an_always_symlink_dest_is_claimed_like_any_other(fake_home, monkeypatch):
    """The registry must see a `{ path, always }` table, not choke on it or drop it.

    It parsed `symlink_dest` itself before the table shape existed, which would have handed a
    mapping straight to `Path()` — a claim silently missing from the one command that answers "is
    this path PULSE-managed?".
    """
    _stub_config(
        monkeypatch,
        {
            "agents-md": {
                "method": "wrapper-script",
                "dest": str(fake_home / ".agents" / "AGENTS.md"),
                "content_file": "config/statusline-command.sh",
                "symlink_dest": [
                    {"path": str(fake_home / "AGENTS.md"), "always": True},
                    str(fake_home / ".claude" / "CLAUDE.md"),
                ],
            }
        },
    )

    claims = list(home._symlink_claims())

    assert [c.path for c in claims] == [fake_home / "AGENTS.md", fake_home / ".claude" / "CLAUDE.md"]
    assert {c.source for c in claims} == {str(fake_home / ".agents" / "AGENTS.md")}


# ---------------------------------------------------------------------------
# blocks, merges and key surgery
# ---------------------------------------------------------------------------


def test_a_block_claim_is_one_per_file_and_block(fake_home, monkeypatch):
    _stub_config(
        monkeypatch,
        {
            "fzf": {"zshrc": "source fzf", "zshenv": "export FZF=1"},
            "direnv": {"zshrc": "eval direnv"},
        },
    )

    targets = [c.target for c in home._block_claims()]

    assert "~/.zshrc [PULSE::fzf]" in targets
    assert "~/.zshenv [PULSE::fzf]" in targets
    assert "~/.zshrc [PULSE::direnv]" in targets


def test_the_identity_derived_blocks_are_the_machine_tier(fake_home, monkeypatch):
    _stub_config(monkeypatch, {})

    machine = {c.target for c in home._block_claims() if c.tier == home.Tier.MACHINE}

    # A corporate CA path and a proxy host are true of this box only — the one piece of the surface
    # that is already machine-local rather than public.
    assert any("certs" in t for t in machine)
    assert any("proxy" in t for t in machine)
    assert any(".ssh/config" in t for t in machine)


def test_several_writers_may_claim_one_path(fake_home, monkeypatch):
    """The registry is a list, not a path-keyed mapping: ~/.zshrc carries both marker blocks and
    zsh.configure-omz's regex surgery, which are different writers with different conflicts."""
    _stub_config(monkeypatch, {"fzf": {"zshrc": "source fzf"}})

    writers = {c.writer for c in [*home._block_claims(), *home._key_claims()] if c.path == fake_home / ".zshrc"}

    assert writers == {home.Writer.BLOCK, home.Writer.KEY}


# ---------------------------------------------------------------------------
# imperative and install
# ---------------------------------------------------------------------------


def test_a_declared_dconf_key_is_claimed(fake_home, monkeypatch):
    _stub_config(
        monkeypatch,
        {"gnome-ext-vitals": {"method": "gnome-extension", "dconf": {"/org/gnome/shell/extensions/vitals/x": "true"}}},
    )

    claims = [c for c in home._imperative_claims() if c.owner == "gnome-ext-vitals"]

    assert claims[0].target == "dconf /org/gnome/shell/extensions/vitals/x"
    assert claims[0].path is None


def test_a_single_binary_package_claims_the_binary_not_the_install_prefix(fake_home):
    cfg: util.PackageConfig = {
        "method": "script",
        "check_cmd": "dprint",
        "single_binary": True,
        "env": {"DPRINT_INSTALL": "~/.local"},
    }

    targets = [path for path, _ in home._install_targets("dprint", cfg)]

    assert targets == [fake_home / ".local" / "bin" / "dprint"]


def test_an_install_target_outside_home_is_not_claimed(fake_home, monkeypatch):
    _stub_config(monkeypatch, {"somewhere": {"method": "archive", "install_dir": "/opt/somewhere"}})

    assert not [c for c in home._install_claims() if c.owner == "somewhere"]


def test_an_installed_tree_is_derived_not_public(fake_home, monkeypatch):
    _stub_config(monkeypatch, {"go": {"method": "archive", "install_dir": str(fake_home / ".local" / "share" / "go")}})

    claim = next(c for c in home._install_claims() if c.owner == "go")

    assert claim.tier == home.Tier.DERIVED
    assert claim.writer == home.Writer.INSTALL


# ---------------------------------------------------------------------------
# classification — a registry entry does not imply a classifier
# ---------------------------------------------------------------------------


def test_only_the_deploy_writer_produces_classifiable_claims():
    assert {c.writer for c in home.claims() if c.classifiable} == {
        home.Writer.WHOLE_FILE,
        home.Writer.WHOLE_FILE_UNDECLARED,
    }


def test_a_claim_with_no_path_reports_no_state():
    claim = home.Claim(
        target="dconf /org/gnome/x",
        writer=home.Writer.IMPERATIVE,
        authority=home.Authority.CO_OWNED,
        tier=home.Tier.PUBLIC,
        owner="x",
    )

    assert home.state_of(claim, {}) == "—"


def test_an_unclassifiable_claim_reports_presence_only(tmp_path):
    path = tmp_path / "flameshot.ini"
    claim = home.Claim(
        target="ini",
        writer=home.Writer.KEY,
        authority=home.Authority.APP,
        tier=home.Tier.PUBLIC,
        owner="x",
        path=path,
    )

    assert home.state_of(claim, {}) == "absent"
    path.write_text("[General]\n")
    assert home.state_of(claim, {}) == "present"


def test_a_deploy_backed_claim_reports_its_real_state(tmp_path, monkeypatch):
    """The claim carries the writer's own Managed, so the state comes from deploy.classify() on the
    same object the writer acts on rather than from a path lookup that could go stale."""
    monkeypatch.setattr(deploy, "_REPO_ROOT", tmp_path)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "app.conf").write_text("source\n")
    path = tmp_path / "app.conf"
    path.write_text("edited here\n")
    managed = deploy.Managed(
        path=path, package="app", source="config/app.conf", mechanism=deploy.Mechanism.MANAGED_FILE
    )
    claim = home.Claim(
        target="~/app.conf",
        writer=home.Writer.WHOLE_FILE_UNDECLARED,
        authority=home.Authority.PULSE,
        tier=home.Tier.PUBLIC,
        owner="app",
        path=path,
        managed=managed,
    )

    manifest: deploy.Manifest = {
        str(path): {
            "package": "app",
            "source": "config/app.conf",
            "mechanism": "managed-file",
            "digest": "not-what-is-there",
            "deployed_at": "2026-08-30T00:00:00+00:00",
        }
    }
    assert home.state_of(claim, manifest) == "dirty"


# ---------------------------------------------------------------------------
# scope
# ---------------------------------------------------------------------------


def test_system_targets_are_all_outside_home():
    assert not [t for t in home.SYSTEM_TARGETS if t.startswith(str(home._HOME))]


def test_the_real_registry_covers_every_writer_it_defines():
    """A writer in the enum with no claim on a real machine is a classification nobody can act on —
    it would make the summary's percentages describe a vocabulary rather than a surface."""
    assert {c.writer for c in home.claims()} == set(home.Writer)


# ---------------------------------------------------------------------------
# the task
# ---------------------------------------------------------------------------


@pytest.fixture
def two_claims(monkeypatch):
    listed = [
        home.Claim(
            target="~/AGENTS.md",
            writer=home.Writer.WHOLE_FILE,
            authority=home.Authority.PULSE,
            tier=home.Tier.PUBLIC,
            owner="agents-md",
            managed=deploy.Managed(
                path=Path("/nonexistent/AGENTS.md"),
                package="agents-md",
                source="config/agents-md",
                mechanism=deploy.Mechanism.WRAPPER_SCRIPT,
            ),
        ),
        home.Claim(
            target="dconf /org/gnome/x",
            writer=home.Writer.IMPERATIVE,
            authority=home.Authority.CO_OWNED,
            tier=home.Tier.PUBLIC,
            owner="gnome-ext-x",
        ),
    ]
    monkeypatch.setattr(home, "claims", lambda: listed)
    monkeypatch.setattr(deploy, "load_manifest", dict)
    return listed


def test_the_task_filters_by_writer(two_claims, capsys):
    home.list_claims(MockContext(), writer="imperative")

    out = capsys.readouterr().out
    assert "dconf /org/gnome/x" in out
    assert "~/AGENTS.md" not in out
    assert "1 claim(s) of 2" in out


def test_the_task_emits_json(two_claims, capsys):
    home.list_claims(MockContext(), json=True)

    payload = cast(list[dict[str, object]], json.loads(capsys.readouterr().out))
    assert [entry["writer"] for entry in payload] == ["whole-file", "imperative"]
    assert [entry["classifiable"] for entry in payload] == [True, False]


def test_a_filter_matching_nothing_says_so(two_claims, capsys):
    home.list_claims(MockContext(), tier="secret")

    assert "no claims match" in capsys.readouterr().out
