# Feature: AutoBuild Capture Cluster (FEAT-OBSC)

> **Reconcile-then-spec output, 2026-07-09.** This is the ONE feature consolidating
> lanes OBS-1 / OBS-2 / OBS-3 plus the M2 lint rider, per decisions of record
> **D-OBS-1..4** (`ai-transition/docs/observability-analysis-production-and-continual-learning-2026-07-09.md` §7,
> all FILED 2026-07-09) and the operative kickoff (Step 4 of
> `ai-transition/docs/kickoff-prompts-flywheel-closure-2026-07-09.md`, including its two
> riders: L12's `baseline.json` in the archival scope, and the M2 lint-budget flip).
> It **absorbs, supersedes, or closes every task** in the prior
> `tasks/backlog/autobuild-instrumentation/` (TASK-INST series, FEAT-CF57),
> `TASK-REV-2FE2`, and `tasks/backlog/autobuild-observability-fixes/` (FEAT-AOF)
> backlogs — see the Disposition Register below. No INST duplicates remain in
> `tasks/backlog/` or `tasks/design_approved/`.

## Problem

The instrumentation layer built in 2026-03 (FEAT-CF57, TASK-INST series) is **built
and dead**: event schemas, emitter backends, redaction, and the per-role emit paths
all exist and are test-proven, but no production `AgentInvoker` receives an emitter —
every `LLMCallEvent`/`ToolExecEvent` no-ops into a `NullEmitter`. Meanwhile run
artifacts (player/coach turn JSONs, `task_work_results.json`, sdk_debug traces) live
inside disposable worktrees, are gitignored, and are **destroyed by worktree prune**
(the lpa-platform-poc per-turn corpus was permanently lost this way; 3 of 4 QAV gold
negatives had to be reconstructed). And raw Player traces — the teacher data both
Story A (cost/provenance telemetry) and Story B (Player distillation, the DF-006
survival fallback) depend on — are **not captured at all**: `sdk_debug` is opt-in via
`GUARDKIT_AUTOBUILD_PRESERVE_DEBUG` and zero sdk_debug dirs exist anywhere on disk.
Every frontier Player run since June is unrecoverable teacher data.

## Verified wiring truth (disk-verified 2026-07-09, this session)

| Hop | State | Evidence |
|---|---|---|
| CLI (feature mode) builds `CompositeBackend([JSONLFileBackend])`, passes `emitter=` | ✅ live (TASK-INST-013) | `guardkit/cli/autobuild.py:1046-1048`, `:1069`; JSONL → `<cwd>/.guardkit/autobuild/<FEAT>/events.jsonl` (main repo, survives prune) |
| CLI (**task mode**) builds an emitter | ❌ none — single-task runs emit nothing | `guardkit/cli/autobuild.py:555-572` |
| FeatureOrchestrator stores + forwards emitter | ✅ live | `feature_orchestrator.py:806` (store), `:4062` (forward, TASK-INST-013); emits `WaveCompletedEvent` at `:3690` |
| AutoBuildOrchestrator stores `self._emitter` | ✅ live (TASK-INST-004) | `autobuild.py:1566`; lifecycle emits `:5764-5851` |
| AutoBuildOrchestrator → AgentInvoker | ❌ **severed — the missing hop** | three construction sites pass no `emitter=`: `autobuild.py:2151`, `:2183`, `:8230` → `NullEmitter` at `agent_invoker.py:1488` |
| AgentInvoker emit paths (llm.call / tool.exec) | ✅ built, dead in production (TASK-INST-005b/005c) | `agent_invoker.py:4443` (LLMCallEvent), `:4546` (ToolExecEvent); test-proven with injected emitters |
| Model attribution | ❌ falls back to literal `"default"` | `agent_invoker.py:4431`; real model available in the resolved `model` local (`:4001-4009`) and in `AssistantMessage.model` on the raw stream |
| Correlation identity | ❌ unwired | `_run_id`/`_current_attempt`/`_current_agent_role`/`_prompt_profile` read via getattr (`:4413-4419`, `:4521-4527`) but **never assigned**; lifecycle events fabricate divergent run_ids (`autobuild.py:5773/:5811/:5841`); ToolExec hardcodes `exit_code=0` (`:8481`) |
| Run-artifact durability | ❌ destructible | `_archive_phase` (`feature_orchestrator.py:4901`) archives task-md folders only and is **production-dead** (called only from tests); nothing archives `<worktree>/.guardkit/autobuild/<task_id>/` before `WorktreeManager.cleanup` (`worktrees/manager.py:509-551`) / the `--fresh` clean path (`feature_orchestrator.py:1106`, `:1198`) |
| Raw trace capture (sdk_debug) | ❌ off, raw, uncapped, worktree-bound | `sdk_debug.py:31` env gate, default OFF; writes prompt.txt / options.json / messages.jsonl with **no redaction, no size caps**, under the worktree (dies with prune) |
| Redaction | Partial | `SecretRedactor` (`instrumentation/redaction.py:60`) applied ONLY to ToolExecEvent fields (`agent_invoker.py:4536-4540`); sdk_debug streams unredacted; `guardkit/lib/secret_scrub.py` is a separate publication-boundary scrubber by design |

Note: line numbers in the 07-09 decision docs drifted slightly (2147→2151, 2179→2183,
8218→8230, ~4422→4431, 8207→8230); the figures above are current as of this session.

## Solution — four workstreams, one feature

1. **WS1 — Wire the emitter live (OBS-1, dashboard ask A-4b).** Pass `self._emitter`
   through the three AgentInvoker construction sites; give `guardkit autobuild task`
   mode emitter parity; fix model attribution to the real resolved/served model; wire
   joinable correlation identity (run_id, attempt, role, prompt_profile, real exit
   codes) so capture = flywheel input by construction (WS4 Appendix A fields 4–5).
2. **WS2 — Run-artifact durability (OBS-2).** Archive `.guardkit/autobuild/{task_id}/`
   **and** the feature-level `baseline.json` (L12 rider) to a stated durable home
   before any worktree removal; sweep the feature-level `events.jsonl`; NAS-backed
   home per D-OBS-4 with in-loop writes strictly node-local.
3. **WS3 — Default-on Player trace capture (OBS-3, gated on D-OBS-2 prerequisites).**
   Extend redaction to sdk_debug message streams; then flip sdk_debug to default-on
   via repo allowlist (guardkit, study-tutor, forge, fleet-*; client/FinProxy repos
   stay opt-in per run) with size-capped rotation, a keep-out-of-git guarantee, and a
   per-field conformance check against WS4 Appendix A
   (`ai-transition/docs/ws4-learning-flywheel-scope-and-build-plan-2026-07-07.md`, Appendix A).
4. **WS4 — M2 lint-budget rider (per WS4 Amendment M3).** Flip the template
   structure-lint per-section token budgets from INFO/report-only to WARNING at the
   now-committed 32K-floor serving figure (per-slice ≤ ~20k; the 64K seat is headroom,
   not the gate). Carried here as a small item rather than a separate lane claim.

## Tasks (6 tasks, 4 waves)

| Wave | Task | Description | Complexity | Decision |
|------|------|-------------|-----------|----------|
| 1 | TASK-OBS-4899 | Wire emitter through the three AgentInvoker sites + task-mode CLI parity | 3 | D-OBS-1 (OBS-1) |
| 1 | TASK-OBS-F3F5 | Flip structure-lint token budgets INFO→WARNING at committed 32K-floor figure | 2 | M2 rider / WS4 Amendment M3 |
| 2 | TASK-OBS-9F43 | Real model attribution + joinable correlation identity on events | 4 | D-OBS-1 (OBS-1) |
| 2 | TASK-OBS-80FE | Archive run artifacts (incl. `baseline.json`) before worktree prune; stated durable home | 5 | D-OBS-1/4 (OBS-2) + L12 rider |
| 3 | TASK-OBS-C440 | Extend secret redaction to sdk_debug message streams | 4 | D-OBS-2 prerequisite |
| 4 | TASK-OBS-396E | sdk_debug default-on: repo allowlist, rotation, keep-out-of-git, Appendix A conformance | 6 | D-OBS-2 (OBS-3) |

Dependencies: 9F43 ← 4899; 396E ← {C440, 80FE, 9F43}. F3F5 is independent.

## Constraints (standing, from the decisions of record)

- **Node-local file writes only** in any agent loop — no Jarvis/NATS/Slack/fleet
  infra enters the loop (self-contained-agents rule). The NAS sync in WS2 is an
  out-of-loop operator/cron step, never an in-loop write.
- **The three D-OBS-2 prerequisites are unconditional** — message-stream redaction,
  keep-out-of-git guarantee, size-capped rotation must all hold **before** the
  default-on flip. Enforcement is two-layer: redaction precedes by wave ordering
  (TASK-OBS-C440, wave 3, a hard dependency of the flip task); rotation and
  keep-out-of-git land inside the flip task itself and are **runtime-gated** — the
  default-on path refuses to activate unless both guards hold at startup
  (TASK-OBS-396E Change 3a / AC-2b), so wave ordering is not load-bearing for them.
  Motivated by §4 hazard 3 (80-minute FinProxy leak incident; client data in prompts).
- **Client/FinProxy repos stay opt-in per run** regardless of any default.
- Absence-of-failure discipline applies to every new capture check: an absent capture
  signal is surfaced, never read as success (`.claude/rules/absence-of-failure-is-not-success.md`).

## Known limitations (explicitly out of scope, documented so they aren't silent)

- **CoachValidator's independent-test path** calls `select_harness` directly
  (`coach_validator.py:4741-4832`), bypassing `_invoke_with_role` — those LLM calls
  emit no `llm.call` event even after WS1; sdk_debug preservation is the only
  telemetry there. Candidate follow-up lane, not funded by D-OBS-1.
- **`GraphitiQueryEvent`** has no production emit site (the Graphiti implementation
  was removed by FEAT-MEM-09 WS-2c, 2026-07-02). Schema retained; no work here.
- **NATSBackend** has no production construction site (JSONL-only CompositeBackend);
  correct under the node-local constraint. No work here.
- **OBS-4..8 lanes** (stats aggregator, coach-ft-v3 shadow, label sidecar, general
  eval, dashboard) are downstream/sibling lanes, not this feature. OBS-6 is queued
  separately (kickoff Step 6).
- **Context-reduction leftovers** from FEAT-CF57 (digest adoption/A-B profile runs,
  adaptive-concurrency consultation) are delivered code whose *operational adoption*
  is not funded here.

---

## Disposition Register (the reconciliation record)

### Why TASK-INST-005 is SUPERSEDED (question of record)

`TASK-INST-005-instrument-agent-invoker` (monolith, complexity 6) was created
2026-03-02 10:12 by commit `53d49f258` (the FEAT-CF57 `/feature-plan` output) and
superseded **the same day** by commit `16200e26b` (13:25), which renamed the file in
place to `.SUPERSEDED.md` (the filename suffix was the only marker — fixed today with
an explicit frontmatter status) and created its three replacements in the same
commit. The trigger was the mid-planning discovery (recorded in the task's
Architecture Note) that the Player uses the **inline prompt-builder pattern**
(TASK-ACO-002) rather than subprocess delegation, so instrumentation had to touch
multiple distinct seams; the complexity-6 monolith straddling two producer contracts
was split for autobuild sizing into:

- **TASK-INST-005a** — pure helper module (`llm_instrumentation.py`) — delivered.
- **TASK-INST-005b** — `llm.call` emission from `_invoke_with_role` — the "internal
  emit paths at agent_invoker.py:4443/:4546 that no-op via NullEmitter" are exactly
  this delivery — completed 2026-03-08.
- **TASK-INST-005c** — `tool.exec` emission + redaction — completed 2026-03-08.

### FEAT-CF57 / TASK-INST series (all dispositioned 2026-07-09)

Everything below was delivered to main via merge `45d74188b` (2026-03-03,
"Merge autobuild/FEAT-CF57") and wrap-up `76e2439e2` (2026-03-08). The task files
had never been archived — they sat duplicated in `tasks/backlog/` (status
`in_review`) **and** `tasks/design_approved/` (a state-bridge merge artifact — the
same orchestrator-moves-files mechanism documented in
`.claude/rules/path-string-mismatch-is-not-dishonesty.md`).

| Task | Disposition (2026-07-09) | Evidence |
|---|---|---|
| TASK-INST-001 event schemas | **Closed completed** → `tasks/completed/2026-03/TASK-INST-001/` | `instrumentation/schemas.py`; merge `45d74188b` |
| TASK-INST-002 emitter backends | **Closed completed** → `tasks/completed/2026-03/TASK-INST-002/` | `instrumentation/emitter.py` |
| TASK-INST-003 redaction pipeline | **Closed completed** → `tasks/completed/2026-03/TASK-INST-003/` | `instrumentation/redaction.py` |
| TASK-INST-004 orchestrator lifecycle | **Closed completed** → `tasks/completed/2026-03/TASK-INST-004/` | `autobuild.py:1566`, `:5764-5851` |
| TASK-INST-005 (monolith) | **Superseded** (by 005a/b/c, commit `16200e26b`) → `tasks/obsolete/` with explicit status | see above |
| TASK-INST-005a helpers | **Closed completed** → `tasks/completed/2026-03/TASK-INST-005a/` | `instrumentation/llm_instrumentation.py` |
| TASK-INST-005b llm.call events | Already completed 2026-03-08 (`tasks/completed/2026-03/TASK-INST-005b/`) — no action | emit path `agent_invoker.py:4443` |
| TASK-INST-005c tool.exec events | Already completed (canonical `tasks/completed/2026-03/TASK-INST-005c/`); **stale backlog duplicate deleted** | emit path `agent_invoker.py:4546` |
| TASK-INST-006 Graphiti loader | **Closed completed** → `tasks/completed/2026-03/TASK-INST-006/`; instrumented surface later removed by fleet-memory cutover (`GraphitiQueryEvent` now has no producer) | `context_loader.py` delta in `45d74188b`; FEAT-MEM-09 WS-2c |
| TASK-INST-007 role digests | **Closed completed** → `tasks/completed/2026-03/TASK-INST-007/` | `instrumentation/digests.py`, `.guardkit/digests/` |
| TASK-INST-008 adaptive concurrency | **Closed completed** → `tasks/completed/2026-03/TASK-INST-008/` | `instrumentation/concurrency.py` |
| TASK-INST-009 integration tests | **Closed completed** → `tasks/completed/2026-03/TASK-INST-009/` (stale dep on superseded 005 noted in file) | `tests/orchestrator/instrumentation/` |
| TASK-INST-010 init-path reconcile | **Closed completed** → `tasks/completed/2026-03/TASK-INST-010/` | `cli/init.py` +273 in `45d74188b` |
| TASK-INST-011 template→Graphiti sync | **Closed completed-then-removed** → `tasks/completed/2026-03/TASK-INST-011/`; implementation deleted by FEAT-MEM-09 WS-2c (2026-07-02). Any surviving intent must be re-specified against fleet-memory — **out of scope here** | `template_sync.py` no longer exists |
| TASK-INST-012 enrich seeding | **Closed completed-then-removed** → `tasks/completed/2026-03/TASK-INST-012/`; same cutover note as 011 | `seed_*.py` no longer exist |
| TASK-INST-013 wire emitter CLI | Already completed (`tasks/completed/2026-03/TASK-INST-013/`) — no action; live marker `cli/autobuild.py:1046` | commit `76e2439e2` |
| TASK-INST-014 digest files | Already completed — no action | `76e2439e2` |
| TASK-INST-015 instrumentation guide | Already completed — no action | `docs/guides/autobuild-instrumentation-guide.md` |
| TASK-REV-2FE2 (parent review) | **Closed completed** → `tasks/completed/2026-03/TASK-REV-2FE2/` (report at `.claude/reviews/TASK-REV-2FE2-review-report.md` remains the historical plan of record) | plan implemented via FEAT-CF57 |
| README + IMPLEMENTATION-GUIDE | **Archived** → `tasks/completed/2026-03/autobuild-instrumentation/` with reconciliation banner (contract consumer lists still name superseded 005 — historical record, not corrected) | this session |

`TASK-INST-04CA` (installer symlinks) shares the INST prefix by hash coincidence and
is unrelated — untouched.

### FEAT-AOF / autobuild-observability-fixes (all dispositioned 2026-07-09)

The folder's three residents were stale backlog copies that doubled as the
TASK-HMIG-010 LangGraph dogfood feature (runs 19–25). Branch `autobuild/FEAT-AOF`
remains unmerged and accumulated dogfood noise; **recommendation: discard, do not
merge** (merging would regress TASK-ABFIX-012 — see TP05).

| Task | Disposition (2026-07-09) | Evidence |
|---|---|---|
| TASK-FIX-PV01, TASK-FIX-TS04 | Long completed on main — no action | merges `5f78f1eda`, `e2bc6d99f` |
| TASK-FIX-IA03 | Formally completed (`tasks/completed/TASK-FIX-IA03/`); **stale backlog duplicate deleted**. Two residuals were lost with the branch reset (`3ecf44858` destroyed commit `140a8cda`): the "user files" warning wording and the 22-test `_is_doc_level_excluded` regression suite. Recorded here as optional follow-ups, **not funded by this feature** | core landed via TASK-GK-DOC-001 (`8e738e816`) |
| TASK-FIX-GD02 | **Closed superseded** → `tasks/obsolete/`: per-task baseline mechanism landed via TASK-FIX-VL06 (`212f9d24`, `_record_baseline`) and was extended by TASK-AB-XREPOEV01. Residual open question (uncommitted-changes set-difference delta vs committed-baseline diff) recorded in the tombstone; branch copy do-not-merge | `agent_invoker.py` baseline machinery, now load-bearing for two `.claude/rules/` |
| TASK-FIX-TP05 | **Closed superseded** → `tasks/obsolete/`: TASK-ABFIX-012 (`18ceb2ae6`) delivers the intent in stronger form and **deliberately reverses** TP05's `zero_test_blocking=False` AC with documented guards ("Do not flip this back without those guards") | `guardkit/models/task_types.py` |
| Folder README | **Archived** → `tasks/completed/2026-06/autobuild-observability-fixes/` with banner | this session |

`FEAT-CF57.yaml` / `FEAT-AOF.yaml` manifests were left untouched; run
`guardkit feature audit [--fix]` after this reconciliation to re-derive inferred
statuses from the new file locations.

## References

| Resource | Location |
|---|---|
| Decisions of record | `ai-transition/docs/observability-analysis-production-and-continual-learning-2026-07-09.md` §7 (D-OBS-1..4) |
| Operative kickoff (+ riders) | `ai-transition/docs/kickoff-prompts-flywheel-closure-2026-07-09.md` Step 4 |
| WS4 Appendix A field contract | `ai-transition/docs/ws4-learning-flywheel-scope-and-build-plan-2026-07-07.md` (line ~381) |
| 32K-floor serving figure (M2/M3) | same WS4 doc, §Amendment A/B + WS4-S12 row |
| Prior feature (delivered) | `tasks/completed/2026-03/autobuild-instrumentation/` (FEAT-CF57), report `.claude/reviews/TASK-REV-2FE2-review-report.md` |
| Instrumentation guide | `docs/guides/autobuild-instrumentation-guide.md` |
| Fleet decision context | `ADR-FLEET-001` (trace-richness by default), `DF-006` (frontier = revocable teacher), `DF-001` (no cloud on unattended path) |
