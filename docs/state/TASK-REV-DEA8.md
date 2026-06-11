# TASK-REV-DEA8 — provenance record

> Provenance stub filed by **TASK-INFRA-CIGREEN** (2026-06-11) so the
> orchestrator-code reference resolves under the
> `tests/rules/test_no_dead_task_id_references.py` lint. Parent review task;
> the implementing fix tasks are filed normally (see below).

**What it was:** the parent review behind the FPSG defense-in-depth work —
distinguishing a path-existence miss from a Pydantic schema violation during
post-mortem triage.

**Where the real artifact lives:** `tasks/completed/TASK-FPSG-005/TASK-FPSG-005.md`
(L4 defense-in-depth) and siblings `TASK-FPSG-002`/`004`.

**Referenced from:** `guardkit/orchestrator/feature_loader.py` (path-existence
vs schema-violation discrimination).
