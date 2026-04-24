# AutoBuild SDK Stall Resilience

**Feature ID**: FEAT-7A00
**Parent review**: [TASK-REV-E4F5](../../in_review/TASK-REV-E4F5-analyse-forge-autobuild-failures-gb10.md) —
architectural review of forge FEAT-FORGE-002 autobuild failures on GB10
**Sibling review**: [TASK-REV-JMBP](../../in_review/TASK-REV-JMBP-analyse-jarvis-FEAT-J002-autobuild-failure-on-macbook-pro.md) —
architectural review of jarvis FEAT-J002 autobuild failure on MacBook Pro (2026-04-24; added
TASK-FIX-7A07 and amended TASK-FIX-7A04 per its Workstream D decision D1)
**Review report**: [.claude/reviews/TASK-REV-E4F5-review-report.md](../../../.claude/reviews/TASK-REV-E4F5-review-report.md)
**Sibling review report**: [docs/reviews/TASK-REV-JMBP-jarvis-autobuild-mbp-review.md](../../../docs/reviews/TASK-REV-JMBP-jarvis-autobuild-mbp-review.md)
**Status**: Backlog
**Created**: 2026-04-24
**Updated**: 2026-04-24 (+TASK-FIX-7A07)

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

Seven subtasks across two waves, addressing all five original weaknesses *plus*
the `coach_agent_invocations_stall` classification gap surfaced by TASK-REV-JMBP:

- **Wave 1** (4 parallel, disjoint files) — the primary fixes
- **Wave 2** (3 parallel-with-rebase, same-file dependencies) — the
  summary/interpreter/feedback-refinement layer on Wave 1

See [IMPLEMENTATION-GUIDE.md](./IMPLEMENTATION-GUIDE.md) for the execution
strategy (Conductor workspaces, testing depth, verification plan).

## Subtasks

| Task | Title | Wave | Mode | Complexity | Review ref |
|---|---|---|---|---|---|
| [TASK-FIX-7A01](./TASK-FIX-7A01-pin-sdk-log-version.md) | Pin claude-agent-sdk + log version at startup | 1 | task-work | 3 | E4F5 R1 / F1 |
| [TASK-FIX-7A03](./TASK-FIX-7A03-defensive-sdk-message-handling.md) | Defensive SDK message handling in streaming loop | 1 | task-work | 4 | E4F5 R3 / F2 |
| [TASK-FIX-7A04](./TASK-FIX-7A04-bootstrap-hardfail-gate.md) | Bootstrap hard-fail gate (`bootstrap_failure_mode`) + requires-python pre-check | 1 | task-work | 4 | E4F5 R4a / F6; **+JMBP W-E** |
| [TASK-DOC-7A06](./TASK-DOC-7A06-runbook-and-graph-seed.md) | Stall runbook + knowledge-graph seed | 1 | direct | 2 | E4F5 R5+R6+R7 |
| [TASK-FIX-7A02](./TASK-FIX-7A02-player-invocation-stall-classification.md) | `player_invocation_stall` classification at summary layer | 2 | task-work | 5 | E4F5 R2 / F3+F4 |
| [TASK-FIX-7A05](./TASK-FIX-7A05-wire-venv-to-coach-pytest.md) | Wire bootstrap venv into Coach pytest | 2 | task-work | 5 | E4F5 R4b / F7 |
| [TASK-FIX-7A07](./TASK-FIX-7A07-coach-agent-invocations-stall-classification.md) | `coach_agent_invocations_stall` classification + recovery feedback + mixed_partial_failure verdict | 2 | task-work | 5 | **JMBP D1 / W-B+C+F** |

## Success Criteria (feature-level)

The feature is done when:

- FEAT-FORGE-002 Wave 1 completes on GB10 (requires TASK-FIX-7A01's SDK
  upgrade to be applied on that host — the task covers the code change;
  the host upgrade is a manual verification step).
- Replaying the two saved GB10 transcripts through the final-summary code
  produces `player_invocation_stall` with the new hint, not the
  task-blaming generic hint.
- Replaying the jarvis-FEAT002-run-1 preserved evidence (J002-008, J002-013
  task_work_results + coach_turn_{5,6}) through the summary renderer
  produces `coach_agent_invocations_stall` with the enriched Coach feedback
  naming the specific sub-agents to invoke, and review-summary.md
  distinguishes the two stall types and any co-fire (e.g.
  `coach_agent_invocations_stall + context_pollution`).
- `guardkit.orchestrator` unit tests cover: unknown-SDK-message per-message
  drop; `ValueError` error-class preservation; `bootstrap_failure_mode=block`
  hard-fail; `requires-python` pre-check; Coach interpreter selection via
  bootstrap venv; coach_agent_invocations_stall classifier (including
  missing_phases ordering robustness); mixed_partial_failure verdict.
- Runbook section exists and links back to TASK-REV-E4F5, TASK-REV-JMBP,
  and TASK-REV-8A08.
- Graphiti knowledge graph contains: the "player-invocation-stall
  distinction" fact (7A02), the "coach-agent-invocations-stall distinction"
  fact (7A07), and the bimodal `implementation_mode` routing rule (7A07)
  under `guardkit__project_decisions`.

## Prior Art

- **TASK-REV-8A08** (FEAT-486D / TASK-AD-004 stall, 2026-04-13) — first
  incident of the same class-of-defect. At that time the `"SDK API error"`
  hint branch did fire because Coach feedback included the substring;
  here it doesn't.
- **TASK-REV-MCPS** (2026-04-24) — namespace-hygiene rule, separate
  class-of-defect. Confirmed not triggered on the GB10 forge runs; for
  the MBP jarvis run, the MCPS fixes (TASK-FIX-MCPS.1/.2) were
  **empirically validated** — the first invocation hit the collision, the
  post-fix re-invocation completed Wave 1 cleanly.
- **TASK-REV-JMBP** (2026-04-24) — sibling architectural review filed
  after 7A0x was scoped. Its Workstream D decision D1 added TASK-FIX-7A07
  and amended TASK-FIX-7A04 rather than opening a parallel feature. The
  `coach_agent_invocations_stall` class it identifies is symmetric with
  `player_invocation_stall` (TASK-FIX-7A02) — together they constitute
  the core stall taxonomy for autobuild.

## Notes

- This feature lives in the **guardkit** repo, not forge. The fixes apply
  to guardkit's autobuild orchestrator, which all projects (forge, jarvis,
  specialist-agent, …) consume.
- TASK-FIX-7A04 + TASK-FIX-7A05 (bootstrap gate + venv wiring) were
  originally flagged as "split to a separate review" in the review's
  Decision Matrix. The user explicitly chose **Full scope** at the
  [I]mplement checkpoint, so they're included here. They can be deferred
  if time-boxed — Wave 1/2 structure keeps them in their own subtasks.
