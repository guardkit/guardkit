# TASK-REV-J6F1 — provenance record

> Provenance stub filed by **TASK-INFRA-CIGREEN** (2026-06-11) so the
> orchestrator-code reference resolves under the
> `tests/rules/test_no_dead_task_id_references.py` lint. This is the parent
> *review* task; its child *fix* task is filed normally (see below).

**What it was:** the review that motivated claim-audit path normalisation —
`git status --porcelain` paths are always worktree-relative, so absolute
claim paths can never match without a normalisation step. FEAT-JARVIS-006
repro.

**Where the real artifact lives:** the fix task is filed at
`tasks/completed/2026-05/TASK-FIX-CAUD-J6F1-claim-audit-path-normalisation.md`.

**Referenced from:** `guardkit/orchestrator/coach_verification.py` (claim-path
normalisation step).
