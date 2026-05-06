# Feature: Honesty / State-Bridge Resilience Fix

**Feature ID**: FEAT-1B452
**Parent Review**: [TASK-REV-1B452](../../in_review/TASK-REV-1B452-honesty-verification-false-fail-after-state-bridge-move.md) — architectural review v2 (causal-chain validated)
**Review report**: [.claude/reviews/TASK-REV-1B452-review-report.md](../../../.claude/reviews/TASK-REV-1B452-review-report.md)
**Created**: 2026-05-06

## Problem statement

During FEAT-FFC3 Wave 3 autobuild on 2026-05-06, a complete and correct Player turn (28 minutes, 25 SDK turns, 26 passing tests, 16 ACs covered) was marked `error`. Production code was correct on disk; the framework rejected the work on a bookkeeping technicality, and the manual recovery (YAML status flip) bypassed the Coach gate entirely.

**Root cause** (validated end-to-end against running code in the v2 review):

A structural collision between three individually-correct design decisions in the autobuild orchestrator:

1. `state_bridge.transition_to_design_approved` uses `shutil.move` (not `git mv`) — runtime state, not commit-worthy.
2. `_detect_git_changes` uses `git diff --name-only <baseline>` without `-M` — rename detection is heuristic and parallel-wave-unsafe.
3. `_record_baseline` runs *before* `_ensure_design_approved_state` — baseline must precede SDK invocation for parallel-wave attribution.

Each is correct in isolation. Together: the post-turn `git diff --name-only` reports the state-bridge move as a tracked-file delete in `tasks/backlog/...`. The orchestrator's union-merge at [`agent_invoker.py:2796-2797`](../../../guardkit/orchestrator/agent_invoker.py) then injects this orchestrator-induced ghost path into the Player's `files_modified`. CoachVerifier (wired into the deterministic Coach path by TASK-AB-FIX-INVAB1, commit `b9a45694`) checks `Path.exists()` for every claim, the ghost path doesn't exist (file is in `tasks/design_approved/` now), and the short-circuit at [`coach_validator.py:850-872`](../../../guardkit/orchestrator/quality_gates/coach_validator.py) drops 16 ACs.

**The Player has no direct role.** The path the verifier flags as a "lie" was never in the Player's report — the orchestrator put it there.

## Solution approach

Three layers of fix, defence-in-depth:

- **Layer 1** (load-bearing) — TASK-FIX-1B4A: identity-based canonical-path resolution in `CoachVerifier`. When a path doesn't exist, ask state_bridge for the task's current canonical path; if found and exists, suppress the discrepancy.
- **Layer 3'** (preventative) — TASK-FIX-1B4C: filter orchestrator-induced state-bridge moves out of the union-merge in `_create_player_report_from_task_work`. The ghost path never reaches the Coach.
- **Layer 2** (robustness) — TASK-FIX-1B4B: demote single path-only honesty discrepancies from `must_fix` to `should_fix` so AC verification continues even if a residual case slips through.
- **Documentation** — TASK-DOC-1B4D: add `.claude/rules/path-string-mismatch-is-not-dishonesty.md` as inverse-shape sibling of `absence-of-failure-is-not-success.md`.

Layers 1 and 3' are both load-bearing — either alone closes the FFC3 reproducer. Together they provide independent defence at the source (3' filters before injection) and at the consumer (1 resolves before flagging). Layer 2 is the safety net if both upstream layers miss an edge case.

## Subtasks

| ID | Title | Wave | Mode | Workspace | Depends on |
|----|-------|------|------|-----------|------------|
| [TASK-FIX-1B4A](TASK-FIX-1B4A-canonical-path-resolution.md) | Canonical-path resolution in CoachVerifier (Layer 1) | 1 | task-work | honesty-fix-wave1-1 | — |
| [TASK-FIX-1B4C](TASK-FIX-1B4C-filter-orchestrator-induced-ghosts.md) | Filter orchestrator-induced ghost paths at union-merge (Layer 3') | 1 | task-work | honesty-fix-wave1-2 | — |
| [TASK-FIX-1B4B](TASK-FIX-1B4B-demote-single-honesty-discrepancy.md) | Demote single path-only honesty discrepancies (Layer 2) | 2 | task-work | honesty-fix-wave2-1 | TASK-FIX-1B4A |
| [TASK-DOC-1B4D](TASK-DOC-1B4D-sibling-rule-false-red.md) | Sibling rule for false-red shape | 3 | direct | honesty-fix-wave3-1 | TASK-FIX-1B4A, TASK-FIX-1B4C |

**Wave-1 ship criteria**: TASK-FIX-1B4A and TASK-FIX-1B4C must both land before next autobuild attempt. They are independent in code (touch different files: 1B4A → state_bridge + coach_verification + coach_validator; 1B4C → state_bridge + agent_invoker). Run in parallel.

## Out of scope

Two additional bugs documented in the FEAT-FFC3 incident doc are tracked under pre-existing tasks (not duplicated here):

- **Bug 2** (`_record_honesty()` AttributeError on `None` honesty_data, `autobuild.py:4376`) — covered by [TASK-REV-7E3F1](../TASK-REV-7E3F1-record-honesty-attributeerror-on-none-payload.md) (review) and [TASK-FIX-7E3F](../../in_progress/TASK-FIX-7E3F-record-honesty-none-payload-regression.md) (fix, in_progress).
- **Bug 3** (`--resume` cannot finalize feature with all tasks completed, `feature_orchestrator.py:973`) — bundled into TASK-FIX-7E3F per the user's scoping decision.

Also out of scope:
- TASK-FIX-1B452-D (Coach Override / YAML-flip replacement) — deferred until 2-4 weeks of post-fix data show whether the override mechanism is needed.
- Broader rework of state_bridge mid-turn semantics — flagged for a future review if false-fails recur after Layers 1+3' land.
