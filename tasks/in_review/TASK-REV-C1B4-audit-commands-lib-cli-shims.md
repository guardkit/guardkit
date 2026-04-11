---
id: TASK-REV-C1B4
title: Audit installer/core/commands/lib for dead CLI shims and misfiled modules
status: review_complete
created: 2026-04-11T16:10:00Z
updated: 2026-04-11T17:45:00Z
priority: low
tags: [review, cleanup, technical-debt, commands-lib, cli-shims]
task_type: review
review_mode: technical-debt
review_depth: standard
parent_task: TASK-FIX-E841
complexity: 3
depends_on: []
review_results:
  mode: technical-debt
  depth: standard
  findings_count: 7
  recommendations_count: 7
  decision: pending_checkpoint
  report_path: .claude/reviews/TASK-REV-C1B4-review-report.md
  completed_at: 2026-04-11T17:45:00Z
---

# Task: Audit `installer/core/commands/lib/` for dead CLI shims and misfiled modules

## Background

Surfaced by [TASK-FIX-E841](../in_review/TASK-FIX-E841-repair-or-deprecate-template-validate-cli.md), which deleted
`installer/core/commands/lib/template_validate_cli.py` — a broken shim that imported a non-existent
`global.lib.template_validation` module. The same task also deleted the companion test file
`tests/integration/test_template_validation_cli.py`, which was itself dead (undefined `parse_args` symbol, stale
`@patch('global.commands.lib.template_validate_cli...')` targets). Both files had been broken for an unknown amount
of time with no user impact reports.

The E841 decision to deprecate (not repair) was made because `/template-validate` runs as a Claude Code slash command
driven by `installer/core/commands/template-validate.md` + subagent, with the authoritative orchestrator living at
`installer/core/lib/template_validation/`. The Python CLI shim next to the markdown file was never the live execution
path.

While investigating E841, two broader concerns came into view that were **explicitly out of scope** for that task but
are worth a dedicated review:

### Concern 1 — Are there other dead CLI shims?

After deleting `template_validate_cli.py`, the only remaining `*_cli.py` file in `installer/core/commands/lib/` is
`upfront_complexity_cli.py`. A quick glance suggests it is structurally different from the broken shim (uses relative
imports with a `try/except ImportError` fallback, not the broken `global.*` dotted path), but this has not been verified
end-to-end. It is possible it works, it is possible it is dead, and it is possible it is partially working but hit by
the same kind of silent rot that killed `template_validate_cli.py`.

**Key questions**:
- Is `upfront_complexity_cli.py` actually invoked anywhere (by a shell script, a skill, a hook, a slash command, a
  symlink in `~/.agentecflow/bin/`, or CI)?
- Does `python3 installer/core/commands/lib/upfront_complexity_cli.py --help` run end-to-end without import errors?
- If it is invoked, is its invocation path still pointing at a valid location, or is it another stale pointer waiting
  to fail?
- If it is not invoked anywhere, should it be deleted (same rationale as E841), kept as a dev utility, or relocated?

### Concern 2 — Is `commands/lib/` a misnamed "kitchen sink" directory?

A broader observation: `installer/core/commands/lib/` contains ~80+ files and is doing much more than "CLI support
for slash commands". It includes:

- **Test files in a non-test location**: `test_agent_invocation_tracker.py`, `test_agent_invocation_validator.py`,
  `test_complexity.py`, `test_complexity_comprehensive.py`, `test_enforcement_resilience.py`, `test_full_review.py`,
  `test_fulltext_fix.py`, `test_micro_basic.py`, `test_micro_task_detector.py`, `test_micro_workflow.py`,
  `test_phase_gate_validator.py`, `test_plan_integration.py`, `test_plan_markdown.py`, `test_quick_review.py`,
  `test_refinement_handler.py` — these appear to be genuine pytest files sitting inside the library directory rather
  than `tests/`. Are they picked up by the pytest collector? Do they still pass? Were they meant to be moved?
- **Demo scripts**: `demo_agent_tracker_integration.py`, `demo_phase_gate_integration.py`, `demo_plan_markdown.py`,
  `demo_template_qa.py`, `verify_micro_implementation.sh`.
- **Multiple `README*.md` and `*_README.md` and spec `.md` files** (`README.md`, `README-CHECKPOINT-DISPLAY.md`,
  `README-PLAN-MODIFIER.md`, `QUICK-START-PLAN-MODIFIER.md`, `QUICK_REVIEW_API.md`, `AGENT_TRACKER_INTEGRATION.md`,
  `MICRO_TASK_README.md`, `graphiti-preamble.md`) mixed in with Python modules.
- **Multiple versions of the same Graphiti diagnosis script**: `graphiti_diagnose.py`, `graphiti_diagnose_v2.py`,
  `graphiti_diagnose_v3.py` — is the version history intentional, or are the older versions dead?
- **Genuine command-support libraries** (the intended content): e.g., `agent_discovery.py`, `clarification/`,
  `complexity_*.py`, `plan_*.py`, `phase_execution.py`, `phase_gate_validator.py`, etc. These are the files actually
  imported by slash commands and orchestrators.

This is not a bug in itself — the directory works — but the mixing of concerns is the exact environment where silent
rot (like the E841 shim) goes unnoticed for a long time. A clean-up may be warranted, or at minimum a conscious
decision about what belongs here.

## Description

This is a **review task** — analyse first, recommend second, **do not implement** as part of this task. The output is a
review report with concrete follow-up recommendations, to be filed as separate implementation tasks via `/task-review`'s
`[I]mplement` decision path.

### Analysis Objectives

**Primary (E841 follow-up)**:

1. **Audit every remaining `*_cli.py` file in `installer/core/commands/lib/`** (currently just
   `upfront_complexity_cli.py`, but verify the glob at review time in case more exist). For each file:
   - Attempt to import it: `python3 -c "from installer.core.commands.lib.<name> import *"` — does it work?
   - Run `--help` if it has a `main()`: does it execute end-to-end?
   - Grep the entire codebase (excluding historical artifacts: `.claude/reviews/`, `docs/reviews/`, `docs/archive/`,
     `tasks/completed/`, `tasks/archived/`, `.claude/state/backup/`) for invocations of the file, its module path, or
     any bin-directory symlink that points at it.
   - Check `~/.agentecflow/bin/` (documented install location per E841's removed "Command Execution" section) for any
     symlinks matching the `*-cli` pattern that map back to this file.
   - Check whether the slash command it supposedly backs (by name) actually uses it, or uses a different execution
     path (subagent, direct Python orchestrator call, etc.).
   - Classify: **live** / **dead** / **unknown** (needs owner input).

**Secondary (directory hygiene)**:

2. **Classify every file in `installer/core/commands/lib/`** at a high level. You do not need to read every file in
   depth — the goal is a shape-check, not a content audit. Categories:
   - `command-library` — imported by a slash command or an orchestrator that a slash command invokes
   - `test-file` — pytest file (starts with `test_`, contains `def test_*`)
   - `demo-script` — contains `demo_` in name, or is a manual runner
   - `documentation` — `.md` files
   - `shell-script` — `.sh` files
   - `versioned-duplicate` — has a `_v2`, `_v3`, etc. suffix where older versions may or may not still be live
   - `orphan` — file that no other file in the codebase imports, and that is not independently runnable as a CLI
3. **Report counts per category** and list any notable orphans or versioned duplicates.
4. **Confirm (or refute) the hypothesis** that `test_*.py` files in `commands/lib/` are being collected and run by
   pytest. Check the `pytest.ini` / `pyproject.toml` test discovery config. Do they run? Do they pass? Should they be
   moved to `tests/`?
5. **Identify the live purpose of each `graphiti_diagnose*.py` version**. Is `v3` the current one and `v1`/`v2`
   abandoned? If so, the older versions are candidates for deletion.

### Non-Objectives (Out of Scope)

- Do **not** refactor or move any files as part of this task. All changes happen in follow-up implementation tasks.
- Do **not** audit `installer/core/lib/` (the real library directory) or `installer/core/agents/` — scope is strictly
  `commands/lib/`.
- Do **not** investigate individual orchestrator correctness, complexity of internal logic, or design quality. The
  concern here is "is this file alive or dead, and does it belong here?" — not "is this file good?".
- Do **not** touch or re-audit files that E841 already addressed (`template_validate_cli.py`,
  `test_template_validation_cli.py`, the "Command Execution" note in `template-validate.md`).

## Acceptance Criteria

- [ ] Produce a review report at `.claude/reviews/TASK-REV-C1B4-review-report.md` (the standard `/task-review` output
      location) containing:
  - [ ] **Section 1 — CLI shim audit**: One subsection per `*_cli.py` file found in `installer/core/commands/lib/`,
        with classification (live / dead / unknown), the exact evidence used (import check result, invocation search
        results, symlink check), and a recommendation (keep / delete / investigate further / relocate).
  - [ ] **Section 2 — Directory classification summary**: Counts per category, list of orphans (if any), list of
        versioned duplicates (if any).
  - [ ] **Section 3 — Test file location finding**: Concrete answer to "are `test_*.py` files in `commands/lib/`
        collected by pytest, and if so should they be moved to `tests/`?" — with evidence (pytest config inspection,
        collection output, or pass/fail status).
  - [ ] **Section 4 — Graphiti diagnose versioning finding**: Concrete answer to "which version of
        `graphiti_diagnose*.py` is live, and are the others dead?"
  - [ ] **Section 5 — Recommended follow-up tasks**: A numbered list of discrete, individually-actionable tasks
        (format: `TASK-FIX-{hash}`, `TASK-REF-{hash}`, `TASK-TSE-{hash}`, etc. — do not generate hashes, leave as
        `{hash}`), each with a one-sentence rationale and a suggested priority. These become the `[I]mplement` output
        if the reviewer chooses that decision path in `/task-review`.
- [ ] The review report must **not** contain any code changes or implementation — only analysis and recommendations.
- [ ] The review must be runnable via `/task-review TASK-REV-C1B4` and reach a decision checkpoint
      (Accept / Implement / Revise / Cancel) at the end.

## Notes on Execution

- Use the `/task-review` command (not `/task-work`) — this is a review task and the workflow is different.
- Favor the `Explore` or `general-purpose` subagent for the directory-shape classification step (Section 2), since
  it spans many files and benefits from parallel reads; reserve the main conversation context for synthesis and the
  final report.
- For Section 1 (CLI shim audit), do the import check **in-process** with `python3 -c "..."` exactly as E841 did, so
  the evidence format matches and the audit style is consistent across both tasks.
- Treat historical artifacts (`.claude/reviews/`, `docs/reviews/`, `docs/archive/`, `tasks/completed/`,
  `tasks/archived/`, `.claude/state/backup/`) as read-only evidence only — never propose edits to them, and filter
  grep results to exclude them when counting "live" references.

## References

- Parent fix task (deleted the first dead shim): [TASK-FIX-E841](../in_review/TASK-FIX-E841-repair-or-deprecate-template-validate-cli.md)
- Grandparent reviews that surfaced the original side note:
  - [TASK-REV-A5F8](../in_review/TASK-REV-A5F8-analyse-d0c1-followups-scaffolding-and-exemplar.md) — Section 1 "On the 'broken template_validate_cli.py' side note"
  - [TASK-REV-D0C1](../in_progress/TASK-REV-D0C1-register-dotnet-railway-fastendpoints-template.md) — original "Side Note (Not in Scope)"
- Target directory: [installer/core/commands/lib/](../../installer/core/commands/lib/)
- Authoritative orchestrator directory (for comparison of what a "live" shim should route to):
  [installer/core/lib/](../../installer/core/lib/)
