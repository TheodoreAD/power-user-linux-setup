#!/bin/bash
# Refreshes every shallow clone under $RESEARCH_HOME/repos/ to the latest commit on its default
# branch. These are disposable reference clones with no local commits to preserve, so a hard
# reset to whatever was just fetched is safe and expected — not a working clone's update flow.
set -u

: "${RESEARCH_HOME:=${HOME}/research}"
mkdir -p "${RESEARCH_HOME}"/{repos,docs,pages}

shopt -s nullglob
for repo in "${RESEARCH_HOME}"/repos/*/; do
    [ -d "${repo}.git" ] || continue
    name=$(basename "$repo")
    before=$(git -C "$repo" rev-parse --short HEAD 2>/dev/null)
    if git -C "$repo" fetch --depth 1 origin -q && git -C "$repo" reset --hard FETCH_HEAD -q; then
        after=$(git -C "$repo" rev-parse --short HEAD)
        if [ "$before" = "$after" ]; then
            echo "[${name}] up to date (${after})"
        else
            echo "[${name}] ${before} -> ${after}"
        fi
    else
        echo "[${name}] FAILED to refresh" >&2
    fi
done
