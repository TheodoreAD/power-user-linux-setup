#!/bin/bash
# Devcontainer fallback for pulse-proxy.service: no systemd --user unit tracking, no crash
# auto-restart, no persistence across a container rebuild — invoke again (e.g. from
# postCreateCommand) any time the container restarts. See docs/corporate-proxy.md.
# The systemd unit's EnvironmentFile, by hand: written only by `inv proxy.install
# --keyring-fallback`, holds PYTHON_KEYRING_BACKEND and no secret. Without it Px looks for a
# Secret Service that a container does not have and fails to read its own credential.
# shellcheck disable=SC1091 # optional, and its path is not resolvable at lint time
[ -f "${HOME}/.config/power-user-linux-setup/proxy.env" ] &&
  . "${HOME}/.config/power-user-linux-setup/proxy.env" && export PYTHON_KEYRING_BACKEND

pgrep -f "${HOME}/.local/bin/px$" > /dev/null ||
  nohup "${HOME}/.local/bin/px" > "${XDG_STATE_HOME:-$HOME/.local/state}/pulse-proxy.log" 2>&1 &
