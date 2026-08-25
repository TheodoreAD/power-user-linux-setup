"""Unit tests for tasks/chrome.py's pure helpers — launcher-name parsing, `Local State` reading
(a real file under tmp_path, no Chrome required), and the `rewrite` text transform that does the
actual normalization. No task is invoked and nothing under ~ is touched. See tests/README.md.
"""

import json
from pathlib import Path

import pytest

from tasks.chrome import (
    Profiles,
    add_ozone_flag,
    autostart_disabled,
    chrome_starters,
    entry_exec,
    launches_chrome,
    parse_launcher,
    read_profiles,
    rewrite,
    strip_label,
)

LABELS = frozenset({"Main", "Work", "DoHu"})

GMAIL_MAIN = """\
[Desktop Entry]
Version=1.0
Terminal=false
Type=Application
Name=Gmail
Exec=/opt/google/chrome/google-chrome "--profile-directory=Profile 2" --app-id=fmgjjmm
Icon=chrome-fmgjjmm-Profile_2
NoDisplay=true
StartupWMClass=crx_fmgjjmm
"""

YOUTUBE_WITH_ACTIONS = """\
[Desktop Entry]
Name=YouTube
Exec=/opt/google/chrome/google-chrome "--profile-directory=Profile 2" --app-id=agimnki
NoDisplay=true
StartupWMClass=crx_agimnki
Actions=Search;

[Desktop Action Search]
Name=Search
Exec=/opt/google/chrome/google-chrome "--profile-directory=Profile 2" --app-id=agimnki "--app-launch-url-for-shortcuts-menu-item=https://www.youtube.com/results"
"""


# ---------------------------------------------------------------------------
# parse_launcher
# ---------------------------------------------------------------------------


def test_parse_launcher_splits_app_id_from_profile():
    launcher = parse_launcher(Path("chrome-fmgjjmmmlfnkbppncabfkddbjimcfncm-Profile_2.desktop"))
    assert launcher is not None
    assert launcher.app_id == "fmgjjmmmlfnkbppncabfkddbjimcfncm"
    assert launcher.profile_dir == "Profile 2"


def test_parse_launcher_handles_the_default_profile():
    launcher = parse_launcher(Path("chrome-aghbiah-Default.desktop"))
    assert launcher is not None
    assert launcher.profile_dir == "Default"


@pytest.mark.parametrize("name", ["google-chrome.desktop", "chrome-.desktop", "chrome-noprofile.desktop"])
def test_parse_launcher_rejects_non_pwa_filenames(name):
    assert parse_launcher(Path(name)) is None


# ---------------------------------------------------------------------------
# read_profiles
# ---------------------------------------------------------------------------


def test_read_profiles_extracts_names_and_last_used(tmp_path):
    state = tmp_path / "Local State"
    state.write_text(
        json.dumps(
            {
                "profile": {
                    "last_used": "Profile 2",
                    "info_cache": {
                        "Default": {"name": "Work"},
                        "Profile 2": {"name": "Main"},
                    },
                }
            }
        )
    )
    assert read_profiles(state) == Profiles(labels={"Default": "Work", "Profile 2": "Main"}, primary="Profile 2")


def test_read_profiles_returns_empty_when_chrome_is_not_installed(tmp_path):
    assert read_profiles(tmp_path / "absent") == Profiles(labels={}, primary=None)


@pytest.mark.parametrize("payload", ["[]", '{"profile": "wrong-shape"}', '{"profile": {"info_cache": 3}}'])
def test_read_profiles_tolerates_unexpected_shapes(tmp_path, payload):
    state = tmp_path / "Local State"
    state.write_text(payload)
    assert read_profiles(state).labels == {}


# ---------------------------------------------------------------------------
# strip_label / add_ozone_flag
# ---------------------------------------------------------------------------


def test_strip_label_removes_a_known_profile_suffix():
    assert strip_label("Gmail — Main", LABELS) == "Gmail"


def test_strip_label_leaves_an_unknown_suffix_alone():
    # An app whose real name contains an em dash must survive untouched.
    assert strip_label("Notes — Personal Edition", LABELS) == "Notes — Personal Edition"


def test_add_ozone_flag_inserts_after_the_binary():
    assert add_ozone_flag("/usr/bin/google-chrome-stable %U") == "/usr/bin/google-chrome-stable --ozone-platform=x11 %U"


def test_add_ozone_flag_is_idempotent():
    once = add_ozone_flag("/usr/bin/google-chrome-stable %U")
    assert add_ozone_flag(once) == once


def test_add_ozone_flag_handles_a_bare_binary():
    assert add_ozone_flag("/usr/bin/google-chrome-stable") == "/usr/bin/google-chrome-stable --ozone-platform=x11"


# ---------------------------------------------------------------------------
# rewrite
# ---------------------------------------------------------------------------


def test_rewrite_labels_the_entry_name():
    text, changes = rewrite(GMAIL_MAIN, label="Main", known_labels=LABELS, unhide=False, ozone=False)
    assert "Name=Gmail — Main\n" in text
    assert [c.field for c in changes] == ["Name"]


def test_rewrite_unhides_only_when_asked():
    hidden, _ = rewrite(GMAIL_MAIN, label="Main", known_labels=LABELS, unhide=False, ozone=False)
    assert "NoDisplay=true" in hidden

    shown, changes = rewrite(GMAIL_MAIN, label="Main", known_labels=LABELS, unhide=True, ozone=False)
    assert "NoDisplay" not in shown
    assert "NoDisplay" in [c.field for c in changes]


def test_rewrite_is_idempotent():
    once, _ = rewrite(GMAIL_MAIN, label="Main", known_labels=LABELS, unhide=True, ozone=True)
    twice, changes = rewrite(once, label="Main", known_labels=LABELS, unhide=True, ozone=True)
    assert twice == once
    assert changes == []


def test_rewrite_relabels_after_a_profile_rename():
    once, _ = rewrite(GMAIL_MAIN, label="Main", known_labels=LABELS, unhide=False, ozone=False)
    renamed, changes = rewrite(once, label="Work", known_labels=LABELS, unhide=False, ozone=False)
    assert "Name=Gmail — Work\n" in renamed
    assert "Gmail — Main" not in renamed
    assert [c.field for c in changes] == ["Name"]


def test_rewrite_leaves_desktop_action_names_alone():
    """The right-click shortcut labels are Name= lines too, in [Desktop Action ...] sections."""
    text, _ = rewrite(YOUTUBE_WITH_ACTIONS, label="Main", known_labels=LABELS, unhide=True, ozone=False)
    assert "Name=YouTube — Main\n" in text
    assert "Name=Search\n" in text
    assert "Name=Search — Main" not in text


def test_rewrite_flags_every_exec_including_desktop_actions():
    text, changes = rewrite(YOUTUBE_WITH_ACTIONS, label="Main", known_labels=LABELS, unhide=False, ozone=True)
    assert text.count("--ozone-platform=x11") == 2
    assert [c.field for c in changes].count("Exec") == 2


def test_rewrite_reports_no_changes_when_ozone_is_not_wanted():
    _, changes = rewrite(YOUTUBE_WITH_ACTIONS, label="Main", known_labels=LABELS, unhide=False, ozone=False)
    assert [c.field for c in changes] == ["Name"]


# ---------------------------------------------------------------------------
# autostart drift — which entries can start Chrome, and whether they carry the flag
# ---------------------------------------------------------------------------

FLAGGED_STARTER = """\
[Desktop Entry]
Type=Application
Name=Google Chrome (XWayland pre-start)
Exec=/usr/bin/google-chrome-stable --ozone-platform=x11 %U
"""

PWA_STARTER = """\
[Desktop Entry]
Type=Application
Name=WhatsApp Web
Exec=/opt/google/chrome/google-chrome "--profile-directory=Profile 2" --app-id=hnpfjng
"""

NOT_CHROME = """\
[Desktop Entry]
Type=Application
Name=Spotify
Exec=/snap/bin/spotify %U
"""


def _autostart(tmp_path: Path, name: str, text: str) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_entry_exec_ignores_desktop_action_exec_lines():
    """Only the [Desktop Entry] Exec is what autostart runs — an action's Exec is a right-click item."""
    assert entry_exec(YOUTUBE_WITH_ACTIONS) == (
        '/opt/google/chrome/google-chrome "--profile-directory=Profile 2" --app-id=agimnki'
    )


def test_entry_exec_returns_none_when_there_is_no_exec():
    assert entry_exec("[Desktop Entry]\nName=Broken\n") is None


@pytest.mark.parametrize(
    "exec_value, expected",
    [
        ("/usr/bin/google-chrome-stable --ozone-platform=x11 %U", True),
        ("/opt/google/chrome/google-chrome --app-id=hnpfjng", True),
        ("env BAMF_DESKTOP_FILE_HINT=/x /usr/bin/google-chrome-stable", True),
        ("/snap/bin/spotify %U", False),
        ("", False),
    ],
)
def test_launches_chrome(exec_value: str, expected: bool):
    assert launches_chrome(exec_value) is expected


@pytest.mark.parametrize(
    "line",
    ["Hidden=true", "X-GNOME-Autostart-enabled=false"],
)
def test_autostart_disabled_recognizes_both_mechanisms(line: str):
    assert autostart_disabled(f"[Desktop Entry]\nExec=/usr/bin/google-chrome-stable\n{line}\n")


def test_autostart_disabled_is_false_for_a_live_entry():
    assert not autostart_disabled(FLAGGED_STARTER)


def test_chrome_starters_finds_only_chrome_entries(tmp_path: Path):
    _autostart(tmp_path, "00-google-chrome-x11.desktop", FLAGGED_STARTER)
    _autostart(tmp_path, "spotify.desktop", NOT_CHROME)

    starters = chrome_starters((tmp_path,))

    assert [s.path.name for s in starters] == ["00-google-chrome-x11.desktop"]
    assert starters[0].has_flag


def test_chrome_starters_flags_an_unflagged_pwa_entry(tmp_path: Path):
    """The drift case: a PWA set to run at login can beat the flagged entry and claim Wayland."""
    _autostart(tmp_path, "00-google-chrome-x11.desktop", FLAGGED_STARTER)
    _autostart(tmp_path, "chrome-hnpfjng-Profile_2.desktop", PWA_STARTER)

    starters = chrome_starters((tmp_path,))

    assert {s.path.name: s.has_flag for s in starters} == {
        "00-google-chrome-x11.desktop": True,
        "chrome-hnpfjng-Profile_2.desktop": False,
    }


def test_chrome_starters_skips_a_disabled_entry(tmp_path: Path):
    hidden = PWA_STARTER.replace("[Desktop Entry]\n", "[Desktop Entry]\nHidden=true\n")
    _autostart(tmp_path, "google-chrome.desktop", hidden)

    assert chrome_starters((tmp_path,)) == []


def test_chrome_starters_lets_a_user_entry_mask_the_system_one(tmp_path: Path):
    """XDG masking is by filename: a user entry replaces the system one rather than adding to it."""
    user, system = tmp_path / "user", tmp_path / "system"
    _autostart(user, "google-chrome.desktop", FLAGGED_STARTER)
    _autostart(system, "google-chrome.desktop", PWA_STARTER)

    starters = chrome_starters((user, system))

    assert len(starters) == 1
    assert starters[0].has_flag


def test_chrome_starters_tolerates_a_missing_directory(tmp_path: Path):
    assert chrome_starters((tmp_path / "does-not-exist",)) == []
