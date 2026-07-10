---
format_version: 1
---

# Task Complete - Finalize Task with Feature/Epic Progress Rollup

Finalize a task through the **shared atomic completion routine** — the single
completion path also used by task-work § Phase 6 (Green) and, post-merge, by
feature-complete. This slash command is a **thin wrapper** over
`guardkit task complete`; it validates the pre-completion gates, then delegates
the mechanical finalize (atomic status-flip + move, archival, rollup, PM sync,
fleet-memory capture-outcome, conductor git-state commit) to the CLI.

> **Demotion note (task-complete-demotion-scope §7, Phase 1, 2026-07-10):** the
> file-move + status-flip that used to be hand-rolled bash here is now the ONE
> atomic routine `installer/core/commands/lib/task_completion_helper.complete_task`
> (exposed as `guardkit task complete`). Completing where the work finishes —
> task-work § Phase 6 with `--complete` — is the preferred path; this slash
> surface remains for manual / operator_handoff / reopen cases and retires only
> in the demotion scope's final phase (PB-2/PB-3 tombstone).

## Usage
```bash
/task-complete TASK-XXX [options]
```

## Examples
```bash
# Complete a task (normal path — from IN_REVIEW)
/task-complete TASK-045

# Complete without triggering rollup (batch operations)
/task-complete TASK-045 --no-rollup

# Force sync to external PM tools
/task-complete TASK-045 --force-sync
```

## Completion Validation Process

### Pre-Completion Checks (AI-verified before delegating)

Before invoking `guardkit task complete`, confirm:

1. **Acceptance Criteria**: All criteria satisfied
2. **Implementation Steps**: All steps complete
3. **Quality Gates**: Tests pass, coverage met, security clean
4. **Code Review**: Implementation reviewed and approved
5. **Documentation**: Required documentation completed
6. **External Dependencies**: No blocking dependencies remain

### State Transition (location-agnostic)

```
Status: IN_REVIEW → COMPLETED
```

`IN_REVIEW` is the normal task-work terminal state ("the ONLY path to
IN_REVIEW"). The completion routine is **location-agnostic** — `find_task_file`
resolves the task wherever it currently lives (in_review, in_progress, blocked,
design_approved, …), so a task completed directly from an earlier state is
handled without special-casing. (This corrects the earlier `IN_PROGRESS`-only
prose — demotion scope §4 Phase 0.)

### File Organization on Completion

The routine performs an **atomic status-flip + file-move** — one operation, so
"completed but sitting in backlog" is unrepresentable (the WS3-S8 guarantee):

```bash
tasks/completed/YYYY-MM/
└── TASK-045-<slug>.md            # flipped to status: completed, then landed
```

Related root-level artefacts (`TASK-045-IMPLEMENTATION-SUMMARY.md`,
`TASK-045-COMPLETION-REPORT.md`, coverage JSON) and the `.claude/task-plans/`
implementation plan are archived alongside. Idempotent; failures to archive an
individual file are logged and never block completion.

## Delegation — invoke the shared routine

After the pre-completion checks pass, delegate the finalize to the CLI:

```bash
guardkit task complete TASK-XXX
```

This single command carries, in order:

1. Pre-completion carve-out gates + fail-closed `qa.enforce_tier1` (when on);
2. **Atomic status-flip + file-move** into `tasks/completed/YYYY-MM/`;
3. Related-file archival;
4. Feature → Epic → Portfolio rollup + external PM sync (`--no-rollup` honoured);
5. fleet-memory `capture-outcome` (the learning flywheel's write path —
   best-effort, **loud on failure**);
6. Conductor git-state commit (`docs/state/{task_id}/`; non-blocking).

Carve-outs enforced by the routine / `guardkit task complete`:

- `--autobuild-mode` → **REFUSED**: feature-build merges BEFORE completion; the
  autobuild lane finalizes via feature-complete calling the same routine
  post-merge (guard metric: no completion for an unmerged branch).
- `task_type: operator_handoff` → their completion path is feature-complete;
  auto-finalize is refused (Phase 6), while the deferred manual completion is
  still available through this routine.

## Quality Assurance Integration

Quality gates must pass before completion: coverage ≥80%, tests 100%, security
clean, code review approved. When `qa.enforce_tier1` is on for the repo, the
routine additionally fails CLOSED unless the pinned F1 pass bar predates the work
and the known-failure ledger sweep is clean (WS2-B2).

## Fleet-Memory Knowledge Capture (Write Path)

The routine runs `guardkit memory capture-outcome --from-task-file <moved-file>
--success` as a best-effort, non-blocking step (loud log on failure). Task
completion MUST succeed even if the fleet-memory write fails. If the task
recorded **architectural decisions**, capture each as an `adr` payload via
`mcp__fleet_memory__memory_write_payload` (MCP write tool required — the CLI only
writes `build_outcome`). See `docs/internals/commands-lib/memory-preamble.md`.

## Git State Commit (Conductor Support)

The routine commits `docs/state/{task_id}/` via `git_state_helper.commit_state_files`
so completed-task state is visible across Conductor.build worktrees. Non-blocking:
a git failure is logged and never fails completion. Does NOT commit the task file
itself (handled by the atomic move) and does NOT push to remote.
