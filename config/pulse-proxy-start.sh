#!/bin/bash
# Devcontainer fallback for pulse-proxy.service: no systemd --user unit tracking, no crash
# auto-restart, no persistence across a container rebuild — invoke again (e.g. from
# postCreateCommand) any time the container restarts. See docs/corporate-proxy.md.
pgrep -f "${HOME}/.local/bin/px$" > /dev/null ||
  nohup "${HOME}/.local/bin/px" > "${XDG_STATE_HOME:-$HOME/.local/state}/pulse-proxy.log" 2>&1 &
