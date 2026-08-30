---
status: idea
updated: 2026-08-30
---

# `uv run` deletes the project venv, and `~/AGENTS.md` says it layers over it

Filed from a `repo-tasks` session, 2026-08-30, after paying for it. This is a correction to a rule
that repo owns, not a new one.

## What the rule currently says

`~/AGENTS.md`, "Reading a command's result" (rationale in `contributing/global-agents-md.md` under
the same heading):

> Same shape when probing whether a dependency is **absent**: `uv run --with …` layers an ephemeral
> overlay _over_ the active environment, so from a directory with a venv active the probe measures a
> machine that has the package — and it passes, which is the answer you were hoping for.

The failure it describes is real and the prescribed form
(`env -u VIRTUAL_ENV -u PYTHONPATH uv run --no-project --python <ver> --with <pkg> …`) is correct.
**The stated mechanism is what is wrong**, and it understates the risk in a way that matters: a
reader who takes "layers an overlay" at face value concludes the existing venv survives. It does not
always.

## What actually happens

`uv run` in a project directory resolves the interpreter, and when the result differs from the
`.venv` already sitting there it **silently removes and recreates the project environment** before
running anything. It is not `--with` (a bare `uv run` resolves the same way), and it is not the
package being installed.

**The thing doing the differing is this repo's own configuration.** `~/.zshenv:13` exports
`UV_PYTHON="3.14"`, machine-wide, for every shell. uv treats that as an **explicit interpreter
request** — `uv venv -v` reports `Using Python request 3.14 from explicit request` — so every uv
invocation on this machine asks for 3.14 no matter what the project declares.

Isolated in a throwaway project 2026-08-30, `requires-python = ">=3.11"`, no dependencies:

| venv before | `.python-version` | `UV_PYTHON` | `uv run --with cowsay …`                   |
| ----------- | ----------------- | ----------- | ------------------------------------------ |
| 3.13.13     | absent            | `3.14`      | **destroyed**, recreated at 3.14.5         |
| 3.14.5      | absent            | `3.14`      | nothing printed; venv untouched            |
| 3.13.13     | absent            | `3.14`      | `--python 3.13` passed explicitly → intact |
| 3.11.15     | `3.11`            | `3.14`      | **destroyed**, recreated at 3.14.5         |
| 3.11.15     | `3.11`            | unset       | nothing printed; venv **stays 3.11.15**    |

The last two rows are the ones that matter, and they are why an earlier draft of this plan was
wrong. It blamed "uv's own default choice"; there is no default in play. `UV_PYTHON` outranks
`.python-version`, so the obvious fix — derive `.python-version` from `pyproject.toml`'s
`requires-python`, which is already the source of truth for `python_floor()` and for the shipped
`pyrightconfig.json`'s `pythonVersion` — is **inert on this machine** while that export stands.

Every repo here whose `requires-python` floor is below 3.14 is exposed: its venv is one bare
`uv sync` or `uv run` away from being silently rebuilt on the wrong interpreter. `repo-tasks` was
found in exactly that state — `inv venv.check` reported
`.venv is on Python 3.14, but this project
declares 3.11`, and `inv venv.recreate` fixed it only
because it passes `--python 3.11` explicitly.

[PITFALL: this cost a real dev environment before it was isolated. A `uv run --with deptry` in
`repo-tasks` — measuring a tool that is deliberately not a dependency — removed and recreated that
repo's `.venv`. `uv sync --all-groups` restored it and the gate came back green, so the damage was
recoverable and, more to the point, **invisible in the command's own output** unless you read the
two lines above the tool's. On a machine running parallel sessions the window between destruction
and restore is a broken environment for every other session sharing the tree.]

## What the correction should say

Two things the current wording does not:

1. **The consequence is destruction, not just contamination.** "Layers an overlay" is true only when
   the interpreter uv resolves already matches the venv's — which on this machine means only when
   the venv is on 3.14.
2. **`--no-project` is the part of the prescribed form that does the work**, not `-u VIRTUAL_ENV`.
   The environment-stripping addresses the contamination half; `--no-project` is what keeps uv away
   from the project environment it would otherwise rebuild.

## Open questions

[NEEDS CLARIFICATION: does this extend the existing "Reading a command's result" passage or move? It
arrived there as a verification concern — a probe that silently measures the wrong machine — and the
destructive behaviour is not a verification failure at all; it is a side effect on the working
environment. Extending keeps one place for "`uv run --with` is not what it looks like", which is the
`~/AGENTS.md` house preference for a variant of an existing rule. Against: the file's own admission
criteria ask whether a rule's miss is silent and expensive, and these two misses differ in kind.]

[NEEDS CLARIFICATION: **what is `UV_PYTHON=3.14` in `~/.zshenv` actually for, and can it be
narrowed?** It is the root cause, so this question comes before the others. The plausible intent is
making `uv tool install` and a bare `uv venv` outside any project land on 3.14 rather than on
whatever the system ships — a real want, and `bootstrap.sh` already installs 3.14 as the uv-managed
default (`uv python install --default`), which may cover it without the export. If it does, the
export is redundant and removing it costs nothing. If it does not, the narrower forms are
`UV_PYTHON` set only where tools are installed, or leaving it and accepting that every project must
pass `--python` explicitly — which is what `venv.recreate` already does and what makes it work.]

[NEEDS CLARIFICATION: does a generated `.python-version` still earn its place once the export is
narrowed? It would then work, and it is derivable from `requires-python`, which is already the
source of truth for `python_floor()` and the shipped `pyrightconfig.json`. It would also protect CI,
containers, and any machine without this export — none of which have the problem this plan is about,
which is the honest argument that it is a `repo-tasks`/`scaffoldapy` question rather than this
repo's. Note the ordering trap: adding it **first** would look like it fixed nothing and could get
reverted as useless, when it was only masked.]

[NEEDS CLARIFICATION: is `inv venv.check` worth running from somewhere automatic, given the exposure
is machine-wide rather than per-repo? It already exists and already prints the exact fix, but only
when someone types it — and the drift it detects is created silently by an unrelated command. Not
obviously worth a hook; noted because the detection half is already built and unused.]

[UNVERIFIED: measured on uv 0.11.19 only. Whether uv treats a _patch_-level mismatch (a 3.14.5 venv
against a 3.14.6 request) the same way as the minor-level mismatch tested here is untested, and it
is the case that would bite silently as the managed 3.14 moves under the machine.]
