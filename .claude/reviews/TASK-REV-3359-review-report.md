# Review Report: TASK-REV-3359 — Plan: Outcome-Label Sidecar

## Executive Summary

The OBS-6 outcome-label sidecar is architecturally small (aggregate complexity ~5)
and fits the repo's existing seams cleanly. The 80FE archive rider is satisfied
**for free** for pre-cleanup labels (the archiver sweeps `.guardkit/autobuild/`
wholesale), and post-archival writes reduce to sharing one existing resolver
(`get_archive_root_from_env`). The recommended architecture is a new
`guardkit/labels/` package with a single writer, two resolvers (identity, paths),
one CLI group, and imperative `EXECUTE` hooks in the three disposition markdown
commands — the proven TASK-FIX-3C9D shape.

**Recommended approach: Option B** (full identity + path resolvers in the producer).
Six tasks, four waves, no blockers.

## Review Details

- **Mode**: decision · **Depth**: standard
- **Context A**: focus=architecture, tradeoff=maintainability, concerns=archive-seam / writer-integration / consumer-contract
- **Inputs**: `features/outcome-label-sidecar/` spec (21 scenarios, 7 resolved assumptions), code investigation (software-architect agent, 54 tool uses, paths verified)

## Key Findings

1. **Archive seam is already label-compatible (F1, resolves rider 1).**
   `RunArtifactArchiver.archive_worktree_artifacts` copies every item under the
   worktree's `.guardkit/autobuild/` (`archive.py:212-221`, `shutil.copytree`) —
   a sidecar beside `events.jsonl` archives with zero archiver changes, provided
   the label lands before `WorktreeManager.cleanup()` (`manager.py:510-587`,
   archive at :537-566 precedes `git worktree remove` at :568-577). Archive
   layout is nested: `archive_root/<feature_or_task_id>/<task_id>/…` — confirming
   the task-id-anchored relative evidence reference (ASSUM-004) as the only shape
   valid in both live and archived copies, solo and feature modes.

2. **Post-archival writes must share the existing resolver (F2).**
   `get_archive_root_from_env()` (`archive.py:364-374`) + the
   `~/.guardkit/archive/<repo>/` fallback (`archive.py:82-93`) is the acquisition
   path the label writer's archive branch must import, not reimplement — the
   filesystem analogue of `cli-wrapper-shares-client-acquisition-path.md`.

3. **Correlation identity is opportunistic, not guaranteed (F3 — design constraint).**
   `run_id` is minted once per `AutoBuildOrchestrator` (`autobuild.py:1567-1569`);
   `events.jsonl` is the **sole** artifact carrying `run_id`/`attempt`. But
   `AgentInvoker` defaults to `NullEmitter` (`agent_invoker.py:1488`) — most
   dispositions in this repo (interactive `/task-work`, hand-authored TASK-FIXes)
   have **no events.jsonl at all**. Therefore `run_id`/`attempt` MUST be nullable
   in the label schema, and the identity resolver must degrade to `(None, None)`
   — never fabricate. (Per the `absence-of-failure` rule family: absent identity
   stays absent.)

4. **Doc/schema drift discovered: no `event_type` field exists (F4 — hazard).**
   The instrumentation guide's `jq 'select(.event_type == "task.completed")'`
   examples (`autobuild-instrumentation-guide.md:497-518`) do not match the
   actual schema — `BaseEvent` and all subclasses (`instrumentation/schemas.py:107-353`)
   declare no `event_type`, and `JSONLFileBackend.emit()` injects none. The
   identity resolver must type-sniff **structurally** (`verification_status`+`turn_count`
   ⇒ TaskCompleted; `failure_category` ⇒ TaskFailed) and must scan for the last
   *lifecycle-shaped* record, not blindly take the final line (a crash can leave
   a trailing `llm.call`).

5. **Naming collision avoided: do not call this "disposition" (F5).**
   `guardkit/qa/formats/disposition_record.py` (F8, DF-017) already owns
   "disposition-record" with a *different* attribution vocabulary and a *different*
   `run_id` semantics (live-gate campaign id vs 9F43 orchestration id). The new
   module/CLI group must be named `label`, and consumers must never join the two
   `run_id` namespaces. (Per `namespace-hygiene.md`.)

6. **No Python-side disposition hooks exist today (F6).**
   All three landing points (`task-review.md` Phase 5 [A]ccept, `task-complete.md`
   finalize, `feature-complete.md` merge review) are prose/bash markdown. The
   proven wiring shape is the Phase 0 precedent at `task-review.md:647-664`:
   imperative `**EXECUTE** (Bash): guardkit <cmd>` + binary fallback + parse
   contract (TASK-FIX-3C9D / `structural-defence-beats-prompt-instruction.md`).
   Fleet decision DF-018 (task-complete demotion to a shared routine) is future
   work — hook independently now; absorb into the shared routine when it ships.

## Option Evaluation Matrix

| | A — Minimal writer, callers resolve | **B — Producer owns identity + path resolvers** | C — Fold into `qa/formats` as F16 |
|---|---|---|---|
| Complexity | 3 | **5** | 6 |
| Pros | Fastest | Archive-fork + identity resolution centralized, testable, rider-exact; keeps F8 namespace clean | Reuses format machinery |
| Cons | Three markdown commands each reinvent the worktree-vs-archive fork and identity join | Slightly more files | Collides with DF-017 F8; YAML-per-run ≠ append-only JSONL; wrong consumer |
| Verdict | Reject | **RECOMMENDED** | Reject |

## Recommended Architecture (Option B)

```
guardkit/labels/
├── schema.py     OutcomeLabelRecord (pydantic) + compute_label_id()   [nullable run_id/attempt]
├── writer.py     append_label_record() — THE one producer; fail-open, never raises
├── identity.py   events.jsonl run_id/attempt resolver (structural sniff, absence-safe)
└── paths.py      live-worktree vs archive-home target resolver (imports get_archive_root_from_env)
guardkit/cli/label.py   `guardkit label record` + `guardkit label coverage` (registered in cli/main.py)
installer/core/commands/{task-review,task-complete,feature-complete}.md   EXECUTE hooks
```

Disposition-source → verdict-class mapping table (frozen in LBL-004):
| Source | verdict_class |
|---|---|
| Coach verdict upheld at review | coach_correct |
| TASK-FIX close / operator-found defect | operator_caught |
| feature-complete merge review rejection/finding | merge_review_caught |
| live gate / production observation (manual CLI) | live_gate_caught |

## Task Breakdown

| ID | Title | Cx | Deps | Type | Wave |
|---|---|---|---|---|---|
| TASK-LBL-001 | labels package: schema + content-addressed label_id + append-only fail-open writer | 2 | — | scaffolding | 1 |
| TASK-LBL-002 | identity.py: absence-safe run_id/attempt resolver over events.jsonl (structural sniff) | 3 | 001 | feature | 2 |
| TASK-LBL-003 | paths.py: live-vs-archive sidecar target resolver (shares get_archive_root_from_env) | 3 | 001 | feature | 2 |
| TASK-LBL-004 | CLI: `guardkit label record` + `guardkit label coverage` (DC-class floor report) | 4 | 001-003 | feature | 3 |
| TASK-LBL-005 | Wire EXECUTE hooks into the three disposition markdown commands | 2 | 004 | documentation | 4 |
| TASK-LBL-006 | Test suite: label_id determinism, append-only/fail-open, identity degrade, both path branches, mapping table | 3 | 001-004 | testing | 4 |

Estimated effort: ~5–8 hours. Risk: Low. No new dependencies, no fleet infra.

## Context Used

- `.claude/rules/cli-wrapper-shares-client-acquisition-path.md` — shared-acquisition discipline applied to `get_archive_root_from_env` and the single writer
- `.claude/rules/namespace-hygiene.md` — F8 `disposition-record` collision check (F5)
- `.claude/rules/structural-defence-beats-prompt-instruction.md` / TASK-FIX-3C9D — EXECUTE-hook shape (F6)
- `.claude/rules/absence-of-failure-is-not-success.md` family — nullable identity constraint (F3)
- `ai-transition/docs/decisions/REGISTER.md` — DF-017 (F8 ownership), DF-018 (task-complete demotion, future)
- FEAT-OBSC record — 9F43 identity fields, 80FE archive seam, D-OBS-1/D-OBS-4

## Decision Matrix

| Option | Score | Effort | Risk | Recommendation |
|--------|-------|--------|------|----------------|
| A minimal | 55/100 | 3-4h | Medium (caller drift) | No |
| **B producer-resolvers** | **88/100** | 5-8h | Low | **Yes** |
| C qa/formats | 40/100 | 6-9h | Medium (namespace) | No |
