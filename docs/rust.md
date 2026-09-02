# Rust

The Rust toolchain via rustup, installed to XDG paths instead of rustup's own dotdirs.

<https://www.rust-lang.org/tools/install> <https://rust-lang.github.io/rustup/>

Installed via `inv tools.install` (script method — pipes the official rustup installer, pointed at
XDG-compliant paths instead of its `~/.cargo` / `~/.rustup` defaults). Shell environment is written
to `~/.zshenv` by `inv zsh.configure`.

## Environment

```shell
RUSTUP_HOME=~/.local/share/rustup   # installed toolchains, rustup config
CARGO_HOME=~/.local/share/cargo     # cargo cache, registry, installed binaries, rustc/cargo/etc.
```

Both are set automatically by the `zshenv` snippet in `setup.toml`, which also sources
`$CARGO_HOME/env` to put `$CARGO_HOME/bin` on `PATH`.

## What's included

Rustup's `default` profile (used here) installs `rustc`, `cargo`, `rust-std`, `rust-docs`,
`rustfmt`, and `clippy` in one shot. The `rust-analyzer` language server is added on top via
`post_install` in `setup.toml` (`rustup component add rust-analyzer`) — it's only needed for
non-JetBrains editors (VS Code, Neovim, Helix, Zed); PyCharm's Rust plugin uses its own analysis
engine, see [ide.md](ide.md). `post_install` only runs on a fresh install (it's skipped once `rustc`
already exists), so it won't retroactively add new components to an existing install — see Updating
below for that.

## Updating

`rustup` itself manages toolchain versions (stable/beta/nightly, and per-project overrides via
`rust-toolchain.toml`) — no separate version manager needed. `inv tools.install` will **not** update
an existing install (the `script` method only runs once, when `rustc` is missing), so updates go
through `rustup` directly:

```shell
rustup update                              # update the toolchain (rustc, cargo, clippy, rustfmt, ...)
rustup self update                         # update rustup itself
rustup component add rust-analyzer         # add a component that's missing on an existing install
rustup toolchain list                      # installed toolchains
```

## Uninstalling

```shell
rustup self uninstall
```

This removes the whole install — toolchains, cargo cache/registry, and the rustup binary itself
(`~/.local/share/cargo` and `~/.local/share/rustup`, since `CARGO_HOME`/`RUSTUP_HOME` point there).
It prompts for confirmation; pass `-y` to skip that.

Afterwards, either set `enabled = false` on `[packages.rust]` in `setup.toml` (so
`inv tools.install` doesn't reinstall it) or remove the section entirely. Neither
`inv tools.install` nor `inv zsh.configure` prune stale config on their own, so also remove the
`PULSE::rust` sentinel block from `~/.zshenv` by hand — otherwise it'll harmlessly export
`RUSTUP_HOME`/`CARGO_HOME` and source a `$CARGO_HOME/env` that no longer exists.

## Verify

```shell
rustc --version
cargo --version
rust-analyzer --version
```

## See also

- [Dev container](dev-container.md) — the two variables rustup's shims need outside zsh
- [IDEs](ide.md) — which editors need rust-analyzer
- [Updating and removing](updating.md) — `rustup update`, and what else updates itself
