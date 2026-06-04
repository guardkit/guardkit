# Feature-run incidents — TASK-HMIG-010

> Per AC-006: this file records non-recoverable failures from the
> TASK-HMIG-010 feature-level LangGraph validation run, with root-cause
> analysis. "Non-recoverable" means: Coach rejection surviving 3
> task-work attempts, orchestrator crash, state-bridge corruption, or
> any failure the operator cannot resolve without code edits to the
> harness itself.
>
> Recoverable failures (first-pass-fail recovered by `--resume`) go in
> `feature-results.json:task_outcomes[*].notes`, not here.

## 0. Status

- Scaffolded by `/task-work TASK-HMIG-010` (2026-06-04)
- Empty until incidents occur

## Incident schema

Each incident gets its own `## I-NNN: <title>` section with:

- **Task**: which task in the feature triggered it
- **Wave / parallel group**: orchestration context
- **Symptom**: what the operator/orchestrator observed
- **Attempts made**: list of task-work attempts (1, 2, 3 + resume)
- **Root cause**: post-mortem analysis
- **Severity**: low | medium | high (high = blocks cutover; medium = file follow-up task)
- **Resolution**: code edit | spec revision | accepted-as-substrate-quality | other
- **Follow-up task**: TASK-FIX-* or TASK-REV-* filed (if any)

## Incidents

_None yet._

---

## References

- Parent task: [TASK-HMIG-010](../../../tasks/in_progress/TASK-HMIG-010-full-feature-autobuild-validation.md)
- Sibling analysis: [feature-run-analysis.md](feature-run-analysis.md)
- Canary findings precedent: [canary-analysis.md §3](canary-analysis.md) (F1–F8 numbering convention)
