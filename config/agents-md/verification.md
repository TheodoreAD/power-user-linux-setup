## Verification

### Reading a command's result [Claude Code]

Clean-looking stdout is not proof of success — the exit code is. The Bash tool reports it whenever
it is non-zero, so a plain unpiped command already gives you the real answer; `echo $?` and
redirect-to-a-log add nothing. What loses it is a pipe: `tail`/`grep` return _their own_ exit code,
so `$?` after a pipeline never reflects the upstream failure, and the tool's exit report is the
filter's too. Assume a CLI's clean summary text and its exit code can disagree until verified
otherwise.

Same shape when probing whether a dependency is **absent**: `uv run --with …` layers an ephemeral
overlay _over_ the active environment, so from a directory with a venv active the probe measures a
machine that has the package — and it passes, which is the answer you were hoping for. Strip the
environment (`env -u VIRTUAL_ENV -u PYTHONPATH uv run --no-project --python <ver> --with <pkg> …`)
and check `sys.prefix` if in doubt. A package registering a plugin through an entry point (pytest's
`pytest11`) needs nothing in the project to name it, so absence probes are exactly where
contamination hides.

Backgrounding from the shell can leave you reading state from a command that **never ran**:
`nohup script.sh & disown` and `setsid script.sh &` both returned non-zero while the script's first
statement, a file write, never happened — yet a plain `cmd &` plus `sleep` in the same call did run.
Intermittent is the danger: the next call inspects processes or files as though the work happened,
so the failure yields false evidence rather than an error, and a background write or delete that
silently didn't happen looks exactly like one that did. Use the Bash tool's own `run_in_background`
(it survives across turns and re-invokes you on exit); if something must be backgrounded anyway,
have it write a marker the next call checks before trusting any result.

A wait is only as sound as the value its condition tests, and a filter that can return _nothing_
never satisfies one: `gh run list --commit <7-char-sha>` prints `[]` and exits 0 — `--commit`
matches only the full 40-char SHA — so `.[0].status` is `null` forever and
`until [ "$(…)" = "completed" ]` can never become true. Such a loop cannot fail, so it reports
nothing, and "still running" and "will never finish" look identical. Before wrapping anything in a
loop, run the inner command once and look at what it actually returns; bound the wait by an
iteration count or deadline, and say so when it expires. Best is not to hand-roll the loop at all —
reach for the purpose-built waiter first: `gh run watch <run-id> --exit-status` blocks until a run
finishes and turns failure into a non-zero exit, and the run-id comes from
`gh run list --branch <branch>`, the filter that actually matches.

### Generalizing from a sample to a set

A clean-looking sample is not evidence about its siblings, and "they're all the same kind of file"
is not evidence either. `--stat`'s per-file line counts are the cheap tell: when they disagree, read
the outliers, not the representative-looking one. This includes a sample you created yourself —
truncating your own search output turns a complete set into a sample without saying so (see
"Viewing, searching, or editing files").

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
