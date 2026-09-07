"""Unit tests for tasks/verify.py's pure helpers: _resolve (which check each package method gets),
_deploy_check (pass/fail per deploy state and ownership policy), and _all_checks' coverage of
config_files and skills through the deploy registry. Real tmp_path files, not mocked I/O — the
content comparison is the entire point of the check. See tests/README.md.
"""

import pytest

from tasks import deploy, util, verify


def test_resolve_wrapper_script_with_content_file_returns_deploy_kind():
    cfg: util.PackageConfig = {"dest": "~/AGENTS.md", "content_file": "config/statusline-command.sh"}
    kind, target = verify._resolve("agents-md", cfg, util.PackageMethod.WRAPPER_SCRIPT)
    assert (kind, target) == ("deploy", "~/AGENTS.md")


def test_resolve_wrapper_script_with_assembled_from_returns_deploy_kind():
    """An assembled destination has no `content_file`, and resolving it to an existence-only check
    would silently drop ~/AGENTS.md's content verification — the one this function exists for."""
    cfg: util.PackageConfig = {"dest": "~/AGENTS.md", "assembled_from": "agents_md"}
    kind, target = verify._resolve("agents-md", cfg, util.PackageMethod.WRAPPER_SCRIPT)
    assert (kind, target) == ("deploy", "~/AGENTS.md")


def test_resolve_wrapper_script_without_content_file_falls_back_to_path():
    cfg: util.PackageConfig = {"dest": "~/.local/bin/some-tool"}
    kind, target = verify._resolve("some-tool", cfg, util.PackageMethod.WRAPPER_SCRIPT)
    assert (kind, target) == ("path", "~/.local/bin/some-tool")


def test_resolve_still_honors_verify_false_and_verify_cmd_before_method_dispatch():
    assert verify._resolve("x", {"verify": False}, util.PackageMethod.WRAPPER_SCRIPT)[0] == "skip"
    kind, target = verify._resolve("x", {"verify_cmd": "x --check"}, util.PackageMethod.WRAPPER_SCRIPT)
    assert (kind, target) == ("cmd", "x --check")


# ---------------------------------------------------------------------------
# _deploy_check — the verdict per state and policy
# ---------------------------------------------------------------------------


def _managed(tmp_path, mechanism) -> deploy.Managed:
    return deploy.Managed(path=tmp_path / "dest", package="pkg", source="config/x", mechanism=mechanism)


@pytest.mark.parametrize(
    ("state", "passed"),
    [
        (deploy.State.CLEAN, True),
        (deploy.State.ABSENT, False),
        (deploy.State.STALE, False),
        (deploy.State.DIRTY, False),
        (deploy.State.UNKNOWN, False),
    ],
)
def test_deploy_check_managed_content_must_be_clean(tmp_path, state, passed):
    # Exactly the gap this check exists to catch: dest exists, but its content no longer matches
    # the source it was last deployed from (a redeploy never ran, or landed hand-edited content).
    ok, _ = verify._deploy_check(_managed(tmp_path, deploy.Mechanism.WRAPPER_SCRIPT), state)
    assert ok is passed


@pytest.mark.parametrize(
    ("state", "passed"),
    [
        (deploy.State.CLEAN, True),
        (deploy.State.ABSENT, False),
        (deploy.State.STALE, True),
        (deploy.State.DIRTY, True),
        (deploy.State.UNKNOWN, True),
    ],
)
def test_deploy_check_seeded_content_fails_only_when_absent(tmp_path, state, passed):
    # A config_files destination is the user's after first install — a customized copy must not
    # fail `inv setup`, or verify would cry wolf on every config they've ever touched.
    ok, _ = verify._deploy_check(_managed(tmp_path, deploy.Mechanism.CONFIG_FILE), state)
    assert ok is passed


def test_deploy_check_failure_message_points_at_deploy_status(tmp_path):
    ok, message = verify._deploy_check(_managed(tmp_path, deploy.Mechanism.SKILL), deploy.State.DIRTY)
    assert ok is False
    assert "inv deploy.status --name pkg" in message


# ---------------------------------------------------------------------------
# _all_checks — coverage through the deploy registry
# ---------------------------------------------------------------------------


def _stub_config(monkeypatch, packages: dict[str, util.PackageConfig]) -> None:
    monkeypatch.setattr(util, "load_config", lambda: {"packages": packages})
    monkeypatch.setattr(util, "enabled_packages", lambda: packages)
    monkeypatch.setattr(
        util,
        "packages_by_method",
        lambda method: {n: c for n, c in packages.items() if c.get("method") == method},
    )


def test_all_checks_covers_config_files_and_skills_without_duplicating_wrapper_scripts(tmp_path, monkeypatch):
    _stub_config(
        monkeypatch,
        {
            "agents-md": {
                "method": "wrapper-script",
                "dest": str(tmp_path / "AGENTS.md"),
                "content_file": "config/statusline-command.sh",
            },
            "wezterm": {
                "method": "archive",
                "config_files": [{"src": "config/wezterm.lua", "dst": str(tmp_path / "wezterm.lua")}],
            },
            "research-library": {
                "method": "skill",
                "skills": [{"source": "local", "path": "skills/research-library"}],
            },
        },
    )

    deploy_checks = [(name, target) for name, kind, target in verify._all_checks() if kind == "deploy"]

    assert deploy_checks.count(("agents-md", str(tmp_path / "AGENTS.md"))) == 1
    assert ("wezterm", str(tmp_path / "wezterm.lua")) in deploy_checks
    skill_targets = [target for name, target in deploy_checks if name == "research-library"]
    assert skill_targets
    assert skill_targets[0].endswith("skills/research-library")


def test_all_checks_wrapper_script_verify_false_still_skips(tmp_path, monkeypatch):
    # The registry knows every wrapper-script path, but verify = false must still win — which is
    # why wrapper-script paths come from _resolve, never from the registry sweep.
    _stub_config(
        monkeypatch,
        {
            "x": {
                "method": "wrapper-script",
                "dest": str(tmp_path / "x"),
                "content_file": "config/x",
                "verify": False,
            }
        },
    )

    kinds = {name: kind for name, kind, _ in verify._all_checks()}

    assert kinds == {"x": "skip"}


def test_classify_deploy_resolves_a_registry_path_end_to_end(tmp_path, monkeypatch):
    # A real deploy, then the verify-side lookup: the same classifier `inv deploy.status` uses.
    monkeypatch.setattr(deploy, "_REPO_ROOT", tmp_path)
    monkeypatch.setattr(deploy, "_MANIFEST", tmp_path / "state" / "deployed.json")
    monkeypatch.setattr(util, "DRY_RUN", False)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "x.sh").write_text("echo hi\n")
    dest = tmp_path / "x"
    _stub_config(
        monkeypatch,
        {"x": {"method": "wrapper-script", "dest": str(dest), "content_file": "config/x.sh"}},
    )

    m, state = verify._classify_deploy(str(dest))
    assert state == deploy.State.ABSENT
    deploy.deploy(m)
    assert verify._classify_deploy(str(dest))[1] == deploy.State.CLEAN
    dest.write_text("edited\n")
    assert verify._classify_deploy(str(dest))[1] == deploy.State.DIRTY


def test_classify_deploy_raises_for_a_path_outside_the_registry(tmp_path, monkeypatch):
    _stub_config(monkeypatch, {})

    with pytest.raises(RuntimeError, match="isn't in the deploy registry"):
        verify._classify_deploy(str(tmp_path / "nope"))


def _stub_mirror_package(monkeypatch, dest, mirror):
    """One enabled package declaring `mirror` as a copy of `dest`, which is what `_mirror_source`
    walks to answer "what should be here"."""
    monkeypatch.setattr(
        util,
        "enabled_packages",
        lambda: {"agents-md": {"dest": str(dest), "also_deploy_to": [str(mirror)]}},
    )


def test_mirror_check_passes_for_a_copy_holding_the_deployed_bytes(tmp_path, monkeypatch):
    dest = tmp_path / "AGENTS.md"
    dest.write_text("rules\n")
    mirror = tmp_path / "CLAUDE.md"
    mirror.write_text("rules\n")
    _stub_mirror_package(monkeypatch, dest, mirror)

    passed, _ = verify._mirror_check(str(mirror))

    assert passed


def test_mirror_check_fails_for_a_missing_file(tmp_path, monkeypatch):
    dest = tmp_path / "AGENTS.md"
    dest.write_text("rules\n")
    mirror = tmp_path / "CLAUDE.md"
    _stub_mirror_package(monkeypatch, dest, mirror)

    passed, message = verify._mirror_check(str(mirror))

    assert not passed
    assert "missing" in message


def test_mirror_check_fails_for_content_that_has_drifted(tmp_path, monkeypatch):
    """The failure the copy mechanism introduced, and the reason this check compares bytes: a
    mirror left behind by an older deploy is a real file at the right path, and an agent reading
    last week's rules looks exactly like an agent reading this week's."""
    dest = tmp_path / "AGENTS.md"
    dest.write_text("this week's rules\n")
    mirror = tmp_path / "CLAUDE.md"
    mirror.write_text("last week's rules\n")
    _stub_mirror_package(monkeypatch, dest, mirror)

    passed, message = verify._mirror_check(str(mirror))

    assert not passed
    assert "drifted" in message


def test_mirror_check_fails_for_a_leftover_symlink(tmp_path, monkeypatch):
    """A machine deployed before 2026-09-07 still has links at these paths. They resolve to the
    right bytes, so a content comparison alone would pass one — and the whole point of the change
    is that a link is not what should be there."""
    dest = tmp_path / "AGENTS.md"
    dest.write_text("rules\n")
    mirror = tmp_path / "CLAUDE.md"
    mirror.symlink_to(dest)
    _stub_mirror_package(monkeypatch, dest, mirror)

    passed, message = verify._mirror_check(str(mirror))

    assert not passed
    assert "still a symlink" in message


def test_mirror_check_fails_for_a_path_no_package_declares(tmp_path, monkeypatch):
    monkeypatch.setattr(util, "enabled_packages", lambda: {})

    passed, message = verify._mirror_check(str(tmp_path / "CLAUDE.md"))

    assert not passed
    assert "not declared as a mirror" in message


def test_mirror_checks_skip_an_agent_that_isnt_installed(tmp_path, monkeypatch):
    """A mirror into a directory that doesn't exist is correct, not a failure — that agent simply
    isn't on this machine, and the installer skips creating it for the same reason."""
    present = tmp_path / "installed"
    present.mkdir()
    packages = {
        "agents-md": {
            "also_deploy_to": [str(present / "CLAUDE.md"), str(tmp_path / "absent" / "AGENTS.md")],
        }
    }
    monkeypatch.setattr(util, "enabled_packages", lambda: packages)

    checks = verify._mirror_checks()

    assert [t for _, _, t in checks] == [str(present / "CLAUDE.md")]


def test_mirror_checks_never_skip_an_always_destination(tmp_path, monkeypatch):
    """`always = true` has no agent to be absent, so a missing file there is a real failure.

    The installer creates that parent rather than reading its absence as "not installed", so
    skipping the check would hide exactly the case the flag exists to make verifiable.
    """
    packages = {"agents-md": {"also_deploy_to": [{"path": str(tmp_path / "absent" / "AGENTS.md"), "always": True}]}}
    monkeypatch.setattr(util, "enabled_packages", lambda: packages)

    checks = verify._mirror_checks()

    assert [t for _, _, t in checks] == [str(tmp_path / "absent" / "AGENTS.md")]
