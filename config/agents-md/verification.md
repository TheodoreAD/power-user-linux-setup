## Verification

### Reading a command's result [Claude Code]

Clean-looking stdout is not proof of success — the exit code is. The Bash tool reports it whenever
it is non-zero, so a plain unpiped command already gives you the real answer; `echo $?` and
redirect-to-a-log add nothing. Assume a CLI's clean summary text and its exit code can disagree
until verified otherwise.

**A pipe no longer loses that**, so anything you remember about `tail` masking an upstream failure
is out of date: `[packages.claude-code]`'s `zshenv` snippet sets `PIPE_FAIL` in every shell the Bash
tool runs, so a pipeline reports the rightmost non-zero status rather than its last stage's.
`setopt | rg pipefail` confirms it in any session that seems to behave otherwise. Two consequences:

- **A non-zero exit after `| head` means `head` cut something off**, not that the command failed.
  Four different codes mean exactly that, depending on what was cut and by what — so read the fact
  rather than the number. Count first (`rg -c`, `wc -l`) or run it whole.
- **`| rg` or `| grep` as the last stage returns 1 when nothing matched**, which is an answer and
  not a failure.

### Probing whether a dependency is absent

`uv run --with …` layers an ephemeral overlay _over_ the active environment, so from a directory
with a venv active the probe measures a machine that **has** the package — and it passes, which is
the answer you were hoping for. Strip the environment
(`env -u VIRTUAL_ENV -u PYTHONPATH uv run --no-project --python <ver> --with <pkg> …`) and check
`sys.prefix` if in doubt. A package registering a plugin through an entry point (pytest's
`pytest11`) needs nothing in the project to name it, so absence probes are exactly where
contamination hides.

### Backgrounding a command [Claude Code]

**Use the Bash tool's own `run_in_background`** — it survives across turns and re-invokes you on
exit. Backgrounding from the shell instead can leave you reading state from a command that **never
ran**: `nohup script.sh & disown` and `setsid script.sh &` both returned non-zero while the script's
first statement, a file write, never happened — yet a plain `cmd &` plus `sleep` in the same call
did run. Intermittent is what makes it dangerous: the next call inspects files or processes as
though the work happened, so the failure yields false evidence rather than an error, and a
background write that silently didn't happen looks exactly like one that did. If something must be
backgrounded anyway, have it write a marker the next call checks before trusting any result.

### Waiting for something to finish

**Reach for the purpose-built waiter before hand-rolling a loop**:
`gh run watch <run-id> --exit-status` blocks until a run finishes and turns failure into a non-zero
exit, with the run-id from `gh run list --branch <branch>`.

A hand-rolled wait is only as sound as the value its condition tests, and **a filter that can return
_nothing_ never satisfies one**: `gh run list --commit <7-char-sha>` prints `[]` and exits 0,
because `--commit` matches only the full 40-char SHA — so `.[0].status` is `null` forever and
`until [ "$(…)" = "completed" ]` can never become true. Such a loop cannot fail, so it reports
nothing, and "still running" and "will never finish" look identical. Run the inner command once and
look at what it actually returns before wrapping it, bound the wait by an iteration count or
deadline, and say so when it expires.

### Generalizing from a sample to a set

A clean-looking sample is not evidence about its siblings, and "they're all the same kind of file"
is not evidence either. `--stat`'s per-file line counts are the cheap tell: when they disagree, read
the outliers, not the representative-looking one. This includes a sample you created yourself —
truncating your own search output turns a complete set into a sample without saying so (see
"Viewing, searching, or editing files").

**A probe you write to test a library's behaviour is such a sample, and a passing probe reads as
confirmation.** When the suspicion is about precision, width, or any limit, the input has to be one
that can actually fail: a `Decimal` round-trip through SQLAlchemy's SQLite dialect passed on ten
significant digits and silently lost the value on nineteen, no warning, and the ten-digit probe read
as "`Numeric` is fine" — one step from being written into a shared doc where nobody re-derives it.
Choose the input from what would break, not from what is convenient to type.

### Verifying behavior in a repo with test coverage

Run the test suite, not a one-off ad-hoc script (`python3 -c "..."`, a manual re-render in `/tmp`) —
check whether an existing test, or a trivial addition to one, already covers it. "Slow" or "needs
the network" is not a reason to fall back to a throwaway script: write a real, clearly-labeled test
instead (marked/skipped from the fast default suite per that repo's convention). Genuinely
exploratory prototyping with no natural home in the suite yet stays legitimate, done deliberately
outside the real repo. A green run is only evidence about the code that was actually imported — with
an editable install the package resolves to the working tree, not to whatever you checked out, so
confirm the import path (`python -c "import pkg; print(pkg.__file__)"`) before trusting a per-commit
or per-worktree result.

`tmp_path` sandboxes the working tree, not the user: a test that runs `direnv allow`, `uv tool`,
`inv configure`, or any code path through `Path.home()` writes into the real `$HOME` (direnv's allow
database, `~/.cache/claude-code`, ...) and leaves one stale entry per run. Give such tests a
fake-`HOME` fixture — patch `os.environ` _and_ any library holding its own environment snapshot
(copier runs `_tasks` from plumbum's `local.env`, copied at import; `monkeypatch.setenv` never
reaches it) — and pin `UV_CACHE_DIR` back to the real cache so the run stays warm.
