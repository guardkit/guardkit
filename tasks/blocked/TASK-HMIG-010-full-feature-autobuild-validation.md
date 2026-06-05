---
id: TASK-HMIG-010
title: Full feature autobuild end-to-end validation under LangGraph
status: blocked
previous_state: in_progress
state_transition_reason: "Run 3 (2026-06-05T06:36, ~70min, post-LGFM+SUMM-ROOT+MODEL-PROFILE) produced first real autobuild data: 2/3 tasks reached APPROVED state (IA03 turn 1, TP05 turn 1). GD02 (complexity 6) hit 50-min task budget AND Coach approved AFTER cancellation fired — F14 cancellation-race makes GD02's true verdict ambiguous, which directly blocks AC-008 falsifier computation. Filed F14 as TASK-FIX-CTOUT01 (re-blocks 010). Also filed F12 (TASK-FIX-LGFM3, 4th instance of model-threading-class) and F16 (TASK-FIX-FALK01, cosmetic Graphiti teardown). F13 (test-orchestrator SPECHANG timeout) and F15 (substrate slowness on complexity-6) recorded as substrate-quality findings in feature-run-analysis.md §6 — not code blockers."
task_type: validation
created: 2026-05-19T20:30:00Z
updated: 2026-06-05T09:00:00Z
priority: critical
complexity: 5
deadline: 2026-06-15
parent_review: TASK-REV-HMIG
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 3
parallel_group: 3B
implementation_mode: manual    # operator-monitored end-to-end run; /task-work produces scaffolding only
intensity: standard
effort_hours: 8
blocked_by:
  - TASK-FIX-CTOUT01  # F14 — cancellation race that makes GD02's verdict ambiguous (blocks AC-008 computation). ~3h fix.
# Soft-fail follow-ons (don't block 010, but should land before AC-008 verdict for clean signal):
#   - TASK-FIX-LGFM3   # F12 — coach_test role model-threading. Soft-fails to subprocess. ~30 min fix.
#   - TASK-FIX-FALK01  # F16 — Graphiti FalkorDB teardown race. Cosmetic. ~1h fix, deferrable.
# Substrate-quality findings recorded for AC-008 evidence:
#   - F13: test-orchestrator specialist hits SPECHANG 600s cap on qwen36-workhorse (run-3 line 289)
#   - F15: GD02 took 50min for 2 turns on complexity-6 task (substrate slow on this shape)
depends_on:
  - TASK-HMIG-009A  # canary 12-run batch passed 2026-06-04 — substitute for the originally-cited TASK-HMIG-009 which was halted at F1/F4
  # - TASK-HMIG-009 # ORIGINAL: blocked at F1/F4; superseded by 009A per TASK-REV-HM09 §7
falsifier: "A representative 3-task feature (target: FEAT-PEBR-style structure, ≥3 tasks across ≥2 waves) completes under GUARDKIT_HARNESS=langgraph with ≥80% of tasks passing on first attempt (matches LangGraph fleet baseline; comfortably exceeds the SDK baseline). Any task that fails first-pass must succeed on --resume; non-recoverable failures fail the falsifier and trigger Wave 4 cutover-halt."
tags:
  - autobuild
  - validation
  - feature-build
  - langgraph-migration
---

# Task: Full feature autobuild end-to-end validation

## Description

Wave 3's second task. After TASK-HMIG-009 confirms the LangGraph harness on
isolated canary tasks, run a full multi-task feature autobuild under
`GUARDKIT_HARNESS=langgraph` to validate the end-to-end orchestration —
multi-wave execution, parallel groups, feature-complete merge, Coach gating
across multiple tasks, etc. The canary tasks tested the harness; this test
tests the orchestration around the harness.

## Acceptance Criteria

- [ ] AC-001: Target feature selected and recorded in
      `.guardkit/autobuild/TASK-REV-HMIG-feature-target.json`. Selection criteria:
      ≥3 tasks, ≥2 waves, includes a BDD-gated task, includes a task with non-trivial state-bridge transitions, total estimated effort ≤8h orchestrator-time.
- [ ] AC-002: Feature run end-to-end with `GUARDKIT_HARNESS=langgraph` via
      `guardkit autobuild feature FEAT-XXX`.
- [ ] AC-003: Per-task outcome recorded in
      `.guardkit/autobuild/TASK-REV-HMIG-feature-results.json`:
      `task_id`, `wave`, `parallel_group`, `coach_decision`, `turns_used`, `first_pass_success`, `resume_used`, `wall_clock_seconds`, `notes`.
- [ ] AC-004: First-pass-success rate computed and compared to the canary
      baseline from TASK-HMIG-009. Significant divergence (>10pp drop) is a
      red flag and must be investigated before Wave 4.
- [ ] AC-005: Any first-pass failure → `--resume` retry; resume outcome
      recorded; analysis of why first-pass failed and whether the retry was
      successful.
- [ ] AC-006: Any non-recoverable failure documented with root-cause analysis
      in `docs/state/TASK-REV-HMIG/feature-run-incidents.md`. A non-recoverable failure means: Coach rejection that survives 3 task-work attempts, orchestrator crash, state-bridge corruption, or any failure the operator cannot resolve without code edits to the harness itself.
- [ ] AC-007: Feature-complete merge attempted. The merge succeeds (no
      conflict, no broken downstream consumer) — this exercises the
      `WorktreeManager` + `feature_complete` paths which are substrate-agnostic
      but must continue to work under LangGraph.
- [ ] AC-008: Falsifier evaluation:
  - If ≥80% first-pass-success AND no non-recoverable failure: proceed to Wave 4 cutover.
  - If <80% first-pass-success OR any non-recoverable failure: halt cutover. Escalate to operator with the incidents document.
- [ ] AC-009: Result analysis appended to
      `docs/state/TASK-REV-HMIG/feature-run-analysis.md` (separate from
      canary-analysis.md for clarity).

## Implementation Notes

- The "target feature" should be a real feature the operator wants built — this
  is a validation run AND a feature delivery. Don't synthesise a feature; pick
  one already in backlog that fits the selection criteria.
- Schedule for D-9 → D-7 so that result analysis informs the D-7 cutover-flip
  decision.
- If the feature's tasks have failures unrelated to the substrate (e.g.,
  pre-existing bugs in the orchestrator), distinguish those in the analysis
  — they don't fail the falsifier.
- TASK-HMIG-009's results gate this task. If canary fails the 75% threshold,
  this task does not run.

## References

- Review §7.3 — Wave 3 sequencing
- Review §11 — Falsifier for the central recommendation
- Review §5.10 — Cross-repo failure-rate asymmetry (80-90% LangGraph fleet baseline)
- TASK-HMIG-009 result artifacts

## Notes

Wave 4 cutover hinges on this task's outcome. If both TASK-HMIG-009 (now
substituted by TASK-HMIG-009A) and TASK-HMIG-010 pass their falsifiers, the
cutover flip at D-7 is a configuration change with high confidence. If either
fails, the cutover-flip PR should be held until the issue is resolved or the
falsifier explicitly relaxed by the operator with a recorded rationale.

## Operator handoff (2026-06-04, scaffolded by `/task-work TASK-HMIG-010`)

`/task-work` produced the **scaffolding** for this validation but did not
execute the feature autobuild run — that is operator-driven because it
costs real LLM tokens and ~8h orchestrator-time, and the AC-001 target
selection is a business decision.

### Scaffolded artefacts

| Path | Purpose |
|---|---|
| `.guardkit/autobuild/TASK-REV-HMIG-feature-target.json` | Candidate features + fit-against-AC-001 scoring + operator_pick slot. Operator fills the operator_pick block before running. |
| `.guardkit/autobuild/TASK-REV-HMIG-feature-results.json` | Per-task outcome schema + empty `task_outcomes` array. Operator appends to it after each task completes (the runner does not yet auto-emit; same gap as TASK-FIX-CANARY-PARSER). |
| `docs/state/TASK-REV-HMIG/feature-run-analysis.md` | Human-authored audit narrative. Sections 0/9 pre-filled; sections 1-8 to fill after the run. |
| `docs/state/TASK-REV-HMIG/feature-run-incidents.md` | Incident log for non-recoverable failures (AC-006). Empty until a non-recoverable failure occurs. |

### Dependency substitution noted

Original `depends_on: TASK-HMIG-009` is **blocked** at F1/F4 (pre-loop
bypass, worktree-manager-cwd-branch). The substitute **TASK-HMIG-009A**
completed 2026-06-04 with 5/6 = 83.3% on both harnesses (LangGraph
67% first-pass, SDK 50% first-pass), passing the central ≥75%
falsifier. Cutover GO recommended. Frontmatter updated accordingly.

### AC-001 selection: the load-bearing operator decision

3 backlog candidates + 1 alternative path presented in `feature-target.json` with explicit fit-scoring:

1. **autobuild-observability-fixes** *(RECOMMENDED)* — clean fit on structure + effort + state-bridge (GD02), runtime-agnostic (no Claude-Code-tied surfaces), real dogfooding value (the feature improves the autobuild surface that 010 is validating). Fails BDD criterion — relaxation rationale: 009A's 12-run batch already validated the BDD-plugin contract under qwen36-workhorse.
2. **graphiti-docs** — pure documentation, safer/lighter alternative. Lower run-time risk but under-validates the Coach's test-execution gates.
3. **graphiti-context-fixes** — smallest fit, probably too lightweight to stress-test the orchestration surface.
4. *(alternative path)* **design fresh via /feature-spec + /feature-plan** — adds ~1-2h design overhead, naturally produces BDD-gated tasks. Requires an operator-supplied feature idea.

Dropped from earlier scaffold: **beads-integration** (operator: never going to need), **feature-build-ux** (Claude-Code-tied surfaces — TTY/progress/polling — the LangGraph Player can't meaningfully exercise).

Operator must fill `feature-target.json:operator_pick` before proceeding.

### Pre-flight before running

```bash
# 1. Confirm 009A's validated substrate is still live.
curl -fs http://promaxgb10-41b1:9000/v1/models | jq '.data[].id' | grep qwen36-workhorse

# 2. Confirm LangGraphHarness still imports (cross-repo).
python -c "from guardkitfactory.harness import LangGraphHarness; print('ok')"

# 3. Confirm the picked feature's tasks are clean in backlog.
ls tasks/backlog/{picked_feature}/TASK-*.md

# 4. Dry-run the orchestration plan.
guardkit autobuild feature {picked_feature} --dry-run
```

### Execution (D-9 → D-7 per spec; ~8h total)

```bash
# Real run. Resumable.
GUARDKIT_HARNESS=langgraph \
  OPENAI_BASE_URL=http://promaxgb10-41b1:9000/v1 \
  OPENAI_API_KEY=llama-swap-local-key \
  guardkit autobuild feature {picked_feature} \
    --model qwen36-workhorse \
    2>&1 | tee .guardkit/autobuild/TASK-REV-HMIG-feature-run/run-1-stdout.log

# After each task, append outcome to feature-results.json:task_outcomes.

# On any first-pass failure:
guardkit autobuild feature {picked_feature} --resume

# On all-pass: attempt the feature-complete merge (AC-007).
guardkit autobuild complete {picked_feature}
```

### After the run completes

1. Fill `feature-results.json:aggregate_metrics` (compute first_pass_success_rate, delta-vs-009A).
2. Fill `feature-results.json:falsifier_verdict` (verdict, rationale, cutover_decision).
3. Fill sections 1-8 of `feature-run-analysis.md`.
4. If any non-recoverable failure: write incident entry in `feature-run-incidents.md`.
5. Tick AC-001 through AC-009 in this file based on what landed.
6. Per AC-008:
   - ≥80% first-pass-success AND zero non-recoverable: proceed to **TASK-HMIG-011** (cutover ceremony).
   - Anything else: **HALT cutover**, escalate to operator with incidents document.

### Caveats already known going in

- Runner does not auto-emit per-task records (same gap surfaced by 009A's TASK-FIX-CANARY-PARSER). Manual append to feature-results.json is the current shape. Filing TASK-FIX-FEATURE-RUNNER-EMIT is appropriate if the operator wants this fixed before/during the run, but it does not block 010 — manual append is tractable for ≤4-5 task slices.
- F6 (Player honesty collapse on multi-turn iteration on qwen36-workhorse) was definitive in 009A. At feature scale, F6's surface is wider — but 009A also showed F7 (unrecoverable_stall detection) fires correctly, so a single F6 hit per task should fail fast rather than burn compute.
- The AC-001 ≤8h bound is tight against the only fully-fitting candidate (beads-integration sliced to 4 tasks). If the operator picks a smaller candidate that relaxes BDD, the effective wall-clock will be ~4-6h.
