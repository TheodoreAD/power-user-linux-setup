"""Unit tests for tasks/util.py's pure helpers — ok_label, ensure_block_text/BlockStatus,
packages_by_method's enabled/tag-filtering logic (given an in-memory config, no file I/O), and the
sudo state machine with every probe stubbed out. See tests/README.md.
"""

import os
import pwd
import sys
import types
from pathlib import Path
from typing import override

import pytest
from invoke import Context, MockContext, Result, UnexpectedExit

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


@pytest.mark.parametrize(
    ("mode", "expected"), [(0o644, True), (0o600, False), (0o640, False)], ids=["0644", "0600", "0640"]
)
def test_readable_by_all_reads_the_other_bit(tmp_path, mode, expected):
    """0600 is the mode the old `cp`-based sudo_write left behind, and the one that must read as
    drift; 0640 is here so "readable by some" is not mistaken for "readable by all"."""
    path = tmp_path / "99-pulse"
    path.write_text("x")
    path.chmod(mode)

    assert util.readable_by_all(path) is expected


def test_readable_by_all_is_false_for_a_missing_file(tmp_path):
    assert util.readable_by_all(tmp_path / "never-created") is False


class _Recorder(Context):
    """Records commands; any containing a `fail` fragment exits 1, raising unless `warn` was given,
    as invoke's own runner does."""

    def __init__(self, fail: str | None = None) -> None:
        super().__init__()
        self.commands: list[str] = []
        self._fail: str | None = fail

    @override
    def run(self, command: str, **kwargs: object) -> Result:
        self.commands.append(command)
        result = Result(command=command, exited=1 if self._fail and self._fail in command else 0)
        if result.exited and not kwargs.get("warn"):
            raise UnexpectedExit(result)
        return result


def test_sudo_write_runs_one_sudo_alone_and_cleans_up_its_tempfile(monkeypatch):
    """Without a terminal sudo keys its cache on the parent PID, and only a lone command keeps
    that parent as this process — a shell operator makes bash fork and the `sudo -n` fails. See
    sudo_write's docstring for the measurement."""
    monkeypatch.setattr(util, "SUDO", "sudo -n")
    c = _Recorder()

    assert util.sudo_write(c, Path("/etc/example.conf"), "text\n") is True

    [command] = c.commands
    assert command.startswith("sudo -n install -m 0644 ")
    assert not any(op in command for op in ("&&", "||", ";", "|"))
    assert not Path(command.split()[-2]).exists(), "the tempfile is removed from Python, not by a chained rm"


def test_sudo_write_makes_the_parent_directory_as_a_separate_lone_command(monkeypatch):
    monkeypatch.setattr(util, "SUDO", "sudo -n")
    c = _Recorder()

    util.sudo_write(c, Path("/etc/docker/daemon.json"), "{}\n", mkdir=True)

    assert c.commands[0] == "sudo -n mkdir -p /etc/docker"
    assert c.commands[1].startswith("sudo -n install -m 0644 ")


def test_sudo_write_with_warn_reports_a_failure_instead_of_raising(monkeypatch):
    """apt's repo registration reports one repo and carries on, so it needs the answer, not a raise."""
    monkeypatch.setattr(util, "SUDO", "sudo -n")

    assert util.sudo_write(_Recorder(fail="install"), Path("/etc/x"), "t", warn=True) is False
    with pytest.raises(UnexpectedExit):
        util.sudo_write(_Recorder(fail="install"), Path("/etc/x"), "t")


def test_sudo_read_reads_a_readable_file_without_sudo(tmp_path):
    """Every file sudo_write installs is 0644, so this is the common case, and it keeps sudo out of
    a dry run, which has not authenticated."""
    path = tmp_path / "99-pulse"
    path.write_text("content\n")
    c = _Recorder()

    assert util.sudo_read(c, path) == "content\n"
    assert c.commands == []


def test_write_claude_settings_refuses_past_the_budget_and_leaves_the_file_alone(monkeypatch, tmp_path):
    # Claude Code rejects a settings file over 2 MiB whole, so an oversized write would lose every
    # setting in it, not just the rules that pushed it over.
    settings_file = tmp_path / "settings.json"
    settings_file.write_text('{"theme": "dark"}\n', encoding="utf-8")
    monkeypatch.setattr(util, "CLAUDE_SETTINGS", settings_file)
    monkeypatch.setattr(util, "CLAUDE_SETTINGS_BUDGET", 64)
    with pytest.raises(RuntimeError, match="over the 64-byte budget"):
        util.write_claude_settings({"permissions": {"allow": ["Bash(x *)"] * 10}})
    assert settings_file.read_text(encoding="utf-8") == '{"theme": "dark"}\n'
    assert not settings_file.with_suffix(".json.bak").exists()


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


def test_ensure_sudo_in_a_dry_run_asks_for_nothing_and_leaves_no_sudo_able_to_prompt(monkeypatch, fresh_sudo):
    """A dry run authenticates nothing. It used to leave SUDO as `sudo -A`, so every root read in
    one could raise a password dialog, or at a terminal stop at an invisible in-invoke prompt."""
    calls = _sudo_answers(monkeypatch, ok_flags=(), askpass="/home/u/.local/bin/askpass-zenity")
    monkeypatch.setattr(util, "run_interactive", lambda cmd, **kw: pytest.fail(f"asked for a password: {cmd}"))
    monkeypatch.setattr(util, "DRY_RUN", True)

    assert util.ensure_sudo() is True
    assert util.SUDO == "sudo -n"
    assert calls == [], "not even the probes: a dry run is not a reason to touch sudo's state"


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


def _raise_key_error(_name: str):
    raise KeyError(_name)


def _passwd_shell(monkeypatch, shell: str) -> None:
    monkeypatch.setattr(util, "current_user", lambda: "someone")
    monkeypatch.setattr(pwd, "getpwnam", lambda _name: types.SimpleNamespace(pw_shell=shell))


def test_login_shell_reads_the_registered_shell_not_the_inherited_one(monkeypatch):
    # $SHELL answers "what started the process that started me", which is a different question and
    # is wrong in exactly the case this check exists for.
    _passwd_shell(monkeypatch, "/bin/bash")
    monkeypatch.setenv("SHELL", "/usr/bin/zsh")
    assert util.login_shell() == "/bin/bash"
    assert util.login_shell_is_zsh() is False


def test_login_shell_is_zsh_matches_by_name_not_by_path(monkeypatch):
    # A machine can have an apt zsh at /usr/bin/zsh and another earlier on PATH; both count.
    _passwd_shell(monkeypatch, "/usr/local/bin/zsh")
    assert util.login_shell_is_zsh() is True


def test_login_shell_survives_a_user_with_no_passwd_entry(monkeypatch):
    # A plain `docker build` sets $HOME and no $USER; getpwnam("") raises rather than returning.
    monkeypatch.setattr(util, "current_user", lambda: "ghost")
    monkeypatch.setattr(pwd, "getpwnam", _raise_key_error)
    assert util.login_shell() == ""
    assert util.login_shell_is_zsh() is False


def _bus_context(stdout: str, ok: bool = True) -> MockContext:
    """A Context whose dbus-send answers with `stdout`. The command is matched loosely because the
    real one is a single long line and pinning it here would test the string, not the parse."""
    return MockContext(run=Result(stdout=stdout, exited=0 if ok else 1), repeat=True)


def test_secret_service_reports_a_store_that_answers(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(util, "session_bus_address", lambda: "unix:path=/run/user/1000/bus")
    monkeypatch.setattr(util, "command_exists", lambda _name: True)
    assert "answering" in util.secret_service_state(_bus_context("   boolean true\n"))


def test_secret_service_separates_installed_from_running(monkeypatch: pytest.MonkeyPatch):
    # The distinction that matters, and the reason this moved out of wsl.py: gnome-keyring on disk
    # with nothing holding the bus name is the normal state of a WSL distro after installing it,
    # and it is not the same as "no keyring" — proxy.py tells the two apart by this answer.
    monkeypatch.setattr(util, "session_bus_address", lambda: "unix:path=/run/user/1000/bus")
    monkeypatch.setattr(util, "command_exists", lambda _name: True)
    assert util.secret_service_state(_bus_context("   boolean false\n")) == "installed but not running/unlocked"


def test_secret_service_needs_a_bus_before_anything_can_answer(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(util, "session_bus_address", lambda: None)
    assert "no session bus" in util.secret_service_state(MockContext())


def test_secret_service_says_unknown_rather_than_guessing(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(util, "session_bus_address", lambda: "unix:path=/run/user/1000/bus")
    monkeypatch.setattr(util, "command_exists", lambda _name: False)
    assert "unknown" in util.secret_service_state(MockContext())


def test_session_bus_prefers_the_environment(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", "unix:path=/tmp/somewhere-else")
    assert util.session_bus_address() == "unix:path=/tmp/somewhere-else"


def test_login_shell_warning_is_silent_on_a_zsh_machine(monkeypatch):
    _passwd_shell(monkeypatch, "/usr/bin/zsh")
    assert util.login_shell_warning("SSL_CERT_FILE") is None


def test_login_shell_warning_names_both_the_shell_and_what_is_lost(monkeypatch):
    # The whole failure is silent, so the message has to carry the diagnosis: neither the shell in
    # use nor the exports that never arrived shows up anywhere else.
    _passwd_shell(monkeypatch, "/bin/bash")
    note = util.login_shell_warning("SSL_CERT_FILE and friends")

    assert note is not None
    assert "/bin/bash" in note
    assert "SSL_CERT_FILE and friends" in note
    assert "zsh.set-default-shell" in note


def test_login_shell_warning_still_warns_when_the_shell_is_unknown(monkeypatch):
    # A container with no passwd entry is not evidence that zsh is in place — the exports are just
    # as invisible, so the safe answer is the warning, not silence.
    monkeypatch.setattr(util, "current_user", lambda: "ghost")
    monkeypatch.setattr(pwd, "getpwnam", _raise_key_error)
    note = util.login_shell_warning("http_proxy")

    assert note is not None
    assert "unknown" in note


def _service_state(monkeypatch: pytest.MonkeyPatch, state: str) -> None:
    monkeypatch.setattr(util, "secret_service_state", lambda _c: state)


def test_keyring_remedy_says_unlock_when_a_store_is_already_answering(monkeypatch):
    # The case the old single message got exactly backwards: telling a machine that already has
    # gnome-keyring and dbus-user-session to install them is no help, and both are now declared
    # packages, so this is the state a WSL distro that ran setup lands in.
    _service_state(monkeypatch, "answering ✓")
    remedy = util.secret_store_remedy(MockContext())
    assert "not missing" in remedy
    assert "--unlock" in remedy
    assert "install" not in remedy


def test_keyring_remedy_asks_for_dbus_when_there_is_no_bus_at_all(monkeypatch):
    _service_state(monkeypatch, "no session bus, so nothing can answer")
    remedy = util.secret_store_remedy(MockContext())
    assert "dbus-user-session" in remedy
    assert "--unlock" not in remedy, "nothing can be unlocked on a bus that does not exist"


def test_keyring_remedy_covers_both_fixes_when_nothing_owns_the_bus_name(monkeypatch):
    # A bus with no owner for org.freedesktop.secrets cannot distinguish "not installed" from
    # "installed, never started" from the outside, so the message may not pick one.
    _service_state(monkeypatch, "installed but not running/unlocked")
    remedy = util.secret_store_remedy(MockContext())
    assert "gnome-keyring" in remedy
    assert "--unlock" in remedy


def test_keyring_remedy_does_not_guess_when_the_probe_could_not_answer(monkeypatch):
    _service_state(monkeypatch, "unknown (dbus-send not installed)")
    remedy = util.secret_store_remedy(MockContext())
    assert "could not tell" in remedy
    assert "dbus-send not installed" in remedy
