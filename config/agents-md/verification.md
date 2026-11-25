## Verification

### Probing whether a dependency is absent

`uv run --with …` layers an ephemeral overlay _over_ the active environment. So from a directory
with a venv active the probe measures a machine that **has** the package, and it passes, which is
the answer you were hoping for. Strip the environment
(`env -u VIRTUAL_ENV -u PYTHONPATH uv run --no-project --python <ver> --with <pkg> …`; in
PowerShell, remove `Env:VIRTUAL_ENV` and `Env:PYTHONPATH` first) and check `sys.prefix` if in doubt.
A package registering a plugin through an entry point (pytest's `pytest11`) needs nothing in the
project to name it, so absence probes are exactly where contamination hides.

### Waiting for something to finish

**Reach for the purpose-built waiter before hand-rolling a loop.**
`gh run watch <run-id> --exit-status` blocks until a run finishes and turns failure into a non-zero
exit, with the run-id from `gh run list --branch <branch>`.

A hand-rolled wait is only as sound as the value its condition tests, and **a filter that can return
_nothing_ never satisfies one**. `gh run list --commit <7-char-sha>` prints `[]` and exits 0,
because `--commit` matches only the full 40-char SHA, so `.[0].status` is `null` forever and
`until [ "$(…)" = "completed" ]` can never become true. Such a loop cannot fail, so it reports
nothing, and "still running" and "will never finish" look identical. Run the inner command once and
look at what it actually returns before wrapping it. Bound the wait by an iteration count or
deadline, and say so when it expires.

### Generalizing from a sample to a set

A clean-looking sample is not evidence about its siblings, and "they're all the same kind of file"
is not evidence either. `--stat`'s per-file line counts are the cheap tell: when they disagree, read
the outliers, not the representative-looking one. This includes a sample you created yourself, since
truncating your own search output turns a complete set into a sample without saying so — see
"Viewing, searching, or editing files".

**A probe you write to test a library's behaviour is such a sample, and a passing probe reads as
confirmation.** When the suspicion is about precision, width, or any limit, the input has to be one
that can actually fail. A `Decimal` round-trip through SQLAlchemy's SQLite dialect passed on ten
significant digits and silently lost the value on nineteen, no warning, and the ten-digit probe read
as "`Numeric` is fine" — one step from being written into a shared doc where nobody re-derives it.
Choose the input from what would break, not from what is convenient to type.

### Verifying behavior in a repo with test coverage

Run the test suite, not a one-off ad-hoc script such as `python3 -c "..."` or a manual re-render in
`/tmp`. Check whether an existing test, or a trivial addition to one, already covers it. "Slow" or
"needs the network" is not a reason to fall back to a throwaway script. Write a real,
clearly-labeled test instead, marked or skipped from the fast default suite per that repo's
convention. Genuinely exploratory prototyping with no natural home in the suite yet stays
legitimate, done deliberately outside the real repo. A green run is only evidence about the code
that was actually imported. With an editable install the package resolves to the working tree, not
to whatever you checked out, so confirm the import path
(`python -c "import pkg; print(pkg.__file__)"`) before trusting a per-commit or per-worktree result.

`tmp_path` sandboxes the working tree, not the user. A test that runs `direnv allow`, `uv tool`,
`inv configure`, or any code path through `Path.home()` writes into the real `$HOME` — direnv's
allow database, `~/.cache/claude-code`, and so on — and leaves one stale entry per run. Give such
tests a fake-`HOME` fixture, patching `os.environ` _and_ any library holding its own environment
snapshot (copier runs `_tasks` from plumbum's `local.env`, copied at import, and
`monkeypatch.setenv` never reaches it). Pin `UV_CACHE_DIR` back to the real cache so the run stays
warm.
