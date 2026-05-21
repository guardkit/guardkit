# Architectural Review — TASK-HMIG-008R

**Reviewer**: architectural-reviewer (Phase 2.5B)
**Date**: 2026-05-21
**Plan under review**: [`implementation_plan.md`](./implementation_plan.md)
**Status**: APPROVE WITH RECOMMENDATIONS → patches applied to plan

## Scores

| Dimension | Score |
|---|---|
| SOLID | 38/50 |
| DRY | 20/25 |
| YAGNI | 18/25 |
| **Overall** | **76/100** |

## Must-address findings (all resolved in current plan)

1. **§11.2 fallback contradicts falsifier #1** — original plan said "on `gather_evidence` exception, fall back to `validate()`". That reactivates the deterministic-decision path the falsifier requires to be gone. **Resolution**: §3 "Exception handling for gather_evidence" now emits a synthetic `feedback` decision with rationale instead. `GUARDKIT_COACH_LEGACY=1` is the sole, operator-controlled, intentional revert.
2. **`None` field ambiguity** — `bundle.quality_gates = None` was indistinguishable from "gates not yet computed" vs "gate computation aborted". **Resolution**: added `gathering_status: Literal["complete", "partial_honesty_abort", "partial_gate_abort", "partial_exception"]` field to `CoachEvidenceBundle` (§2) + guard #5 in `<absence_of_failure_guards>` (§4).
3. **Duplicate honesty channel** — both the legacy `invoke_coach(honesty_verification=…)` parameter and the new `evidence_bundle.honesty` would have produced two honesty sections in the prompt. **Resolution**: §4 "Honesty channel unification" — `evidence_bundle.honesty` is single source of truth when bundle is present; legacy parameter is deprecated but tolerated for non-`_invoke_coach` callers.

## Should-address findings (noted in plan; deferred to implementer)

4. **asyncio.get_event_loop pattern is deprecated in Python 3.12+** — old plan replicated the existing fallback pattern. **Resolution**: §3 pseudocode now uses `asyncio.run(...)`.
5. **AC-016 tests wiring, not LLM behaviour** — plan §6 AC-016 now carries a docstring note that this is a wiring test only; behavioural falsifier is Wave-3 canary (TASK-HMIG-009).

## Citation drift confirmed not a blocker

The plan's AC-012 citation of `_ORCHESTRATOR_MANAGED_PATH_PATTERNS` (`agent_invoker.py:164-170`) is correct — both filters co-exist as defence-in-depth:
- Pattern-based filter (TASK-FIX-PCN, 2026-04-xx)
- `state_transitions.json`-driven filter (TASK-FIX-1B4C, 2026-05-06)
The rule file `.claude/rules/path-string-mismatch-is-not-dishonesty.md` predates TASK-FIX-PCN and is slightly stale; no action required on this task.

## Source files verified

- `guardkit/orchestrator/autobuild.py` lines 5281-5401 — regression confirmed at 5282-5301
- `guardkit/orchestrator/agent_invoker.py` lines 164-170, 1843-1947, 2174-2210 — current shape confirmed; no `evidence_bundle` parameter exists yet, so the plan is purely additive
- `guardkit/orchestrator/coach_verification.py` lines 326-400 — `_verify_files_exist` with `state_bridge.canonical_path_for` at line 364, `resolved_paths` populated at 374-380
- `guardkit/orchestrator/quality_gates/coach_validator.py` lines 779-813 (`validate()` signature), 5430-5460 (Layer 2 demotion logic)

## Implementation budget impact

| Estimate | Hours |
|---|---|
| Original plan as-written | 14-16h (§11.2 conflict would have caused rework at merge) |
| Plan with must-address patches | 12-13h (matches frontmatter `effort_hours: 12`) |

Post-patch the plan would score ≥80/100 on a re-review. Phase 2.8 checkpoint can proceed.
