# Canary validation comparison — TASK-REV-HMIG

> **Skeleton** scaffolded by `/task-work TASK-HMIG-009` (2026-05-21).
> This file is **auto-regenerated** by
> `python scripts/canary_validation_runner.py --aggregate` after the
> 18 canary runs complete. Do not hand-edit sections 1–3 except to
> annotate the verdict. Hand-fill section 4 (per-task AC equivalence)
> from the per-run `coach_turn_N.json` artefacts.

## 0. Status

- [ ] All 18 canary runs complete (3 tasks × 2 harnesses × 3 reps)
- [ ] `--aggregate` invoked to populate sections 1–3
- [ ] Section 4 (per-task AC equivalence) hand-filled from artefacts
- [ ] Verdict cross-referenced into TASK-HMIG-009 AC-007
- [ ] Audit doc at `docs/state/TASK-REV-HMIG/canary-analysis.md` written

## 1. Aggregate first-pass-success rate (the central falsifier)

_To be filled by `--aggregate`._

- **LangGraph**: _/9 = __%
- **SDK**: _/9 = __%

### Verdict

_To be filled by `--aggregate` based on TASK-HMIG-009 AC-007 thresholds:_

- LangGraph ≥ 85% → STRONGLY CONFIRMED → proceed at full pace to TASK-HMIG-010.
- LangGraph 75–85% → WEAKLY CONFIRMED → proceed with elevated R-02/R-06 risk weighting.
- LangGraph < 75% → **FALSIFIED per review §11** → halt Wave 4 cutover, escalate, open
  follow-up task (TASK-HMIG-011 or similar) for the revert decision.

## 2. Per-harness aggregate metrics

_To be filled by `--aggregate`._

| Metric | SDK | LangGraph |
|---|---|---|
| First-pass success | _/9 | _/9 |
| Mean turns used | _ | _ |
| Mean wall-clock (s) | _ | _ |
| Mean ACs passed | _ | _ |
| Mean ACs failed | _ | _ |

## 3. Per-task per-run summary

_To be filled by `--aggregate` from `TASK-REV-HMIG-canary-results.json`._

| Task | Harness | Run | Turns | Coach | ACs ✓ | ACs ✗ | Wall-clock (s) | Notes |
|---|---|---|---|---|---|---|---|---|
| TASK-GLI-004 | sdk | 1 | _ | _ | _ | _ | _ | _ |
| TASK-GLI-004 | sdk | 2 | _ | _ | _ | _ | _ | _ |
| TASK-GLI-004 | sdk | 3 | _ | _ | _ | _ | _ | _ |
| TASK-GLI-004 | langgraph | 1 | _ | _ | _ | _ | _ | _ |
| TASK-GLI-004 | langgraph | 2 | _ | _ | _ | _ | _ | _ |
| TASK-GLI-004 | langgraph | 3 | _ | _ | _ | _ | _ | _ |
| TASK-FIX-A7D3 | sdk | 1 | _ | _ | _ | _ | _ | _ |
| TASK-FIX-A7D3 | sdk | 2 | _ | _ | _ | _ | _ | _ |
| TASK-FIX-A7D3 | sdk | 3 | _ | _ | _ | _ | _ | _ |
| TASK-FIX-A7D3 | langgraph | 1 | _ | _ | _ | _ | _ | _ |
| TASK-FIX-A7D3 | langgraph | 2 | _ | _ | _ | _ | _ | _ |
| TASK-FIX-A7D3 | langgraph | 3 | _ | _ | _ | _ | _ | _ |
| TASK-DOC-267D | sdk | 1 | _ | _ | _ | _ | _ | _ |
| TASK-DOC-267D | sdk | 2 | _ | _ | _ | _ | _ | _ |
| TASK-DOC-267D | sdk | 3 | _ | _ | _ | _ | _ | _ |
| TASK-DOC-267D | langgraph | 1 | _ | _ | _ | _ | _ | _ |
| TASK-DOC-267D | langgraph | 2 | _ | _ | _ | _ | _ | _ |
| TASK-DOC-267D | langgraph | 3 | _ | _ | _ | _ | _ | _ |

## 4. Per-task AC equivalence

_Hand-filled by the operator after `--aggregate`. For each canary task,
list ACs where SDK and LangGraph agreed (both passed or both failed
across all 3 reps), and ACs where the two harnesses disagreed. The
disagreement set is the audit signal — disagreements either expose a
harness behavioural-drift bug, a non-deterministic LLM artefact, or a
genuine Coach-prompt difference that needs follow-up._

### TASK-GLI-004

| AC | SDK verdict (3 reps) | LangGraph verdict (3 reps) | Agreement |
|---|---|---|---|
| _to fill from coach_turn_N.json_ | — | — | — |

### TASK-FIX-A7D3

| AC | SDK verdict (3 reps) | LangGraph verdict (3 reps) | Agreement |
|---|---|---|---|
| _to fill from coach_turn_N.json_ | — | — | — |

### TASK-DOC-267D

| AC | SDK verdict (3 reps) | LangGraph verdict (3 reps) | Agreement |
|---|---|---|---|
| _to fill from coach_turn_N.json_ | — | — | — |

## 5. References

- Canary set: [TASK-REV-HMIG-canary-set.json](TASK-REV-HMIG-canary-set.json)
- Raw run records: [TASK-REV-HMIG-canary-results.json](TASK-REV-HMIG-canary-results.json) (created by runner)
- Audit analysis: [../../docs/state/TASK-REV-HMIG/canary-analysis.md](../../docs/state/TASK-REV-HMIG/canary-analysis.md)
- Parent review: [../../.claude/reviews/TASK-REV-HMIG-review-report.md](../../.claude/reviews/TASK-REV-HMIG-review-report.md), §11 (falsifier) and §7.3 (Wave 3 sequencing)
- Driver task: [../../tasks/in_progress/TASK-HMIG-009-canary-validation.md](../../tasks/in_progress/TASK-HMIG-009-canary-validation.md) (will move on completion)
