---
status: landed
updated: 2026-09-02
---

# Every commit carries a why, because the log is the only thing an agent reads

Filed from an `ingesta` session, 2026-09-01, after the user named it directly: **commits must say
what and why, and for that they must always have a description, so agents can walk through history
and understand the past without checkouts.**

## Context

`### Committing multi-part work` in `config/agents-md/git.md` already opens on the premise — "git
history is how future agents learn why a change happened" — and then constrains only _granularity_.
The body of the message is the other half of that same claim and is nowhere stated, so a session can
split its commits impeccably and still leave a log that explains nothing.

**What changed is who reads it.** A commit body used to be a courtesy to a colleague who mostly
remembered the change anyway. Work here is now almost entirely agentic, and an agent arriving at a
commit has no memory of it at all — the log is not a supplement to its recollection, it is the whole
of its access.

**And on this machine it cannot go and look instead.** Parallel sessions share one working tree, so
checking out an old commit to understand it is not a private act — it moves a tree other sessions
are working in, which the same file forbids elsewhere. `git log` and `git show` are the only reads
that are safe by construction. That closes the loop: the body is not the convenient channel, it is
the only one, and a subject line is the entire budget for a change nobody can afford to check out.

## The failure shape, measured

The session that prompted this made 17 commits. Fifteen carried real bodies; **two carried only the
`Co-Authored-By:` trailer**, and both were plan/doc commits landing immediately after the
substantive code commit they belonged to — `Close the elapsed-time deferral` and
`Point stage 6 at
where the install question now lives`.

The rationalisation is worth recording because it is seductive and specific: _the reasoning had just
been written into the plan file in that very commit_, so restating it in the message felt like
duplication. It is not, for two reasons:

- **`git log` does not show the file.** The reader deciding whether a commit is worth opening sees
  the subject and nothing else.
- **For a plan commit the body outlives what it describes.** `plan-docs` retires a plan by
  **deleting** it, and `archive` reconstructs it from the deletion commit — so the file is
  deliberately temporary while the message is permanent. A bare-bodied plan commit is the one case
  where the "the file says it" defence is not merely weak but backwards.

The same session had `~/AGENTS.md` in context throughout and still produced them, which suggests
this is a genuine gap in the wording rather than an adherence problem.

## Recommended direction

**Extend `### Committing multi-part work`; do not add a heading.** The section already states the
premise this rule follows from, and a reader who meets granularity and body under one principle
generalises better than one holding two adjacent rules. `git.md` stands at 8 rules / 191 lines and
would stay at 8.

Roughly:

> **Every commit has a body, and the body says _why_.** The subject says what changed; the body says
> what it is for, what it beat, and what it cost — an agent reading `git log` months later has no
> other access to that, and on a machine where sessions share one working tree it cannot check the
> commit out to find out. A doc or plan commit is not exempt: the log does not show the file, and a
> plan file is deleted at retirement while its commit message is permanent. A trailer is not a body.

Two guards worth writing in, because both failure directions are real:

- **A floor, not a ceremony.** A formatting fix's why is one clause, and demanding a paragraph for
  it teaches padding — which is worse than a bare subject, because padding reads as reasoning.
- **`Co-Authored-By:` alone satisfies `%b`.** Any check written for this — a report, an audit, a
  `git log --format` sweep — has to strip trailers first, or the two commits above look compliant.
  That is exactly how they passed unnoticed in the session that made them.

## Landed 2026-09-02

Written into `config/agents-md/git.md` as three paragraphs extending
`### Committing multi-part work`, exactly as the direction above proposed — no new heading, `git.md`
still at 8 rules. Deployed to `~/AGENTS.md` with `inv deploy.all --name agents-md`.

All three questions were answered rather than deferred:

[DECISION: **nothing enforces it.** A `commit-msg` hook is refused under the same rule as every
other mechanism firing behind the agent's back. That was policy already; what is new is that it now
has a measurement behind it — the sweep recorded in `2026-08-23-git-hooks-for-quality-gate.md` on
2026-09-02 found the CI shape a hook would have caught has stopped occurring since the equivalent
`~/AGENTS.md` rule went in. Teaching the rule is not merely the preferred lever here, it is the one
observed to work.]

[DECISION: **the store is the exception, and it is named in the rule rather than left to be
inferred.** A plan filed into the store commits as `<repo>: <what it is>` with no body, because the
filed plan is its own description and the commit is only its delivery. `gh pr create --body` and
`gh issue comment` get the full rule — a PR description is read by the same agents, with the same
lack of access to anything but the text.]

[DECISION: **the `scaffoldapy` question is handed off, not left open here.** It was the third
question and it is a different repo's decision to make: a generated repo carries its own `AGENTS.md`
to contributors who never see this machine's, and the rule's strongest supporting argument — that
sessions share one working tree, so no one can check a commit out to understand it — is a property
of this machine and not of theirs. The premise survives the move and that argument does not, which
is exactly the kind of thing the owning repo should weigh. Filed as
`2026-09-02-commit-bodies-in-generated-repos.md` in `scaffoldapy`'s store mirror, with the trimmed
version recommended; writing into another repo is out.]

## What this plan still owes

Nothing. The rule is written and deployed, the enforcement and store-exception questions are
decided, and the one remaining question belongs to `scaffoldapy` and now has its own plan there.
Retirable.

## Migrated to

- **The rule itself** → `config/agents-md/git.md`, `### Committing multi-part work`, deployed to
  `~/AGENTS.md`. That is the artifact; read it there rather than the draft wording in "Recommended
  direction" above, which it has moved past.
- **Evidence and admission argument** → `contributing/global-agents-md.md`,
  `## Committing multi-part work` → `### Every commit has a body`. Carries the 17-commit
  measurement, the two-bare-bodies shape, the "the plan file already says it" rationalisation and
  why it is backwards for a plan commit, and the three guards — plus one thing stated there and not
  here, which of the two supporting arguments is machine-specific.
- **The enforcement decision** → `contributing/global-agents-md.md`,
  `## Proposing an enforcement mechanism for agent behavior`, where it joins the measurement that
  now backs the principle.
- **The open `scaffoldapy` question** → `2026-09-02-commit-bodies-in-generated-repos.md`, filed in
  that repo's store mirror and committed there. It carries the trimmed-version recommendation and
  names which clauses not to copy.

**Deliberately not migrated:** the verification log (rule written, deployed, verified at a line
number) — that is in git. The draft wording under "Recommended direction" is not migrated either:
the shipped clause is longer and differs in its guards, so keeping the draft would leave two
versions with only their dates to tell them apart.
