# TASK-REV-AOF-RUN9 — provenance record (cross-repo doc)

> Provenance stub filed by **TASK-INFRA-CIGREEN** (2026-06-11) so the
> orchestrator-code reference resolves under the
> `tests/rules/test_no_dead_task_id_references.py` lint. The review document
> lives in the sibling `guardkitfactory` repo.

**What it was:** the FEAT-AOF run-9 pre-next-run readiness review. Run-9
turn-2 (2026-06-07) showed the test-orchestrator make its last model call at
~90s then go silent — motivating the 600s duration cap (which bounds a hang
but does not eliminate it) on specialist invocations.

**Where the real artifact lives:**
`../guardkitfactory/docs/reviews/autobuild-migration/TASK-REV-AOF-RUN9-pre-next-run-readiness-review.md`.

**Referenced from:** `guardkit/orchestrator/specialist_invocations.py`.
