# TASK-REV-ABST Implementation Guide

> **Companion to**: [`TASK-REV-ABST-review-report.md`](./TASK-REV-ABST-review-report.md)
> **Generated**: 2026-05-10
> **Audience**: operator picking up the ABST follow-through tasks (today, in 7 days, or later)

This guide answers: *"Now that the review is complete, how do I actually run the follow-up tasks?"*

---

## Verdict context (short version)

`TASK-REV-ABST` recommended **Narrow** — a 7-day gate-stack freeze (2026-05-11→2026-05-17) plus monitoring, with re-measurement on 2026-05-17 to pick **Continue / Hold-Narrow / Pivot**.

Five concrete tasks were filed in `tasks/backlog/`. Three are immediate; two are deferred to 2026-05-17. Headline next-task `TASK-REV-PIVOT` is conditional and not yet filed — it only gets created if a negative-falsifier fires on 2026-05-17.

---

## The 5 tasks

| Task | Status | Command | Effort | Earliest start |
|---|---|---|---|---|
| [`TASK-FREEZE-ABST`](../../tasks/backlog/TASK-FREEZE-ABST-7day-gate-stack-freeze.md) | backlog | `/task-work TASK-FREEZE-ABST` | <1h | now |
| [`TASK-OBS-ABST`](../../tasks/backlog/TASK-OBS-ABST-passive-run-success-observability.md) | backlog | `/task-work TASK-OBS-ABST` | 4-6h | now |
| [`TASK-RETIRE-AC`](../../tasks/backlog/TASK-RETIRE-AC-audit-assumption-confidence-warn-mode.md) | backlog | `/task-work TASK-RETIRE-AC` | 1-2h | after `TASK-FREEZE-ABST` lands |
| [`TASK-DEMOTE-PA`](../../tasks/backlog/TASK-DEMOTE-PA-audit-plan-audit-at-followup.md) | backlog (`not_actionable_until: 2026-05-17`) | `/task-work TASK-DEMOTE-PA` | 1-2h | **2026-05-17** |
| [`TASK-REV-ABST.1`](../../tasks/backlog/TASK-REV-ABST.1-followup-stocktake-2026-05-17.md) | backlog (`not_actionable_until: 2026-05-17`) | `/task-review TASK-REV-ABST.1` | 2-3h | **2026-05-17** |

> **Important**: `TASK-REV-ABST.1` is a review task (`task_type: review`) — use `/task-review`, not `/task-work`. The other four are implementation tasks.

---

## Recommended order

```bash
# Today (under 1h):
/task-work TASK-FREEZE-ABST

# Today / over the next few days (4-6h, main monitoring deliverable):
/task-work TASK-OBS-ABST

# After FREEZE lands (1-2h):
/task-work TASK-RETIRE-AC

# On 2026-05-17:
/task-work TASK-DEMOTE-PA       # 1-2h
/task-review TASK-REV-ABST.1    # 2-3h — picks Continue / Hold / Pivot
```

### Dependencies (verbatim from task frontmatter)

```
TASK-FREEZE-ABST ─┬─→ TASK-RETIRE-AC ─┐
                  └─→ TASK-DEMOTE-PA ─┤
TASK-OBS-ABST ────┬───────────────────┼─→ TASK-REV-ABST.1
                  └─→ TASK-DEMOTE-PA ─┘
```

`TASK-REV-ABST.1` declares all four other tasks as soft/hard dependencies (it reads their outputs).

---

## Notes on `/task-work` behaviour

- Auto-runs Phase 2-5 (plan → arch review → complexity eval → implementation → tests → code review).
- All four implementation tasks are complexity 2-5, so they should auto-proceed without hitting the Phase 2.8 human checkpoint (that fires at ≥7).
- `TASK-OBS-ABST` has 10 ACs and complexity 5 — `/task-work` will produce a multi-phase plan; you'll see the plan before implementation starts and can intervene if you want a slimmer first cut.
- `not_actionable_until: 2026-05-17` is **informational only** — it doesn't physically block early execution. Just don't run those two early; their data preconditions won't be ready.

## Parallel-execution option

`TASK-FREEZE-ABST` and `TASK-OBS-ABST` touch different paths and can run in parallel via Conductor workspaces if you want. Sequential is simpler and they're small enough that parallelism overhead probably isn't worth it.

---

## First validation observation (logged 2026-05-10)

After this implementation guide was written, **`FEAT-FG-001` autobuild ran cleanly** on `guardkit@HEAD` post AB-001/003/004 fixes:

- **Outcome**: COMPLETED, 6/6 tasks, 22m 25s, "Clean executions: 6/6 (100%)".
- **Source**: `~/Projects/appmilla_github/fleet-gateway/docs/history/autobuild-FEAT-FG-001-success-history.md`.
- **TASK-FG-004** (the only task with fresh work; the other 5 were resumed-as-completed): approved on Turn 2 (Turn 1 hit the BDD oracle "1 scenario failed" feedback, Turn 2 cleaned up).

### Effect on the falsifier set (per [review report §8.2](./TASK-REV-ABST-review-report.md#82-falsifying-leading-indicator))

| Falsifier | Status |
|---|---|
| POSITIVE-1: ≥3 consumer-repo features pass cleanly on **first-turn** during the freeze | **Not yet fired** (FG-004 took 2 turns, not 1; this is 1 of ≥3 needed). |
| POSITIVE-2: No new framework FP incident filed during the freeze | **Holding** (this run did not generate a new incident; it resolved the prior one). |
| NEGATIVE-1: A new framework FP class filed | Not fired. |
| NEGATIVE-2: ≥5-turn identical-feedback stall | Not fired (FG-004 approved on Turn 2). |

**Net**: strong corroborating evidence that the May 10 fixes hold against their load-bearing reproducer. **The verdict (Narrow) does not change** — the freeze + monitoring + 2026-05-17 re-measurement still applies. `TASK-OBS-ABST` will fold the FG-001 success into the metric snapshot automatically when it runs.

---

## If something looks wrong on 2026-05-17

`TASK-REV-ABST.1` AC-001 has a precondition check:

- If `TASK-OBS-ABST` is incomplete → escalate to operator before proceeding.
- If `TASK-FREEZE-ABST` did not hold (a NEW_GATE commit landed in the window) → flag in the report and proceed; the freeze-as-process needs review.
- If `TASK-RETIRE-AC` audit didn't complete → the assumption-confidence audit becomes a TASK-REV-ABST.2 follow-up.

The follow-up review's job is to score the four falsifiers above and pick **exactly one** of: promote-to-Continue, hold-Narrow (extend freeze 7 days), or escalate-to-Pivot.

---

## Future agents

If you're picking this up after the operator has been away (e.g. post DDD South West / Kaggle Hackathon), the right reading order is:

1. This file (you are here).
2. [`TASK-REV-ABST-review-report.md`](./TASK-REV-ABST-review-report.md) §1 (executive summary), §8 (recommendation + falsifier), §9 (limits).
3. The five task files in `tasks/backlog/TASK-{FREEZE,OBS,RETIRE,DEMOTE,REV}-*.md`.

The deepest analysis (§2 timeline, §4 gate-by-gate matrix, §6 doom-loop test) is in the review report and does not need re-running unless the verdict is being challenged.

## Provenance

- Originating review: `TASK-REV-ABST` (status `review_complete`, located at `tasks/review_complete/`)
- Review report: [`TASK-REV-ABST-review-report.md`](./TASK-REV-ABST-review-report.md)
- Task files: `tasks/backlog/TASK-{FREEZE,OBS,RETIRE,DEMOTE,REV}-ABST*.md` (and `TASK-REV-ABST.1*.md`)
- Operator constraint that drove the rescoping: deadlines for DDD South West talk + Kaggle Hackathon in 2026-05-10 → ~2026-05-19; precluded `TASK-VAL-FG001/FFC3/FRESH` (autobuild reruns).
