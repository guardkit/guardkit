# TASK-REV-9A4B — provenance record

> Provenance stub filed by **TASK-INFRA-CIGREEN** (2026-06-11) so the
> orchestrator-code reference resolves under the
> `tests/rules/test_no_dead_task_id_references.py` lint. This was a review /
> post-mortem task whose report was never filed as a task file in this repo.

**What it was:** post-mortem on a crash where a `ValueError` (an invalid
value from the Coach) bubbled up to `orchestrate()` and marked the task
`error`, halting `stop_on_failure` runs. The fix wrapped the offending call
in a `try/except`.

**Referenced from:** `guardkit/orchestrator/autobuild.py` (the guarded
Coach-value-handling block).
