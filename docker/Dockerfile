# Canonical example: layering PULSE onto a base image at *build* time — the bake-time analog of
# the postCreateCommand flow in docs/dev-container.md. Three uses:
# 1. A documented, working example of "FROM a stock base image, layer PULSE on top."
# 2. A vehicle for local testing of *uncommitted* changes to tasks/*.py, setup.toml, etc. — it
# COPYs the local working tree in and runs bootstrap-devcontainer.sh --local, not a git clone
# of a pinned ref, so `docker build` picks up whatever's on disk right now.
# 3. A template: FROM this image to layer your own extra tooling on a "strong base," or copy
# this file's pattern against a different base image.
#
# Build from the repo root (needs the whole tree in build context):
# docker build -f docker/Dockerfile -t pulse-devcontainer .
#
# Not used by .devcontainer/devcontainer.json (that uses a prebuilt image + postCreateCommand
# instead) and not built by CI (.github/workflows/devcontainer.yml only smoke-tests
# .devcontainer/devcontainer.json) — this is for local iteration and as a copyable example, not a
# published/CI-tested artifact.

FROM ubuntu:24.04

# PULSE configures zsh, and only zsh — there is no bashrc/bash_profile writer and no `bashrc` field
# in setup.toml. Anything that lands in ~/.local/bin or /usr/bin therefore works in bash by virtue
# of where it sits, and anything installed to its own prefix does not. Docker's ENV is the right
# mechanism for the difference here: it applies to every process in the image, including the
# `RUN`/`sh -c` and `postCreateCommand` contexts that read no shell config at all.
#
# `go` needs nothing extra now — setup.toml symlinks it into ~/.local/bin. rustup's shims do:
# without RUSTUP_HOME they search ~/.rustup, which this layout does not use, and exit 1 with
# "could not choose a version of cargo to run". Verified both directions in a container.
#
# node/npm are deliberately absent from this list. They live under a version-specific nvm path
# (~/.local/share/nvm/versions/node/vX.Y.Z/bin) and nvm publishes no stable alias to point at —
# `alias/default` holds `lts/*`, itself another alias. Hardcoding a version here would go stale on
# the next node upgrade. nvm is a sourced shell function by design (its README says so outright),
# so reaching it from a non-interactive shell is the tool's documented BASH_ENV pattern, not a PATH
# entry. Use `zsh -lic` for node in this image, or source nvm.sh explicitly.
ENV PATH="/root/.local/share/cargo/bin:/root/.local/bin:${PATH}" \
    RUSTUP_HOME="/root/.local/share/rustup" \
    CARGO_HOME="/root/.local/share/cargo"
WORKDIR /setup

COPY setup.toml .
COPY bootstrap.sh .
COPY bootstrap-devcontainer.sh .
COPY tasks/ tasks/
COPY config/ config/

RUN bash bootstrap-devcontainer.sh --local \
    && inv clean.all-full \
    && rm -rf /var/lib/apt/lists/* /tmp/*
