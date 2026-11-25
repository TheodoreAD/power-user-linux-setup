#!/usr/bin/env zsh
# Claude Code SessionStart/CwdChanged hook: activate the current directory's direnv environment
# (a repo's .venv, through its .envrc) for every later Bash tool call. Deployed by
# [packages.claude-direnv-hook] in power-user-linux-setup's setup.toml, which also declares the
# hooks in ~/.claude/settings.json. Edit it there, never here.
#
# Why a hook writing $CLAUDE_ENV_FILE, measured 2026-11-25 in a throwaway WSL distro (Claude Code
# 2.1.332, direnv 2.32.1): each Bash call sources the session's shell snapshot, which ends by
# assigning PATH, and only then the files Claude Code keeps in $CLAUDE_ENV_FILE. So an export in
# ~/.zshenv loses PATH to the snapshot (VIRTUAL_ENV said one repo while python was another's), and
# this file is what wins.
#
# Why every run writes the whole environment rather than `direnv export`'s diff: Claude Code keeps
# one file per hook event (sessionstart-hook-0.sh, cwdchanged-hook-0.sh) and sources them all, so a
# diff from a directory with no .envrc is empty and the session-start repo's venv stays in force.
# Resetting first makes whichever file is sourced last decide.
#
# Why PATH entries ending in /.venv/bin are dropped: a venv active in the shell Claude Code was
# launched from is never the current directory's, and without this a terminal that had another
# repo's venv active leaks it into every directory with no .envrc. User decision 2026-11-25.

[[ -n ${CLAUDE_ENV_FILE:-} ]] || exit 0
command -v direnv > /dev/null 2>&1 || exit 0

unset DIRENV_DIR DIRENV_WATCHES DIRENV_DIFF DIRENV_FILE VIRTUAL_ENV
PATH=${(j.:.)${(s.:.)PATH}:#*/.venv/bin}
{
  print -r -- "unset VIRTUAL_ENV DIRENV_DIR DIRENV_WATCHES DIRENV_DIFF DIRENV_FILE"
  print -r -- "export PATH=${(q)PATH}"
  direnv export zsh 2> /dev/null
} > "$CLAUDE_ENV_FILE"
exit 0
