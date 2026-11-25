---
status: idea
updated: 2026-11-08
---

# Auto mode as the declared default, with a slim rule set and unprompted push and PR work

## Context

Asked 2026-11-08: _"do some reserach if people still use allowlist or denylist for claude, or if the
auto classifier is considered good enough for most work. we are not doing anything there that could
cause real life problems, only a mess in github or a mess in our os, which we can now rebuild thanks
to power user linux setup easily."_ After the research, the user chose to file this plan and added:
_"let's do 1, but allow git push and github operations on prs."_

**The declared mode and the real mode disagree, and the real one is auto.** `setup.toml` declares
`claude_default_mode = "acceptEdits"` (dropped from auto 2026-08-24, see the `session-bash-audit`
skill's `references/research.md`), and `~/.claude/settings.json` carries it. But 96% of Bash calls
in the week to 2026-09-05 ran under auto, toggled per session, because acceptEdits costs about 1,562
web prompts a month against auto's 10 classifier denials, all benign
(`plans/2026-09-05-web-tool-permissions-and-what-auto-actually-buys.md`). The session that wrote
this plan was in auto too. A declaration nobody runs describes nothing.

**What the field does, researched 2026-11-08** (primary sources read: Anthropic's auto-mode default
article and engineering post, `code.claude.com/docs/en/permission-modes`, arXiv 2604.04978,
Backslash Security's write-up; community sentiment from one Hacker News thread, partly read, and
search summaries — Reddit was unreachable, so treat the proportions as indicative):

- Auto is the built-in starting mode for interactive sessions from Claude Code v2.1.283; an explicit
  `permissions.defaultMode` still overrides it.
- Anthropic telemetry: users approve 97% of permission prompts; as of June 2026, 49.5% of active CLI
  users had written a Bash allow rule (43% an interpreter wildcard, about 5% allow any shell
  command); 25% of interactive sessions start in bypass.
- The HN thread on the default flip split roughly: bypass ~40%, bypass inside a container or VM
  ~30%, manual ~15%, auto ~10%, narrow allowlists or hooks ~5%. Exhaustive per-command allowlists
  like this repo's are rare.
- Classifier quality: Anthropic reports 0.4% false positives on real traffic and **17% false
  negatives** on real overeager actions (its own "honest number"), 5.7% on synthetic exfiltration.
  The arXiv stress test on underspecified DevOps scope escalation measured 81% end-to-end false
  negatives — a different workload, not a refutation. **In-project Edit/Write never reaches the
  classifier**, and both independent tests saw a blocked shell write re-done as a file edit.
- Blocked by default: force push, `git reset --hard`, `git clean -fd`, `curl | bash`, exfiltration,
  remote changes the user did not name, merging unapproved PRs, disabling CI. Allowed by default:
  pushing to any branch of the current repo except deploy-like names, creating PRs that match the
  request, reading `.env` and sending credentials to their matching API.

[DECISION: **auto is good enough for this machine's work, because the residual misses land on things
a rebuild or a revert recovers.** The user's threat model is a mess in GitHub or in the OS, and
PULSE rebuilds the OS. The 17%/81% miss rates are the cost; acceptEdits' alternative is a human
approving 97% of prompts reflexively, which Anthropic's own tester study puts at 13.6% of dangerous
commands caught. It beat staying on acceptEdits, which nobody actually runs, and bypass, which drops
the default blocks on force push and history discards that cover the "mess in GitHub" class.]

[DECISION: **`git push`, `git commit` and GitHub PR operations stop prompting — user decision,
2026-11-08.** This reverses the standing "push/commit need their say-so" rule. It beat keeping the
ask rules, whose prompts were approved as routine. The user's words, on being asked about commit:
_"commit and push should go unprompted, but we should make sure we have rules for how to write
commits descriptively, so we can walk the githistory without having to check out files to understand
what happened. also, we don't want force pushes and history changes to be allow automatically, if
possible."_]

[DECISION: **force pushes and history rewrites keep a deterministic prompt — user decision,
2026-11-08.** The classifier already blocks force push and `reset --hard` by default, but a default
is a judgement that can pass when the user's request appears to cover it (Backslash: every requested
force push was cleared). An ask rule resolves before the classifier and always prompts, which is the
"not allowed automatically" the user asked for. It beat leaving these to the classifier.]

[PITFALL: **two things a rebuild cannot recover stay outside that threat model, and they are what
the remaining rules are for.** A leaked credential (an SSH key, the gh token) is a real-world
problem however clean the OS reinstall is. A push to a public repo is irreversible: history stays
readable after any later edit, which is the whole of `config/agents-md/git.md`'s confidentiality
rule. With push unprompted, `plans.py scan --mode staged` before each commit becomes the only check
standing between a private name and a public remote — there is no longer a prompt at which to
notice.]

## Design sketch

1. **`claude_default_mode = "auto"`** in `setup.toml`, rewriting the comment block above it, which
   still argues for acceptEdits. Synced by `inv ai.install-skills`.
2. **Keep every deny rule** in `claude_permissions_deny` unchanged. Deny is the one control auto
   cannot loosen, and those seven rules cover the credential half of the pitfall above.
3. **Remove the ask rules for plain `git push` and `gh pr *`, and do not replace them with allow
   rules.** An allow rule resolves before the classifier, so `Bash(git push *)` as allow would also
   pass `git push --force` unseen — Backslash measured exactly that with `Bash(git:*)`. Left
   unmatched, both go to the classifier, which allows an ordinary push and blocks a force push or a
   push to a deploy-named branch. This also closes the `git -C <repo> push` gap from
   `plans/2026-08-22-compound-command-permission-audit.md` for free: both forms now get the same
   classifier verdict instead of one prompting and one not. The same for `git commit`: its ask rule
   goes, unreplaced.
4. **Add ask rules for every force-push and history-rewrite shape**, so they prompt rather than
   reach the classifier: `git push` with `--force`, `-f`, `--force-with-lease`,
   `--force-if-includes`, `--mirror`, `--delete`/`-d`, or a `+<refspec>`; `git commit --amend`;
   `git rebase`; `git filter-branch`, `git filter-repo`; `git reset` with
   `--hard`/`--merge`/`--keep` (already ask overrides); `git update-ref -d`; `git reflog expire`;
   `git gc --prune=now`. Written as `ask_overrides` in `cli-allowlist/tools.toml`'s `[git]` table,
   the existing mechanism.
5. **Keep ask rules on what publishes or destroys outside a PR**:
   `gh release create/delete/edit/upload`, `gh repo delete/archive/rename/edit` (visibility lives
   under `edit`), `gh secret`, `gh api` with a mutating method. The line is "acts on something other
   than a branch, a commit or a PR of a repo the user owns".
6. **Shrink what remains.** Under auto, an allow rule only buys skipping the classifier call
   (latency; HN's main complaint was a slow classifier), and an ask rule on a reversible local
   command is a prompt nobody needs. So the 445 allow rules can stay as a speed optimisation, and
   most of the 689 asks should go. `cli-allowlist/` keeps owning the rules; what changes is how
   verdicts render.
7. **Make commit messages carry the history on their own.** With commit unprompted, nobody reads a
   message before it lands, so the message rule is the only quality control left. The bar the user
   set: a reader walking `git log` understands what happened **without checking out a file**.
   `config/agents-md/git.md` already requires a body (what the change is for, what it beat, what it
   cost); what it does not yet say is that the body must name **what changed** in enough concrete
   terms — which behaviour, which setting, which file's role — that the diff is confirmation rather
   than the explanation. Measure first: sample recent commits across the personal repos against that
   bar before rewording, per the adherence-not-wording lesson in
   `plans/2026-08-28-auto-mode-contradicts-bash-rules.md`.
8. **Update the instructions that assume acceptEdits or push approval**:
   `config/agents-md/collaboration.md:32` ("Push/commit still need their say-so"),
   `config/agents-md/bash.md`'s "The permission model in force" ("Sessions on this machine run in
   `acceptEdits` mode"), and `docs/claude-code.md`'s `claude_default_mode` section. `git.md`'s "a
   local commit is not a private holding state" gets sharper, not wrong: with push free, a commit is
   now the publishing decision in practice.

## Open questions

[NEEDS CLARIFICATION: **can an ask rule catch a force push behind a global option or a refspec?**
Ask rules are prefix matches, so `Bash(git push --force*)` misses `git push origin main --force` and
`git -C <repo> push -f` — the same gap `plans/2026-08-22-compound-command-permission-audit.md` found
for push itself. The docs say `*` works mid-pattern and spans arguments (`Bash(git * --force*)`),
and that an ask rule "matching command content" falls back to a prompt in auto, but a 2026-09-26
finding says a mid-pattern `*` is read literally when the rule ends in `:*`. Probe every shape with
`inv allowlist.check-claude` before trusting the list in design step 4. If a shape cannot be
expressed, the classifier's default block is what remains for it — "if possible" in the user's
words.]

[NEEDS CLARIFICATION: **does "GitHub operations on PRs" include `gh pr merge`?** The classifier
blocks "merging unapproved PRs" by default, and on a sole-contributor personal repo no PR is ever
approved by anyone else, so removing the ask rule alone may turn a prompt into a classifier denial.
If merge is meant, the fix is an `autoMode.allow` entry or an `autoMode.environment` line declaring
the personal repos trusted — check `code.claude.com/docs/en/auto-mode-config` for the schema, and
whether a new `claude_auto_mode` field on `[packages.claude-code]` is needed to declare it.]

[NEEDS CLARIFICATION: **how does `cli-allowlist` express "leave this unmatched on purpose"?** Today
a verb renders as allow or ask; there is no third verdict meaning "defer to the classifier".
Removing `push` from the `[git]` tree would also lose its classification. Candidates: a
`defer_overrides` list beside `allow_overrides`/`ask_overrides`, or a per-mode render switch keyed
on `claude_default_mode`. The second would keep the acceptEdits rendering correct if the mode is
ever switched back.]

[NEEDS CLARIFICATION: **which ask rules survive the shrink?** Proposed line in design step 4; the
full list needs one pass over `cli-allowlist/` verdicts, and Anthropic's `claude auto-mode defaults`
output shows which of them the classifier already blocks, which makes an ask rule for those
redundant rather than protective.]

[NEEDS CLARIFICATION: **what happens to `plans/2026-08-28-auto-mode-contradicts-bash-rules.md`?**
Making auto the default makes its note — use `cat`/`sed`/`grep`, Grep withdrawn — permanent in every
session. That plan's evidence says announcing a refusal does not hold over long sessions. Accept the
drift as the price, or resolve it there first.]

[DEFERRED: **the Bash sandbox** from
`plans/2026-09-05-web-tool-permissions-and-what-auto-actually-buys.md` stays the only OS-enforced
egress boundary and the honest fix for exfiltration. That plan ordered "revisit
`claude_default_mode`" last, after the sandbox; this plan deliberately goes first, because the
user's threat model makes the sandbox an improvement rather than a prerequisite. Update that plan's
step 4 to point here when this lands.]

## Recommended direction

Answer the merge and ask-rule-shape questions, then land in this order: the commit-message
measurement and any `git.md` tightening first (commits stop being read before they land, so the rule
has to be right before that happens); the instructions fragments and `setup.toml` mode switch
together (one deploy, so no session runs auto under rules that still say acceptEdits); then the
`cli-allowlist` render change, the force-push and rewrite ask rules, and the ask-rule shrink,
verified with `inv allowlist.check-claude` and live probes in a throwaway repo with a remote —
`git push` runs, `git push --force`, `git push origin +main`, `git -C <repo> push -f` and
`git commit --amend` each prompt — so every verdict is observed rather than assumed.

## Sources

- https://claude.com/resources/articles/auto-mode-default-in-claude-code
- https://www.anthropic.com/engineering/claude-code-auto-mode
- https://code.claude.com/docs/en/permission-modes
- https://arxiv.org/html/2604.04978v1
- https://www.backslash.security/blog/claude-code-auto-mode-catches-a-lot-but-not-everything
- https://news.ycombinator.com/item?id=49239021
