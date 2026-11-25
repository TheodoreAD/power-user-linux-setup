## Bash & tool use

### Viewing or editing a file [Claude Code]

Prefer the dedicated harness tool over its Bash equivalent: Read over `cat`/`sed -n`/`head`/`tail`,
Edit/Write over `sed -i`/heredocs. Dedicated tools have their own permission gate and keep the whole
result. Never pipe tool output through `| head`/`| tail` to save context. The harness already
truncates large output and saves the full text to a file, so pre-truncating only loses data and
forces a second run; if size is the worry, count first (`rg -c`, `wc -l`). That includes a log you
did redirect to — Grep/Read _on the log_ as a second call, never `; rg … log | head` tacked onto the
same one. And never append `; echo "EXIT=$?"`: it adds a chain for information the tool already
reports.

**One exception: a mechanical rewrite across many sites** — one substitution through several files,
or a dozen places in one — where Edit costs a call per site. A script may do that, on one condition:
**read `git diff` of what it changed before the gate or the commit.** A pattern wider than intended
applies silently, where Edit's exact, unique match would have refused. One such rewrite stripped the
opening bracket from tags in seven plans, and only reading the diff caught it. A single edit, or a
handful, stays with Edit.

### Searching a tree, by name or by content

**`fd` over `find`, `rg` over `grep -r`.** A non-recursive `grep` stays fine. Translate rather than
reach for the old spelling:

- `find <dir> -name '*.py'` → `fd -e py . <dir>`
- `find <dir> -iname '*plan*'` → `fd plan <dir>`

`find` earns the call only for what `fd` cannot do:

- acting on matches — `-exec`, `-delete`
- selecting by time, size or permission
- `-printf`
- a machine without `fd`, inside a container say

That covered **2 of 37 calls** measured over a week, so the exemption almost certainly does not
cover yours.

**Both tools skip a hidden path on _descent_ only, and the miss is silent.** The command is
well-formed, the path exists, and an empty result reads exactly like "already clean". Three ways
through it:

- **Name the directory**, which needs no flag at all. `rg 'uses: ' <repo>` finds nothing where
  `rg 'uses: ' <repo>/.github` finds every workflow. That works for a **hidden** directory only: a
  **gitignored** one — anything under `.venv/`, `node_modules/`, `build/` — stays ignored even when
  named, and comes back just as silently empty. There, `rg --no-ignore` or `fd -I`.
- **`fd -H`**, safe as written.
- **`rg --hidden --glob '!.git'`**, where the exclusion is **not** optional, because git does not
  ignore its own directory.

**`-H` and `-I` are not a pair**, and pairing them is what makes the safe flag look expensive. `-H`
adds the dot-files you would want searched and nothing else. `-I` disables `.gitignore` and returns
**17,081 files against 152**. Reach for `-I` only to find one file you know is ignored, never as a
default.

### Translating a `grep` invocation to `rg`

**One edit: delete the `r`, keep every other letter.** `rg` is recursive by default and its `-r` is
`--replace`, which takes the next thing as a replacement string. So a carried-over `r` eats your
flag bundle and nothing you asked for applies. Every such form exits 0 and none of them warns. The
worst is a bare `-r`, and it is why the habit survives: rg searches for _the path you named_ across
the whole working directory, prints hits from files you never named, and writes your pattern over
each match — which reads exactly like the recursive search you wanted.

**Three more letters mean something else in rg**, and the one-edit rule is wrong for them. Each
exits 0 and searches something other than what you asked:

| `grep`                       | the same letter in `rg`   | write instead                    |
| ---------------------------- | ------------------------- | -------------------------------- |
| `-L` files **without** match | `--follow`: matched lines | `--files-without-match`          |
| `-h` no filename prefix      | `--help`: no search       | `-I` (`--no-filename`)           |
| `-I` skip binary files       | `--no-filename`           | drop it; rg skips binary already |

`-E` also changes meaning (`--encoding`), but it fails loudly, so it needs no entry here.

**The detection signature, since every occurrence on record was caught by luck:** your own flag
letters appearing where the matched text should be (`inv ai.n` for `inv ai.check-…`), line numbers
missing after you asked for `-n`, a `-l` that printed lines, or hits from a path you did not name.
Any of those means `-r` ate the bundle; a `-L` search printing lines, or help text where results
belong, means one of the three letters above did. Re-run with the corrected flags rather than
reading the output. Deliberate replacement is unaffected: spell it `--replace`, which no `grep`
bundle can turn into.

### Writing to a repo other than the session's

**Only when the user has explicitly approved that change.** Without approval, make no edit and no
commit, however small, however obviously correct, however much a skill's own instructions tell you
to. File it instead:
`python3 ~/.agents/skills/plan-conveyor/scripts/plans.py new <topic> --for <repo>` puts a plan in
that repo's store mirror, outside every working tree, and the next session working there is offered
it. Commit it in the store immediately and say where it went. Genuinely iterative work needing
back-and-forth in that repo gets its own session there rather than a relay.

**With approval, make exactly the approved change and nothing beside it.** Follow that repo's own
`AGENTS.md` and gate, commit only your own hunks (another session may have uncommitted work there),
and report the repo and the commit's SHA, so the user knows a commit exists that no session in that
repo made.

Approval rather than judgment, because a commit in someone else's tree is silent by construction. It
looks routine in `git log`, and the session that owns the repo may push it without ever knowing it
was not theirs. So without approval a mutating `git -C <other repo> commit`/`push` prompting is a
**stop**, not a checkpoint to click through.

### Parsing a command's output, or formatting a date or decimal, in a script

Force plain, fixed-format output from anything a script parses or asserts on. The ambient
environment changes the bytes, and that is not yours to assume:

- **Locale** — `LC_TIME=C date ...`, `LC_NUMERIC=C awk ...`. A locale-sensitive `date` specifier
  (`%a`, `%b`, ...) or a decimal `awk`/`printf` format follows the ambient locale: a weekday can
  come back `Mi` rather than `Wed`, a number `1,23` rather than `1.23`.
- **Colour** — `uv --color never`, or `env -u FORCE_COLOR` for a tool with no such flag. Claude
  Code's background sessions export `FORCE_COLOR=3`, and uv honours it through a pipe, so a parsed
  path comes back wrapped in escapes and a regex quietly stops matching. `NO_COLOR` alone is not the
  fix: the common convention ignores it whenever `FORCE_COLOR` is set.

"The terminal looks fine" is not proof — verify the actual bytes.
