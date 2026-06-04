# Feature-run analysis — TASK-HMIG-010

> Companion to
> [`.guardkit/autobuild/TASK-REV-HMIG-feature-results.json`](../../../.guardkit/autobuild/TASK-REV-HMIG-feature-results.json)
> and [`.guardkit/autobuild/TASK-REV-HMIG-feature-target.json`](../../../.guardkit/autobuild/TASK-REV-HMIG-feature-target.json).
> Separate from [`canary-analysis.md`](canary-analysis.md) for clarity (per AC-009).
> This file is the **human-authored audit narrative** capturing *why*
> the feature run produced the verdict it did and what follow-up work it triggers.

## 0. Status (2026-06-04)

- [x] Scaffolded by `/task-work TASK-HMIG-010` (2026-06-04)
- [ ] AC-001 — Feature target picked by operator (pending — see feature-target.json)
- [ ] AC-002 — Feature run end-to-end with `GUARDKIT_HARNESS=langgraph`
- [ ] AC-003 — Per-task outcomes recorded
- [ ] AC-004 — First-pass-success rate computed + compared to 009A baseline
- [ ] AC-005 — Resume retry attempted on any first-pass failure
- [ ] AC-006 — Non-recoverable failures documented in `feature-run-incidents.md`
- [ ] AC-007 — Feature-complete merge attempted
- [ ] AC-008 — Falsifier evaluation + cutover decision
- [ ] AC-009 — This analysis document filled in

## 1. Executive verdict

_To be filled after the run completes._

## 2. Methodology actually executed

| Aspect | Spec intent | Actual |
|---|---|---|
| Target feature | ≥3 tasks, ≥2 waves, BDD-gated, state-bridge, ≤8h | _pending operator pick_ |
| Harness | langgraph | _pending_ |
| Model | qwen36-workhorse (same as 009A) | _pending_ |
| First-pass attempt | per-task | _pending_ |
| Resume policy | on any first-pass failure | _pending_ |
| Merge attempt | `guardkit autobuild complete` | _pending_ |

## 3. Findings — per-task summary

_Table to be filled task-by-task from `feature-results.json:task_outcomes`._

| Task | Wave | First-pass | Resume needed | Final | Turns | Wall-clock | Notes |
|---|---|---|---|---|---|---|---|
| _TBD_ | | | | | | | |

## 4. Aggregate metrics + 009A baseline comparison

_To be computed once `feature-results.json:aggregate_metrics` is filled._

| Metric | This run (010) | 009A baseline | Delta | Significance |
|---|---|---|---|---|
| First-pass success rate | _pending_ | 67% | | AC-004 threshold: >10pp drop = investigate |
| Approval rate (incl. resume) | _pending_ | 83.3% | | |
| Mean turns to approve | _pending_ | ~1.5 | | |
| Mean wall-clock per task | _pending_ | ~21min | | |

## 5. Falsifier evaluation (AC-008)

Threshold: ≥80% first-pass-success AND zero non-recoverable failures → proceed to Wave 4 cutover.

_Verdict: pending data._

## 6. Substrate-level findings worth recording

_Any new F-numbered findings beyond F1–F8 documented in canary-analysis.md go here. The canary's substrate-quality findings (F2, F5, F6, F7) likely re-surface at feature scale — note whether they reproduce, intensify, or attenuate under multi-task orchestration._

## 7. Recommendation

_To be filled. Two shapes possible:_

- **PROCEED to Wave 4 cutover** (TASK-HMIG-011): falsifier passed. Document any caveats from §6.
- **HALT Wave 4 cutover**: falsifier failed. Document the failure modes and the operator's decision (extend validation, revert, pivot).

## 8. Follow-up tasks

- _Any TASK-FIX-* tasks filed for issues discovered during the run._
- _Any TASK-REV-* tasks if the orchestrator surfaces a class-of-defect worth a review._

## 9. References

- Parent task: [TASK-HMIG-010](../../../tasks/in_progress/TASK-HMIG-010-full-feature-autobuild-validation.md)
- Parent review: [TASK-REV-HMIG](../../../.claude/reviews/TASK-REV-HMIG-review-report.md) §11 (falsifier), §7.3 (Wave 3 sequencing), §5.10 (failure-rate asymmetry)
- Canary precedent: [TASK-HMIG-009A](../../../tasks/completed/TASK-HMIG-009A-partial-canary-no-preloop-backlog-tasks.md), [canary-analysis.md](canary-analysis.md) §8
- Feature-target picks: [`.guardkit/autobuild/TASK-REV-HMIG-feature-target.json`](../../../.guardkit/autobuild/TASK-REV-HMIG-feature-target.json)
- Per-task results: [`.guardkit/autobuild/TASK-REV-HMIG-feature-results.json`](../../../.guardkit/autobuild/TASK-REV-HMIG-feature-results.json)
- Incidents log: [feature-run-incidents.md](feature-run-incidents.md)
