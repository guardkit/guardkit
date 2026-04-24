# AutoBuild SDK Stall Resilience

**Feature ID**: FEAT-7A00
**Parent review**: [TASK-REV-E4F5](../../in_review/TASK-REV-E4F5-analyse-forge-autobuild-failures-gb10.md) —
architectural review of forge FEAT-FORGE-002 autobuild failures on GB10
**Review report**: [.claude/reviews/TASK-REV-E4F5-review-report.md](../../../.claude/reviews/TASK-REV-E4F5-review-report.md)
**Status**: Backlog
**Created**: 2026-04-24

## Problem Statement

Two consecutive `guardkit autobuild feature FEAT-FORGE-002` runs on the GB10
host (`promaxgb10-41b1`) both terminated in `UNRECOVERABLE_STALL` after 3
turns on Wave 1. The Player never ran — every turn aborted inside the SDK
layer:

- **Run 1** (pre-login): `SDK invocation failed for player: Agent player
  received API error: authentication_failed`
- **Run 2** (post-login): `SDK invocation failed for player: Unknown
  message type: rate_limit_event`

AutoBuild's feedback-stall detector then exited correctly, but the summary
hint blamed the task (`"Review task_type classification and acceptance
criteria"`) — a misattribution. The task was fine; the Player never started.

The review identified three compounding weaknesses:

1. `claude-agent-sdk` is loose-pinned (`>=0.1.0`) with no `--upgrade` on
   re-install, so GB10 had a stale SDK that predates `rate_limit_event`.
2. `agent_invoker.py`'s streaming loop wraps unknown message types in a
   blanket `except Exception` that swallows error type information.
3. The final-summary hint block matches only Coach-feedback text for
   `"SDK API error"` — it doesn't use the richer
   `player_result.error` / synthetic-report `recovery_metadata` signals
   the orchestrator already captures.

Two further latent hazards surfaced during the review (orthogonal to this
incident but worth closing):

4. `environment_bootstrap` warns on 0/N success and proceeds anyway.
5. Coach runs `pytest` against whatever PATH Python resolves to — not
   the bootstrap venv.

## Solution Approach

Six subtasks across two waves, addressing all five weaknesses:

- **Wave 1** (4 parallel, disjoint files) — the primary fixes
- **Wave 2** (2 parallel-with-rebase, same-file dependencies) — the
  summary/interpreter wiring layered on Wave 1

See [IMPLEMENTATION-GUIDE.md](./IMPLEMENTATION-GUIDE.md) for the execution
strategy (Conductor workspaces, testing depth, verification plan).

## Subtasks

| Task | Title | Wave | Mode | Complexity | Review ref |
|---|---|---|---|---|---|
| [TASK-FIX-7A01](./TASK-FIX-7A01-pin-sdk-log-version.md) | Pin claude-agent-sdk + log version at startup | 1 | task-work | 3 | R1 / F1 |
| [TASK-FIX-7A03](./TASK-FIX-7A03-defensive-sdk-message-handling.md) | Defensive SDK message handling in streaming loop | 1 | task-work | 4 | R3 / F2 |
| [TASK-FIX-7A04](./TASK-FIX-7A04-bootstrap-hardfail-gate.md) | Bootstrap hard-fail gate (`bootstrap_failure_mode`) | 1 | task-work | 4 | R4a / F6 |
| [TASK-DOC-7A06](./TASK-DOC-7A06-runbook-and-graph-seed.md) | Stall runbook + knowledge-graph seed | 1 | direct | 2 | R5+R6+R7 |
| [TASK-FIX-7A02](./TASK-FIX-7A02-player-invocation-stall-classification.md) | `player_invocation_stall` classification at summary layer | 2 | task-work | 5 | R2 / F3+F4 |
| [TASK-FIX-7A05](./TASK-FIX-7A05-wire-venv-to-coach-pytest.md) | Wire bootstrap venv into Coach pytest | 2 | task-work | 5 | R4b / F7 |

## Success Criteria (feature-level)

The feature is done when:

- FEAT-FORGE-002 Wave 1 completes on GB10 (requires TASK-FIX-7A01's SDK
  upgrade to be applied on that host — the task covers the code change;
  the host upgrade is a manual verification step).
- Replaying the two saved transcripts through the final-summary code
  produces `player_invocation_stall` with the new hint, not the
  task-blaming generic hint.
- `guardkit.orchestrator` unit tests cover: unknown-SDK-message per-message
  drop; `ValueError` error-class preservation; `bootstrap_failure_mode=block`
  hard-fail; Coach interpreter selection via bootstrap venv.
- Runbook section exists and links back to TASK-REV-E4F5 and TASK-REV-8A08.
- Graphiti knowledge graph contains the "player-invocation-stall
  distinction" fact under `guardkit__project_decisions`.

## Prior Art

- **TASK-REV-8A08** (FEAT-486D / TASK-AD-004 stall, 2026-04-13) — first
  incident of the same class-of-defect. At that time the `"SDK API error"`
  hint branch did fire because Coach feedback included the substring;
  here it doesn't.
- **TASK-REV-MCPS** (2026-04-24) — namespace-hygiene rule, separate
  class-of-defect. Confirmed not triggered here (Player reaches streaming,
  so import succeeded).

## Notes

- This feature lives in the **guardkit** repo, not forge. The fixes apply
  to guardkit's autobuild orchestrator, which all projects (forge, jarvis,
  specialist-agent, …) consume.
- TASK-FIX-7A04 + TASK-FIX-7A05 (bootstrap gate + venv wiring) were
  originally flagged as "split to a separate review" in the review's
  Decision Matrix. The user explicitly chose **Full scope** at the
  [I]mplement checkpoint, so they're included here. They can be deferred
  if time-boxed — Wave 1/2 structure keeps them in their own subtasks.
