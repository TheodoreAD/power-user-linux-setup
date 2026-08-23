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

ENV PATH="/root/.local/bin:${PATH}"
WORKDIR /setup

COPY setup.toml .
COPY bootstrap.sh .
COPY bootstrap-devcontainer.sh .
COPY tasks/ tasks/
COPY config/ config/
COPY skills/ skills/

RUN bash bootstrap-devcontainer.sh --local \
    && inv clean.all-full \
    && rm -rf /var/lib/apt/lists/* /tmp/*
