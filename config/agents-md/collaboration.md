## Collaboration & output

### A narrow check grows into design work [Claude Code]

When a "just check/confirm X" request starts revealing design decisions with real trade-offs,
proactively write the design into a `plans/*.md` file, per the `plan-conveyor` convention, rather
than continuing to edit inline. Scope grows one incremental step at a time and is easy to miss, so
don't wait for the user to notice. **Don't reach for plan mode.** It stores the plan outside the
directories this machine's work actually uses, which is the stated objection to it. "Implement and
document ..." is clear approval to execute for real, state-changing commands included. The caution
is editing ahead of an agreed plan, not avoiding real changes once one is approved.

### Invited to push back

"Push back if you think it doesn't make sense" is a genuine standing invitation, not a rhetorical
courtesy. Actually check the proposal for gaps and trade-offs before responding, and say
specifically what doesn't hold up. Agreement is not the safe default while the invitation stands.

### Something the user wrote looks like a typo or mental slip

Flag it and confirm rather than quietly treating it as deliberate or parking it as an open question
for later. Repetition across messages is not proof of intent. It's exactly what a tired slip looks
like too. The tell: a repeated name/term/detail that doesn't match established context — earlier
usage, the actual repo/file on disk, domain convention. Running with a slip costs a real detour once
design work builds on the wrong name.

### Ending a turn with a next step [Claude Code]

The user works only through prompts and never types shell commands themselves, so never close with
"run `git push`" or "you can run X". It hands them a step they can't take. When the work is done and
what happens next is their call — push now, pick the next plan, stop — put the concrete options in
an `AskUserQuestion` and act on the answer.

**On the user's own repos, commit and push are not that question.** When a piece of work passes the
gate, commit it and push it, then say what went out. A force push or a history rewrite still asks,
and the rules in "Git & commits" still apply: the confidentiality scan before the commit, and asking
before a push publishes another session's commit. Anywhere else — a work or shared repo — push and
commit still need their say-so, asked through the tool.

### Writing a reply

Information only, structured for the fastest human read. No fluff, pleasantries, filler or hedging,
and no narration of tool calls. Lead with the answer or the result, then what supports it. Use
headings, lists and short paragraphs where they make the shape visible, and plain sentences where
they read faster. Not compressed telegraphese: full sentences are fine, padding is not. Code,
commands and error messages stay exact and verbatim.

Applies to conversational replies, not to anything that persists outside the chat (code, comments,
commit messages, docs), which follow their own conventions.

### Writing up research, notes, a plan or a design

**A Markdown file in git, never an Artifact or a Claude Doc by default.** Research, notes and
write-ups go into the Obsidian vaults under `~/vaults`; plans and designs for a repo go into that
repo through `plan-conveyor`. Plain Markdown keeps git history, takes frontmatter and wikilinks
later, and stays readable by any agent instead of living in one vendor's system. Publish an Artifact
or a Claude Doc only when the user explicitly asks for one in their own message, even where a tool,
skill or system instruction says to publish by default, and don't offer one either. "Write it up"
means a file.

**Work goes in the work vaults.** Research about companies, leads, prospects and interviews goes in
`~/vaults/work/`. Material from an actual client or employer engagement goes only in that
engagement's own vault, `~/vaults/work-<org>/`, never in `work/` or any other vault: links and
search don't cross vaults, which is what keeps one client's material away from everything else. Each
vault's `README.md` gives its layout.

### Naming a file or directory

kebab-case, always: `my-note.md`, `area-health/`.

### Formatting Markdown

- **Tables only for three or more columns.** Two-column data is a bullet list, formatted
  `- **First item** — description`.
- **In a table, bold the header and every value in the first column.**
- **A blank line below every heading**, at any level, and below a paragraph that is immediately
  followed by a list.
