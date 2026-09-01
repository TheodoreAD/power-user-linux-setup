---
status: idea
updated: 2026-09-01
---

# Should `mise` replace the nvm + go-archive + rustup trio?

## Context

Filed 2026-09-01 out of the "which shell can find which tool" work, which fixed the symptom per
environment and deliberately did not touch the underlying shape. Three language toolchains are
installed three different ways, each reaching `PATH` only through a `zshenv` snippet:

| package | method                                | outside zsh                                 |
| ------- | ------------------------------------- | ------------------------------------------- |
| `go`    | `archive` into `~/.local/share/go`    | fixed — now symlinked into `~/.local/bin`   |
| `rust`  | `script` (rustup, `--no-modify-path`) | needs `RUSTUP_HOME`/`CARGO_HOME` in the env |
| `node`  | `nvm`                                 | unreachable without sourcing `nvm.sh`       |

Each was fixed by a different mechanism because each breaks differently, which is the argument for
looking at whether one tool should own all three.

### What the research found, 2026-09-01

- **nvm is a sourced shell function by design.** Its README states it outright ("`which nvm` will
  not work, since `nvm` is a sourced shell function, not an executable binary") and that "when
  invoking bash as a non-interactive shell, like in a Docker container, none of the regular profile
  files are sourced". Its own answer is the `BASH_ENV` pattern, which covers bash and not `sh -c` —
  and `sh -c` is what a Docker `RUN` uses.
- **Volta is unmaintained.** Its README: "Volta is unmaintained... we will not be able to address
  breakages from new OS releases or other changes in the ecosystem, so you should put it on your
  maintenance roadmap at some point." It points users at `mise`. Worth recording because Volta was
  on the shortlist before this was checked.
- **`mise` is the successor most of the ecosystem now names**, covers node/go/rust/python in one
  actively-maintained Rust binary, and — the part that matters here — distinguishes the two modes
  explicitly. `mise activate` rewrites `PATH` from the shell prompt and its own docs say it "doesn't
  work well for non-interactive situations like scripts"; **shims** (`~/.local/share/mise/shims`)
  are documented as "useful for non-interactive environments like CI/CD pipelines, IDEs, or
  scripts". That is exactly this repo's failure mode, named by the tool's own documentation.

[PITFALL: `rustup`'s shims are not self-locating the way go's binary is. Symlinking
`~/.local/share/cargo/bin/cargo` into `~/.local/bin` puts a command on `PATH` that **fails** —
verified in a container: with `RUSTUP_HOME` unset, rustup searches `~/.rustup`, which this layout
does not use, and exits 1 with "could not choose a version of cargo to run". Broken-on-PATH is worse
than absent, so rust was deliberately left unsymlinked. Any future "just symlink them all" pass has
to know this.]

## Open questions

[NEEDS CLARIFICATION: does adopting `mise` actually reduce mechanisms, or add a fourth? It would
replace three `[packages.*]` entries with one, but `setup.toml`'s methods (`archive`, `script`,
`nvm`) are a general vocabulary other packages use, so the `nvm` method would become dead code while
`archive`/`script` stay. The saving is in the toolchains, not the installer.]

[NEEDS CLARIFICATION: shims mode has its own cost — every `node`/`go`/`cargo` call goes through a
shim that resolves the version by looking at `$PWD`. That is the behaviour that makes it work
non-interactively, and it is also a per-invocation cost and an extra layer in every stack trace.
Measure it before assuming it is free.]

[NEEDS CLARIFICATION: what happens to the per-project version pinning this repo does not currently
have? `mise` reads `mise.toml`/`.tool-versions` per directory, which is a feature nobody here asked
for and which changes what a bare `node` means depending on where you stand. Decide whether that is
wanted or whether a single global version is the point.]

[UNVERIFIED: whether `mise` is packaged in a way this repo's install pipeline can take. It would
need a `[packages.mise]` entry with a real method — check for a maintained PyPI wrapper first per
`~/AGENTS.md`, then a GitHub release binary — rather than its own `curl | sh` installer.]

## Recommended direction

Not now. The per-environment fixes landed 2026-09-01 and cover the measured failures; this is a
consolidation question, and the trigger for revisiting it should be a _second_ symptom the current
shape cannot fix cleanly — most likely node, which is the one left unsolved outside zsh.

If it is picked up, do it as a pilot on one toolchain rather than all three at once, per
`~/AGENTS.md`'s "apply them to one real, already-working repo first". `go` is the wrong pilot (it
works now); `node` is the right one, because it is the case with no good answer today.
