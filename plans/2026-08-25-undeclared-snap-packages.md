---
status: idea
updated: 2026-08-25
---

# Two snaps installed on this machine and declared nowhere

## Context

`snap list` on this machine shows two packages that appear nowhere in `setup.toml`:

```
duf-utility   v0.6.0    1     latest/stable   muesli
mdless        1.0.33    333   latest/stable   arub-islander
```

Both were hand-installed at some point and are invisible to the next machine — exactly the drift
this repo exists to prevent. (Every other snap present is either a Canonical base/runtime snap or
Ubuntu's own preinstalled `firefox`/`thunderbird`/`snap-store`, plus `spotify` and `kubectl`, which
are separate questions.)

Surfaced while evaluating WhatsApp clients, which is otherwise unrelated and was abandoned.

**Neither needs a new `snap` install method.** That was the initial assumption and it's wrong:

- **duf** ships a `.deb` on GitHub releases (`duf_0.9.1_linux_amd64.deb`, muesli/duf). That's a
  straight `deb-github` entry with the same shape as the existing `[packages.dive]` and
  `[packages.hyperfine]`. The installed snap is also stale — v0.6.0 against upstream v0.9.1.
- **mdless**'s snap is a third-party repack: publisher `arub-islander`, not upstream (ttscoff).
  Upstream distributes it as a Ruby gem, and this repo has no ruby-gem method and no reason to grow
  one for a single markdown pager.

So a `snap` method would be built to serve zero packages that actually need it. Dropping that idea;
if a genuinely snap-only tool ever comes up, the design notes are in this file's history.

## Open questions

[NEEDS CLARIFICATION: Is `mdless` still wanted at all? `[packages.bat]` is already declared and
renders markdown with syntax highlighting in the terminal. If mdless earns its place regardless, the
choice is between a third-party snap repack of someone else's tool and `glow` (charmbracelet), which
does the same job, is actively maintained, and ships a `.deb` on GitHub releases — i.e. fits
`deb-github` cleanly. Leaning: replace with `glow` if a real markdown pager is wanted, otherwise
drop it and let `bat` cover the case.]

[NEEDS CLARIFICATION: What happens to the installed snaps once the replacements are declared —
`snap remove duf-utility` as part of the same change, or left in place? Leaving them means two
copies of `duf` on `PATH` with `/snap/bin` ordering deciding which wins, and the snap is three minor
versions behind. Leaning: remove, but that's a live-machine mutation to run deliberately rather than
fold into an install task.]

[NEEDS CLARIFICATION: Are `spotify` and `kubectl` in the same boat? Both are snaps, `kubectl` is
`classic` confinement, and neither was checked against `setup.toml` during this pass. If they're
also undeclared, the same triage applies and this plan should cover all four rather than two.]

## Recommended direction

1. Audit the remaining non-Canonical snaps (`spotify`, `kubectl`) against `setup.toml` first, so
   this is one pass over the real set rather than two.
2. Add `[packages.duf]` as `method = "deb-github"`, `repo = "muesli/duf"`,
   `asset = "duf_{version}_linux_amd64.deb"`, `check_cmd = "duf"` — mirroring `[packages.dive]`.
3. Decide `mdless` per the open question above; most likely drop it, second-most-likely replace with
   `glow` via `deb-github`.
4. Remove the superseded snaps by hand once their replacements are installed and verified.
