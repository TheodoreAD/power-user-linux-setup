# Locale

Language and formats: what PULSE sets, why, and how to change it.

## Setup

```shell
inv system.set-locale
```

Writes `/etc/locale.conf` through `localectl` (systemd-integrated, persists across reboots),
idempotent, and also runs as part of `inv setup`. It sets **three** variables and leaves every other
one alone:

| variable     | value         | why                                                    |
| ------------ | ------------- | ------------------------------------------------------ |
| `LANG`       | `en_US.UTF-8` | English messages, and a sane UTF-8 base for everything |
| `LC_TIME`    | `en_DK.UTF-8` | English weekday/month names, 24-hour clock, ISO dates  |
| `LC_NUMERIC` | `C.UTF-8`     | dot-decimal, so `awk`/`printf` emit `1.50` not `1,50`  |

**The result is a mixed locale, deliberately.** A machine wants English formatting for anything a
person or a script reads, and its own regional facts for currency, paper size and measurement units.
No single locale expresses that, which is why an ordinary "Language: English, Region: elsewhere"
install already produces a mix. `LC_MONETARY`, `LC_PAPER`, `LC_MEASUREMENT`, `LC_ADDRESS`,
`LC_NAME`, `LC_TELEPHONE` and `LC_IDENTIFICATION` are read back and passed through untouched.

### Why `en_DK` for time

Measured across every candidate installed on a real machine — one `date` call each:

| locale        | `%x` date    | `%X` time     | `%a` | decimal |
| ------------- | ------------ | ------------- | ---- | ------- |
| `C.utf8`      | `03/04/26`   | `14:05:00`    | Wed  | `1.50`  |
| `en_US.UTF-8` | `03/04/2026` | `02:05:00 PM` | Wed  | `1.50`  |
| `en_GB.utf8`  | `04/03/26`   | `14:05:00`    | Wed  | `1.50`  |
| `en_CA.utf8`  | `2026-03-04` | `02:05:00 PM` | Wed  | `1.50`  |
| `en_DK.utf8`  | `2026-03-04` | `14:05:00`    | Wed  | `1,50`  |
| `ro_RO.UTF-8` | `04.03.2026` | `14:05:00`    | Mi   | `1,50`  |

`en_DK.UTF-8` is the only one hitting English names, a 24-hour clock and `YYYY-MM-DD` at once, and
its `%c` is full ISO-8601. "Canada-like `yyyy-mm-dd`" resolves here rather than to `en_CA`, which
gets the date right and the clock wrong.

`LC_NUMERIC` is set separately because **`en_DK` is comma-decimal**, like the European locale it is.
Setting `LC_TIME` alone would fix weekdays, clock and dates while leaving `awk`/`printf` emitting
`1,50` — half the problem, silently.

!!! warning

    `en_US` is the wrong "obvious English" choice for `LC_TIME`: `locale first_weekday` is 2 (Monday)
    under `en_DK` and 1 (Sunday) under `en_US`, so it silently flips the first day of the week in the
    GNOME calendar. Easy to notice and hard to attribute.

## Verify

```shell
locale
```

`LANG=en_US.UTF-8`, `LC_TIME=en_DK.UTF-8`, `LC_NUMERIC=C.UTF-8`, and the regional categories on
whatever your install chose. **A logout is enough; a reboot is not needed** — the systemd user
session carries the full set (`systemctl --user show-environment`) and re-reads `/etc/locale.conf`
at login. Shells and applications already running keep the old values until restarted.

The GNOME panel clock does **not** follow `LC_TIME` for 12h-vs-24h — that is
`org.gnome.desktop.interface clock-format`, independent of the locale. What the locale drives in the
panel and calendar is weekday and month _names_.

## Changing it

The task takes all three as parameters, so a one-off is:

```shell
inv system.set-locale --lc-time=en_GB.UTF-8 --lc-numeric=en_US.UTF-8
```

That is not persistent: the next `inv setup` applies the defaults again. Making the choice stick is
an open design question, tracked with the machine-local overrides mechanism — nobody has needed it
yet, and the values above are the ones this machine wanted.

## Pitfalls

- **Do not set `LC_ALL`** — it overrides every individual `LC_*` category with no escape hatch,
  which would defeat exactly the split above.
- **Do not set `LANG` to `C` or `POSIX`** — Python throws Unicode errors, and git and compiler
  output may be garbled. This is not in tension with `LC_NUMERIC=C.UTF-8`: one category asking for
  dot-decimal is not the same as a whole session with no locale, and `C.UTF-8` is UTF-8 either way.
  (`C` alone is not in `localectl list-locales`; the accepted spelling is `C.UTF-8`.)
- **Do not `export LANG=...` in a shell profile** — session-only, and it does not survive a reboot.
- **Do not hand-edit `/etc/locale.conf`** — `localectl set-locale` replaces the whole configuration
  rather than merging into it, so anything not passed on the command line is dropped. That is why
  the task reads the current set back and passes all of it.

## See also

- [How it works](configuration.md) — the setup phase this runs in
- [Quick start](index.md) — where `inv system.set-locale` sits in a first run
