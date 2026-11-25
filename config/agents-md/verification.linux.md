### Reading a command's result [Claude Code]

Clean-looking stdout is not proof of success. The exit code is. The Bash tool reports it whenever it
is non-zero, so a plain unpiped command already gives you the real answer, and `echo $?` and
redirect-to-a-log add nothing. Assume a CLI's clean summary text and its exit code can disagree
until verified otherwise.

**A pipe no longer loses that**, so anything you remember about `tail` masking an upstream failure
is out of date. `[packages.claude-code]`'s `zshenv` snippet sets `PIPE_FAIL` in every shell the Bash
tool runs, so a pipeline reports the rightmost non-zero status rather than its last stage's.
`setopt | rg pipefail` confirms it in any session that seems to behave otherwise. Two consequences:

- **A non-zero exit after `| head` means `head` cut something off**, not that the command failed.
  Four different codes mean exactly that, depending on what was cut and by what, so read the fact
  rather than the number. Count first (`rg -c`, `wc -l`) or run it whole.
- **`| rg` or `| grep` as the last stage returns 1 when nothing matched**, which is an answer and
  not a failure.

### Backgrounding a command [Claude Code]

**Use the Bash tool's own `run_in_background`.** It survives across turns and re-invokes you on
exit. Backgrounding from the shell instead can leave you reading state from a command that **never
ran**: `nohup script.sh & disown` and `setsid script.sh &` both returned non-zero while the script's
first statement, a file write, never happened — yet a plain `cmd &` plus `sleep` in the same call
did run. Intermittent is what makes it dangerous. The next call inspects files or processes as
though the work happened, so the failure yields false evidence rather than an error, and a
background write that silently didn't happen looks exactly like one that did. If something must be
backgrounded anyway, have it write a marker the next call checks before trusting any result.
