#!/bin/bash
# $1 is the caller-supplied prompt (sudo passes "[sudo] password for user:", ssh passes
# "Enter passphrase for key '...':") — shown verbatim so the dialog is accurate for either caller.
#
# The title is derived from that prompt rather than fixed. Both callers share this one helper, and
# an identical "Authentication required" window for each is genuinely ambiguous: ssh-add retries a
# passphrase three times, so a failing SSH load produces three dialogs a user reasonably reads as
# sudo nagging them. Confirmed 2026-08-28 — reported as "you asked me for a lot of sudo prompts",
# for prompts that were not sudo's and for a key that did not need one.
prompt="${1:-Password required}"

case "${prompt}" in
  *"passphrase for key"*) title="SSH key passphrase" ;;
  *"[sudo]"* | *"password for"*) title="sudo password" ;;
  *) title="Authentication required" ;;
esac

# No display, no dialog. ~/.zshenv exports SUDO_ASKPASS/SSH_ASKPASS for every shell, and
# zsh.configure's writer ignores tags, so a headless WSL distro or a dev container gets this
# helper too — where `zenity` either isn't installed or can't connect, and sudo's own report of
# that is the unhelpful "sudo: no password was provided". Read the terminal instead: the caller
# handed us a prompt, /dev/tty is the one thing that's definitely there, and turning echo off is
# two lines. Fails cleanly (exit 1, nothing on stdout) when there is no terminal either, which is
# what a non-interactive caller needs to see.
if [ -z "${DISPLAY}" ] && [ -z "${WAYLAND_DISPLAY}" ]; then
  # Open it rather than test for it: /dev/tty exists as a device node even with no controlling
  # terminal, where opening it fails with ENXIO ("No such device or address") — so `[ -e /dev/tty ]`
  # passes and the next line prints an error nobody can act on.
  exec 3<> /dev/tty 2> /dev/null || exit 1
  printf '%s ' "${prompt}" >&3
  stty -echo <&3
  IFS= read -r reply <&3
  status=$?
  stty echo <&3
  printf '\n' >&3
  exec 3>&-
  [ "${status}" -eq 0 ] || exit 1
  printf '%s\n' "${reply}"
  exit 0
fi

zenity --password --title="${title}" --text="${prompt}"
