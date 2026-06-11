# TASK-HMIG-002R — provenance record (cross-repo)

> Provenance stub filed by **TASK-INFRA-CIGREEN** (2026-06-11) so the
> orchestrator-code reference resolves under the
> `tests/rules/test_no_dead_task_id_references.py` lint. **This task lives in
> the sibling `guardkitfactory` repo, not in guardkit.**

**What it was:** built the real backend + permissions factories in
`guardkitfactory.harness` (2026-05-20) that `LangGraphHarness` consumes.
Until that wiring, `LangGraphHarness` fell back to its built-in DeepAgents
defaults; SDK `permission_mode` vocabulary (`acceptEdits` /
`bypassPermissions`) is dropped at the selector boundary.

**Where the real artifact lives:** `guardkitfactory` repo (sibling). The
guardkit-side consumer task is `TASK-FIX-002R-CONSUME` (imports those
factories alongside `LangGraphHarness` in `harness/selector.py`).

**Referenced from:** `guardkit/orchestrator/harness/selector.py`.
