"""Unit tests for tasks/util.py's pure helpers — ok_label, ensure_block_text/BlockStatus,
packages_by_method's enabled/tag-filtering logic (given an in-memory config, no file I/O), and the
sudo state machine with every probe stubbed out. See tests/README.md.
"""

import os
import sys

import pytest

from tasks import util


def test_ok_label():
    assert util.ok_label(True) == "ok"
    assert util.ok_label(False) == "MISSING"


def test_block_status_formats_as_plain_value_not_enum_repr():
    # (str, Enum) members format as "ClassName.MEMBER" in an f-string unless __str__ is
    # overridden — every call site here prints the status word directly, so this must hold.
    assert f"{util.BlockStatus.ADDED}" == "added"
    assert str(util.BlockStatus.UPDATED) == "updated"


def test_ensure_block_text_adds_new_block():
    text, status = util.ensure_block_text("existing content\n", "myblock", "new stuff")
    assert status == util.BlockStatus.ADDED
    assert "new stuff" in text
    assert text.startswith("existing content\n")


def test_ensure_block_text_is_idempotent_when_unchanged():
    first, _ = util.ensure_block_text("", "myblock", "content")
    second, status = util.ensure_block_text(first, "myblock", "content")
    assert status == util.BlockStatus.OK
    assert second == first


def test_ensure_block_text_updates_changed_block():
    first, _ = util.ensure_block_text("", "myblock", "old content")
    updated, status = util.ensure_block_text(first, "myblock", "new content")
    assert status == util.BlockStatus.UPDATED
    assert "old content" not in updated
    assert "new content" in updated


def test_ensure_block_text_html_style_uses_html_comment_markers():
    text, status = util.ensure_block_text("", "myblock", "content", style=util.MarkerStyle.HTML)
    assert status == util.BlockStatus.ADDED
    assert "<!-- PULSE::myblock -->" in text
    assert "<!-- /PULSE::myblock -->" in text
    assert "#" not in text


def test_ensure_block_text_html_style_blank_lines_around_content():
    # Markdown needs a blank line between adjacent block-level elements (marker <-> content) to
    # match dprint's own formatting — otherwise `inv quality.fix` would perpetually "fix" what
    # render-docs just wrote, and the two would never agree on a stable, idempotent output.
    text, _ = util.ensure_block_text("", "myblock", "content", style=util.MarkerStyle.HTML)
    assert "<!-- PULSE::myblock -->\n\ncontent\n\n<!-- /PULSE::myblock -->" in text


def test_ensure_block_text_html_style_is_idempotent_when_unchanged():
    first, _ = util.ensure_block_text("", "myblock", "content", style=util.MarkerStyle.HTML)
    second, status = util.ensure_block_text(first, "myblock", "content", style=util.MarkerStyle.HTML)
    assert status == util.BlockStatus.OK
    assert second == first


def test_markdown_table_pads_columns_to_the_widest_cell():
    # The padding is what makes a generated table a fixed point of dprint's own formatter; an
    # unpadded table would be re-padded by `inv quality.fix` and rewritten by the next render.
    table = util.markdown_table(("A", "Bee"), [("longer", "x")])
    assert table == "| A      | Bee |\n| ------ | --- |\n| longer | x   |"


def test_markdown_table_escapes_pipes_in_cells():
    # An unescaped `|` opens a column that isn't there, silently shifting every later cell.
    table = util.markdown_table(("Cmd",), [("a | b",)])
    assert "a \\| b" in table
    assert table.splitlines()[-1].count("|") == 3  # the two delimiters plus the escaped one


def test_markdown_table_handles_no_rows():
    assert util.markdown_table(("A", "B"), []) == "| A | B |\n| - | - |"


def test_remove_block_text_takes_out_only_the_named_block():
    text, _ = util.ensure_block_text("hand-written line\n", "mine", "exported=1")
    text, _ = util.ensure_block_text(text, "theirs", "other=2")

    result, removed = util.remove_block_text(text, "mine")

    assert removed is True
    assert "exported=1" not in result
    assert "other=2" in result
    assert result.startswith("hand-written line\n")


def test_remove_block_text_reports_nothing_to_do_when_the_block_is_absent():
    result, removed = util.remove_block_text("just a file\n", "never-written")
    assert (result, removed) == ("just a file\n", False)


def test_remove_block_text_leaves_no_widening_gap_when_applied_repeatedly():
    """add → remove → add → remove has to converge, or a dotfile grows blank lines every run."""
    base = "hand-written line\n"
    text, _ = util.ensure_block_text(base, "mine", "exported=1")
    once, _ = util.remove_block_text(text, "mine")
    text, _ = util.ensure_block_text(once, "mine", "exported=1")
    twice, _ = util.remove_block_text(text, "mine")

    assert once == twice == base


def test_remove_block_writes_only_when_the_block_was_there(tmp_path):
    path = tmp_path / ".zshenv"
    path.write_text(util.ensure_block_text("", "mine", "exported=1")[0])

    assert util.remove_block(path, "mine") is True
    assert "exported=1" not in path.read_text()
    assert util.remove_block(path, "mine") is False


def test_remove_block_on_a_missing_file_is_not_an_error(tmp_path):
    assert util.remove_block(tmp_path / "never-created", "mine") is False


def test_packages_by_method_filters_by_method_and_enabled(monkeypatch):
    monkeypatch.setattr(
        util,
        "load_config",
        lambda: {
            "packages": {
                "ripgrep": {"method": "apt"},
                "fzf": {"method": "apt", "enabled": False},
                "docker": {"method": "apt-repo"},
            }
        },
    )
    monkeypatch.setattr(util, "_excluded_tags", set)
    monkeypatch.setattr(util, "load_overrides", dict)

    result = util.packages_by_method(util.PackageMethod.APT)

    assert set(result) == {"ripgrep"}


def test_packages_by_method_filters_by_excluded_tags(monkeypatch):
    monkeypatch.setattr(
        util,
        "load_config",
        lambda: {
            "packages": {
                "ripgrep": {"method": "apt", "tags": ["cli"]},
                "steam": {"method": "apt", "tags": ["gui"]},
            }
        },
    )
    monkeypatch.setattr(util, "_excluded_tags", lambda: {"gui"})
    monkeypatch.setattr(util, "load_overrides", dict)

    result = util.packages_by_method(util.PackageMethod.APT)

    assert set(result) == {"ripgrep"}


def _config_with_disabled_workaround():
    return {
        "packages": {
            "ripgrep": {"method": "apt", "tags": ["cli"]},
            "chrome-x11": {"method": "wrapper-script", "enabled": False, "tags": ["gui"]},
        }
    }


def test_machine_local_override_enables_a_package_disabled_in_setup_toml(monkeypatch):
    monkeypatch.setattr(util, "load_config", _config_with_disabled_workaround)
    monkeypatch.setattr(util, "_excluded_tags", set)
    monkeypatch.setattr(util, "load_overrides", lambda: {"chrome-x11": True})

    assert set(util.enabled_packages()) == {"ripgrep", "chrome-x11"}


def test_machine_local_override_can_also_disable_a_default_on_package(monkeypatch):
    monkeypatch.setattr(util, "load_config", _config_with_disabled_workaround)
    monkeypatch.setattr(util, "_excluded_tags", set)
    monkeypatch.setattr(util, "load_overrides", lambda: {"ripgrep": False})

    assert set(util.enabled_packages()) == set()


def test_excluded_tags_beat_a_machine_local_override(monkeypatch):
    # Capability beats intent: a machine can ask for a gui package, but a container that excluded
    # `gui` genuinely cannot run it, so the environment stays authoritative.
    monkeypatch.setattr(util, "load_config", _config_with_disabled_workaround)
    monkeypatch.setattr(util, "_excluded_tags", lambda: {"gui"})
    monkeypatch.setattr(util, "load_overrides", lambda: {"chrome-x11": True})

    assert set(util.enabled_packages()) == {"ripgrep"}


def test_load_overrides_reads_enabled_flips_and_skips_unknown_packages(monkeypatch, tmp_path, capsys):
    overrides = tmp_path / "overrides.toml"
    overrides.write_text(
        "[packages.chrome-x11]\nenabled = true\n"
        "[packages.ripgrep]\ndescription = 'no enabled key, so no opinion'\n"
        "[packages.typo-not-in-setup-toml]\nenabled = true\n"
    )
    monkeypatch.setattr(util, "OVERRIDES_PATH", overrides)
    monkeypatch.setattr(util, "load_config", _config_with_disabled_workaround)
    util.load_overrides.cache_clear()

    assert util.load_overrides() == {"chrome-x11": True}
    assert "typo-not-in-setup-toml" in capsys.readouterr().out
    util.load_overrides.cache_clear()


def test_load_overrides_is_empty_when_the_file_does_not_exist(monkeypatch, tmp_path):
    monkeypatch.setattr(util, "OVERRIDES_PATH", tmp_path / "absent.toml")
    util.load_overrides.cache_clear()

    assert util.load_overrides() == {}
    util.load_overrides.cache_clear()


# --- sudo: the "nothing may prompt from inside c.run" invariant --------------
#
# The failure this guards against is not hypothetical: `c.run("sudo -v", pty=True)` hangs forever
# on Python 3.14 (invoke can't forward stdin — pyinvoke/invoke#1070) and races sudo for the
# keystrokes on every older one, printing the password in plain text when it wins. See
# util.ensure_sudo's header and plans/2026-08-31-wsl-and-container-first-run-experience.md.


@pytest.fixture
def fresh_sudo(monkeypatch):
    """Reset the module-level "already authenticated" state around each test."""
    monkeypatch.setattr(util, "_sudo_ready", False)
    monkeypatch.setattr(util, "_sudo_keepalive", None)
    monkeypatch.setattr(util, "SUDO", "sudo")
    monkeypatch.setattr(util, "DRY_RUN", False)


def _sudo_answers(monkeypatch, *, root=False, ok_flags=(), askpass=None, tty=True):
    """Stand in for the machine: which `sudo` probes succeed, and what's available to ask with."""
    calls: list[list[str]] = []

    def fake_ok(*args: str) -> bool:
        calls.append(list(args))
        return tuple(args) in ok_flags

    monkeypatch.setattr(util, "_sudo_ok", fake_ok)
    monkeypatch.setattr(os, "geteuid", lambda: 0 if root else 1000)
    monkeypatch.setattr(util, "command_exists", lambda name: name == "sudo")
    monkeypatch.setattr(util, "_usable_askpass", lambda: askpass)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: tty)
    return calls


def test_sudo_state_separates_a_nopasswd_rule_from_a_warm_cache(monkeypatch, fresh_sudo):
    _sudo_answers(monkeypatch, ok_flags={("-n", "-k", "true"), ("-n", "true")})
    assert util.sudo_state().passwordless is True

    _sudo_answers(monkeypatch, ok_flags={("-n", "true")})
    state = util.sudo_state()
    assert (state.passwordless, state.cached, state.ready) == (False, True, True)


def test_ensure_sudo_authenticates_outside_invoke_and_then_forbids_prompting(monkeypatch, fresh_sudo):
    _sudo_answers(monkeypatch, ok_flags=())
    ran: list[list[str]] = []
    monkeypatch.setattr(util, "run_interactive", lambda cmd, **kw: ran.append(list(cmd)) or 0)

    assert util.ensure_sudo("a test") is True
    assert ran == [["sudo", "-v"]], "the password must be collected by sudo itself, not through invoke"
    assert util.SUDO == "sudo -n", "every later c.run must be unable to prompt"


def test_ensure_sudo_prefers_a_usable_askpass_over_the_terminal(monkeypatch, fresh_sudo):
    _sudo_answers(monkeypatch, ok_flags=(), askpass="/home/u/.local/bin/askpass-zenity")
    ran: list[list[str]] = []
    monkeypatch.setattr(util, "run_interactive", lambda cmd, **kw: ran.append(list(cmd)) or 0)

    util.ensure_sudo()
    assert ran == [["sudo", "-A", "-v"]]


def test_ensure_sudo_needs_nothing_when_already_root(monkeypatch, fresh_sudo):
    _sudo_answers(monkeypatch, root=True)
    monkeypatch.setattr(util, "run_interactive", lambda cmd, **kw: pytest.fail(f"asked for a password: {cmd}"))

    assert util.ensure_sudo() is True
    assert util.SUDO == "", "as root there is nothing to prefix, and sudo may not even be installed"


def test_ensure_sudo_refuses_early_when_it_cannot_ask_at_all(monkeypatch, fresh_sudo):
    """A container's postCreateCommand with a password-protected user: better to stop here, with
    the three ways out, than at an invisible prompt somewhere inside an apt run."""
    _sudo_answers(monkeypatch, ok_flags=(), askpass=None, tty=False)
    monkeypatch.setattr(util, "run_interactive", lambda cmd, **kw: pytest.fail("should not have tried to ask"))

    with pytest.raises(RuntimeError, match="no terminal to ask on"):
        util.ensure_sudo()


def test_ensure_sudo_is_idempotent(monkeypatch, fresh_sudo):
    _sudo_answers(monkeypatch, ok_flags=())
    ran: list[list[str]] = []
    monkeypatch.setattr(util, "run_interactive", lambda cmd, **kw: ran.append(list(cmd)) or 0)

    util.ensure_sudo()
    util.ensure_sudo()
    assert len(ran) == 1


def test_apt_command_can_never_stop_on_a_question(monkeypatch):
    monkeypatch.setattr(util, "SUDO", "sudo -n")
    command = util.apt_command("install -y tzdata")
    assert command.startswith("sudo -n env DEBIAN_FRONTEND=noninteractive")
    assert "--force-confold" in command  # a modified conffile must not prompt either
    assert command.endswith("install -y tzdata")


def test_apt_command_as_root_has_no_stray_sudo(monkeypatch):
    monkeypatch.setattr(util, "SUDO", "")
    assert util.apt_command("update").startswith("env DEBIAN_FRONTEND=noninteractive")
