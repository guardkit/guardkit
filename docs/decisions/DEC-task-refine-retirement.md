# DEC — Retire the `/task-refine` command

**Date:** 2026-07-09
**Status:** ACCEPTED (executed)
**Source:** the 2026-07-08 command-consolidation review session (ai-transition
`docs/guardkit-command-consolidation-review-findings-2026-07-08.md`), first item of the
ADR-C attended command-surface consolidation bundle. Authorized by Rich 2026-07-09
("please proceed with these follow ups"). Executed by the ADR-C follow-ups session.
**Scope:** `installer/core/commands/task-refine.md` + live doc/tooling references.
Historical records (docs/research, docs/reviews, .claude/state backups, past task
archives) deliberately untouched.

## Context

`/task-refine` was a standalone command operating in the IN_REVIEW/BLOCKED window after
`/task-work`: apply a targeted fix under anti-scope-creep constraints, re-run Phases
4/4.5/5, recompute state. Evidence from the consolidation review:

- **Zero inbound references**: no other command, rule, or factory program doc invoked it
  (repo-wide and ai-transition-wide grep, 2026-07-08).
- **Phantom implementation**: its claimed core module
  `installer/core/commands/lib/refinement_handler.py` does not exist — the command was
  markdown-prose-only.
- **Subset machinery**: everything it did is a subset of what `/task-work` owns; re-running
  `/task-work TASK-XXX` covers the fix-and-regate cycle, and `/task-review`'s [I]mplement
  flow covers review-findings fixes with provenance.
- **Shrinking habitat**: the planned task-work auto-completion (ADR-C sibling: the
  /task-complete demote-to-shared-routine design) eliminates the IN_REVIEW dwell the
  command operated in.

## Decision

Delete `installer/core/commands/task-refine.md`; tombstone it in
`scripts/generate_command_manifest.py` (PB-3 mechanism: install.sh prunes the installed
copy on the next run; `guardkit doctor` reports stragglers). Replacement guidance in live
docs: re-run `/task-work TASK-XXX`, or use `/task-review` [I]mplement.

## Executed

- Spec deleted; manifest regenerated (tombstone count 2 → 3).
- Live references removed/updated: `.claude/hooks/capture_slash_command.py` (allowlist),
  `installer/scripts/init-project.sh` (workflow banner), root `CLAUDE.md` + `README.md`
  (command lists), `tests/documentation/test_documentation_audit.py` (known-commands set),
  guides (`guardkit-workflow`, `GETTING-STARTED`, `quick-reference`,
  `quality-gates-integration`, `claude-code-web-setup`, `advanced`), architecture docs
  (`guardkit-system-spec`, `failure-patterns`), workflow docs (`markdown-plans`,
  `plan-modification`).
- `docs/workflows/iterative-refinement-workflow.md` carries a dated retirement banner and
  is preserved as the historical record of the workflow.
- Installed-surface prune verified by an install.sh re-run (task-refine.md gone from
  `~/.agentecflow/commands`).

## Non-goals

`/task-complete` is NOT retired by this note — its demotion to a shared atomic routine is
a separate, larger ADR-C item with its own scope doc (ai-transition
`docs/task-complete-demotion-scope-2026-07-09.md`).
