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

zenity --password --title="${title}" --text="${prompt}"
