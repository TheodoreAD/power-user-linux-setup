#!/bin/bash
# $1 is the caller-supplied prompt (sudo passes "[sudo] password for user:", ssh passes
# "Enter passphrase for key '...':") — shown verbatim so the dialog is accurate for either caller.
zenity --password --title="Authentication required" --text="${1:-Password required}"
