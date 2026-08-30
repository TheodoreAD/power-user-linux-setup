"""Unit tests for tasks/system.py's pure helpers.

`parse_system_locale` is the part that makes `set_locale` safe: localed takes the whole locale
configuration, so a `set-locale LANG=…` naming only some variables drops the rest. The task reads
the current set back and passes it through, and that read is what these cover. See tests/README.md.
"""

from tasks import system

# Real `localectl status` output from this machine, before the 2026-08-30 locale change — the
# regional variables below are exactly the ones a partial set-locale would have silently dropped.
_STATUS = """\
   System Locale: LANG=en_US.UTF-8
                  LC_NUMERIC=ro_RO.UTF-8
                  LC_TIME=ro_RO.UTF-8
                  LC_MONETARY=ro_RO.UTF-8
                  LC_MEASUREMENT=ro_RO.UTF-8
       VC Keymap: (unset)
      X11 Layout: us,ro
       X11 Model: pc105
"""


def test_parse_system_locale_reads_the_whole_block():
    assert system.parse_system_locale(_STATUS) == {
        "LANG": "en_US.UTF-8",
        "LC_NUMERIC": "ro_RO.UTF-8",
        "LC_TIME": "ro_RO.UTF-8",
        "LC_MONETARY": "ro_RO.UTF-8",
        "LC_MEASUREMENT": "ro_RO.UTF-8",
    }


def test_parse_system_locale_stops_at_the_next_field():
    """The block is delimited by indentation, so a later `Key: value` line must not be swallowed —
    `X11 Layout: us,ro` has no `=` but `VC Keymap: (unset)` sits between it and the locales."""
    parsed = system.parse_system_locale(_STATUS)
    assert not any(k.startswith(("VC", "X11")) for k in parsed)


def test_parse_system_locale_is_empty_when_there_is_no_block():
    assert system.parse_system_locale("   VC Keymap: (unset)\n") == {}


def test_parse_system_locale_handles_a_single_inline_entry():
    assert system.parse_system_locale("   System Locale: LANG=C.UTF-8\n") == {"LANG": "C.UTF-8"}
