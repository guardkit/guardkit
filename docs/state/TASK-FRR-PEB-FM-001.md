# TASK-FRR-PEB-FM-001 — provenance record

> Provenance stub filed by **TASK-INFRA-CIGREEN** (2026-06-11) so the
> orchestrator-code reference resolves under the
> `tests/rules/test_no_dead_task_id_references.py` lint. The originating task
> predates the migration of completed tasks into `tasks/completed/2026-05/…`
> and was never filed as its own task file.

**What it was:** introduced the "Files to Create / Files to Modify" (FM-001)
plan convention — non-empty `## Files to Create` / `## Files to Modify`
sections in a task plan are the authoritative `planned_files` set for the
plan-audit path.

**Where the real artifact lives:** commit `02aac9c`.

**Referenced from:** `guardkit/orchestrator/agent_invoker.py` (the
`planned_files` extraction / plan-audit fallback path).
