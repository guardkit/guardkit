# TASK-HMIG-001B — provenance record (cross-repo)

> Provenance stub filed by **TASK-INFRA-CIGREEN** (2026-06-11) so the
> orchestrator-code reference resolves under the
> `tests/rules/test_no_dead_task_id_references.py` lint. **This task lives in
> the sibling `guardkitfactory` repo, not in guardkit** — the lint only
> searches this repo's `tasks/` and `docs/state/`, so this pointer record
> stands in for it.

**What it was:** built the `LangGraphHarness` (the LangGraph-based
`HarnessAdapter` substrate) in the separate `guardkitfactory` package. The
guardkit side consumes it via the `HarnessAdapter` ABC after
`GUARDKIT_HARNESS` selects it.

**Where the real artifact lives:** `guardkitfactory` repo (sibling). The
guardkit-side counterpart interface task is
`tasks/completed/2026-05/TASK-HMIG-001A-define-harness-adapter-interface.md`.

**Referenced from:** `guardkit/orchestrator/harness/adapter.py` and
`guardkit/orchestrator/harness/selector.py`.
