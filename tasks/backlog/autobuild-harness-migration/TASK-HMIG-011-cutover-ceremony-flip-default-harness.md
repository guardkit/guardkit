---
id: TASK-HMIG-011
title: Wave 4 cutover ceremony — flip GUARDKIT_HARNESS default to langgraph + announce + canary observation
task_type: deployment
status: in_progress
created: 2026-06-04T13:30:00Z
updated: 2026-06-11T00:00:00Z
priority: critical
complexity: 3
deadline: 2026-06-22        # deliberately slipped 2026-06-11 — see "Decision note 2026-06-11" below
target_cutover_date: 2026-06-20   # re-derived D-2 from new deadline
target_flip_date: 2026-06-18      # re-derived; gated on the two conditions in the decision note
original_deadline: 2026-06-15     # Anthropic API-key validation enforcement hard date (external; see note)
parent_review: TASK-REV-HMIG
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 4
implementation_mode: manual    # deployment task with date checkpoints + observation window
intensity: standard
effort_hours: 2    # active dev/docs work; PLUS ~5 days of canary observation
depends_on:
  - TASK-HMIG-010          # full feature validation must pass first
  - TASK-HMIG-006.1        # all 3 unmigrated SDK call sites per Option (a) chosen 2026-06-04
  - TASK-HMIG-006.2        # cutover-day-blocker per its own frontmatter
  - TASK-HMIG-006.3        # third unmigrated SDK call site
related_tasks:
  - TASK-HMIG-009A         # canary GO (Reading 2) — see canary-analysis §8.6
  - TASK-HMIG-008R         # LLM Coach restoration (completed)
tags:
  - autobuild
  - cutover
  - deployment
  - langgraph-migration
  - hard-deadline
falsifier: "After D-7 (2026-06-08) flip: invoking `guardkit autobuild task TASK-XXX` with NO GUARDKIT_HARNESS env var set routes through LangGraphHarness (visible in logs as 'GUARDKIT_HARNESS=langgraph' or absence of 'claude_agent_sdk.subprocess_cli' lines during Player invocation). After D-5 (2026-06-10) announce: D-2 to D-0 observation window shows no failure-rate regression vs Wave 3 canary baseline (5/6 = 83.3% any-turn approve OR 4/6 = 66.7% first-pass — pick the operator's chosen reading from canary-analysis §8.6). If any regression: revert via env-var default flip and re-open this task."
---

# Task: Wave 4 cutover ceremony

## Decision note 2026-06-11 — deadline deliberately slipped to 2026-06-22

Operator decision (2026-06-11 review session, with the coach-arc retro): the
flip is **gated on evidence, not the calendar**. Two conditions before AC-001:

1. **First clean fresh-feature green** — FEAT-9DDE re-run after the
   import-path fix (TSJ shim/bin-entry; note the smoke-gate command invokes the
   script by repo-relative path, so TSJ-002's bin entry alone does not fix the
   gate — a `sys.path` shim under `__main__` or a gate-command change is needed).
2. **Coach substrate decision** — TASK-OPS-COACHMOE01 (26B MoE on the B-min
   path) resolved, so the cutover canary observes the substrate we intend to
   keep.

**On the original 2026-06-15 external date**: Anthropic API-key validation
enforcement proceeds regardless of this slip. From 06-15, the SDK path via
`ANTHROPIC_BASE_URL`-redirect may break for local-model use — operators must
set `GUARDKIT_HARNESS=langgraph` explicitly until the default flips. All
documented run recipes already do this (run-15-recipe onward), so the practical
exposure is limited to runs that omit the env var. If any consumer hits this
between 06-15 and the flip, escalate rather than rushing the flip.

Also noted at slip time: TASK-HMIG-010's `blocked_by: TASK-HMIG-013` is stale —
HMIG-013 is subsumed by TASK-OPS-COACHMOE01 (its AC-006 live smoke is delivered
there under the post-COACHSPLIT architecture).

## Spec (verbatim from parent review §7.4 + current code state)

### D-7 (target 2026-06-08): flip the default

Change one line in `guardkit/orchestrator/harness/selector.py:131`:

```python
# Before:
name = os.environ.get(env_var, "sdk").lower()
# After:
name = os.environ.get(env_var, "langgraph").lower()
```

> **Note on parent-review references**: §7.4 says "flip default `GUARDKIT_HARNESS` to `langgraph` in `guardkit/cli/autobuild.py`". That was written before TASK-HMIG-006 introduced the dedicated `selector.py` module (per its OQ-3 design decision). The actual default now lives at `selector.py:131`. `cli/autobuild.py` neither reads nor sets `GUARDKIT_HARNESS`.

SDK path remains **opt-in fallback** via explicit `GUARDKIT_HARNESS=sdk`. No SDK code removal in this task (parent review §7.5 explicitly defers Claude Code dependency removal to post-2026-06-15 as Phase 3).

Document in operator notes (see AC-004 below).

### D-5 (2026-06-10): CUTOVER announce

Communicate LangGraph as the recommended harness. SDK path stays available for emergency revert via `GUARDKIT_HARNESS=sdk`. Audiences:

- README + install docs in this repo
- CLAUDE.md (if it documents the harness)
- Any downstream consumers (jarvis, forge, dataset-factory per `docs/research/dgx-spark/gb10-memory-budget-and-macbook-offload.md`)
- Any operator-facing channel (Slack / email / whatever the operator uses)

### D-2 to D-0 (2026-06-13 to 2026-06-15): canary observation window

- No code changes during the window unless rollback is required.
- Watch for failure-rate regression vs Wave 3 baseline (TASK-HMIG-009A: 5/6 any-turn-approve = 83.3% on both harnesses; 4/6 first-pass = 66.7%).
- Any regression triggers revert via env-var default flip (one-line change in `selector.py:131` back to `"sdk"`).
- 2026-06-15 D-0: Anthropic API-key validation enforcement begins. SDK path via `ANTHROPIC_BASE_URL` redirect to llama-swap may break for any consumer that hasn't migrated; LangGraph path is unaffected (uses `OPENAI_BASE_URL`).

## Acceptance Criteria

- [x] **AC-001** — `selector.py:131` default flipped from `"sdk"` to `"langgraph"`. Single-line commit with a clear message referencing this task ID + parent review §7.4. Land by D-7 (2026-06-08).
- [x] **AC-002** — Falsifier verified: with NO `GUARDKIT_HARNESS` env var set, `guardkit autobuild task TASK-{small fixture}` routes through `LangGraphHarness`. Verifiable via log line absence (`claude_agent_sdk.subprocess_cli` should NOT appear during Player invocation) or presence (`LangGraphHarness` instantiation).
- [x] **AC-003** — Existing test suite still passes with `GUARDKIT_HARNESS=sdk` explicit (SDK path remains fully functional as fallback). No SDK code removed.
- [x] **AC-004** — Operator-facing documentation updated:
  - `README.md` (if it documents harness selection)
  - `CLAUDE.md` files (root + `.claude/CLAUDE.md` if relevant)
  - `docs/guides/` autobuild guides (`autobuild_local_vllm.md` at minimum)
  - **New deprecation/migration note**: brief paragraph explaining the new default, how to opt back to SDK, expected duration of SDK fallback (until Phase 3 post-2026-06-15+).
- [ ] **AC-005** — D-5 (2026-06-10) cutover announce sent. Operator-determined channel + audience. Cross-link to this task ID for traceability.
- [ ] **AC-006** — D-2 to D-0 observation window: no failure-rate regression vs Wave 3 baseline. Observation evidence captured (link to logs / canary re-runs / etc.) in this task's completion notes.
- [x] **AC-007** — Rollback procedure validated by dry-run: confirm that setting `GUARDKIT_HARNESS=sdk` in a fresh shell environment routes through `ClaudeSDKHarness` (existing AC-001D path proven this works pre-flip; verify post-flip the SDK fallback still works).
- [ ] **AC-008** — On 2026-06-15 D-0: if no regression observed in window, mark this task complete + file post-cutover follow-ups (see "Post-cutover follow-ups" below). If regression observed, file rollback task + escalate.

## Cutover execution note (2026-06-16)

The flip landed **2026-06-16** (this session). Status: **flip + verifiable ACs
done; announce + observation window remain operator follow-ups.**

**Done (verified this session) — AC-001, 002, 003, 004, 007:**
- **AC-001** — default flipped in `selector.py`, centralised into a single
  `DEFAULT_HARNESS = "langgraph"` constant so the documented one-line rollback is
  real. Consumers updated to read it: `cli/doctor.py`, and
  `quality_gates/coach_validator.py` (the harness snapshot **and** the
  load-bearing `_is_langgraph_harness` gate — without this the post-flip default
  would have been mis-detected as non-langgraph). The task's `selector.py:131`
  reference is stale; the default now resolves in `select_harness()`.
- **AC-002** — falsifier verified: with `GUARDKIT_HARNESS` unset,
  `select_harness(cwd=...)` returns `LangGraphHarness` and `claude_agent_sdk` is
  never imported during selection.
- **AC-003** — suite green with the flip; SDK-path tests opt into
  `GUARDKIT_HARNESS=sdk` explicitly (selector, coach-timeout, sdk-session-config,
  task-work-interface, generator-close, sdk-environment-parity, agent-invoker
  lazy-import). Two unrelated **pre-existing** reds remain
  (`test_env_var_routes_to_langgraph` — calls `select_harness(langgraph)` with no
  `cwd=`; `test_task_work_sdk_max_turns_is_50` — stale `assert 100 == 50`); both
  fail identically pre-flip (verified via stash) and are out of scope here.
- **AC-004** — `selector.py` docstring + `CLAUDE.md` AutoBuild section updated
  (new default, opt-back-to-SDK, `DEFAULT_HARNESS` rollback pointer). README and
  `docs/guides/autobuild_local_vllm.md` had no harness-selection content to
  update (the latter does not exist).
- **AC-007** — rollback routing verified post-flip: `GUARDKIT_HARNESS=sdk` →
  `ClaudeSDKHarness`; `GUARDKIT_HARNESS=langgraph` → `LangGraphHarness`.

**Remaining (operator / calendar) — AC-005, 006, 008:**
- **AC-005** — cutover announce (operator channel/audience). Not automatable.
- **AC-006** — observation window: no failure-rate regression vs the Wave-3
  baseline. FEAT-9DDE + FEAT-FAUD green (2026-06-14/16) are supporting evidence;
  capture formal window observations here.
- **AC-008** — mark complete + file Phase-3 follow-ups once the window passes
  clean. (Original external D-0 was 2026-06-15; deadline slipped to 2026-06-22.)

## Rollback procedure

The cutover is **fully reversible** for the entire lifetime of the SDK fallback:

```bash
# Per-invocation override:
GUARDKIT_HARNESS=sdk guardkit autobuild task TASK-XXX

# Permanent revert (one-line code change):
# Edit guardkit/orchestrator/harness/selector.py:131 back to:
#   name = os.environ.get(env_var, "sdk").lower()
# Commit, push, redeploy.
```

The parent review §7.5 explicitly retains the SDK path through 2026-06-15+ for this purpose (~250 LOC of `ClaudeSDKHarness` + `_invoke_with_role` body — low maintenance cost for genuine revert optionality).

## Out of scope (per parent review §7.5)

- **Phase 3 — Claude Code dependency removal from guardkit**: intentionally deferred to post-2026-06-15+ as a cleanup task. SDK adapter stays in-repo for revert optionality. File as `TASK-HMIG-012` (or whatever's next) after this task completes successfully + observation window passes clean.
- **ADR drafting** (`ADR-ARCH-031`, `ADR-ARCH-032`) — explicitly out of parent-review scope; downstream of decision points being settled.
- **OpenCode adoption** (research-doc Phase 1) — separate decision track.

## Post-cutover follow-ups (file after AC-008 succeeds)

- `TASK-HMIG-012` (or next): Phase 3 — remove `ClaudeSDKHarness` + `claude-agent-sdk` dependency from guardkit. ~250 LOC removal + dep cleanup. Estimate 4h.
- F6 mitigation work (substrate Player honesty under multi-turn iteration). Was punted from cutover per Reading 2; relevant for ongoing operator UX.
- TASK-HMIG-002R-PERMS-CUSTOM-MIDDLEWARE restoration when DeepAgents upstream supports permissions on execute-capable backends.
- TASK-HMIG-009B (optional full 18-rep canary) — only if larger-N validation is wanted.
- ADR-ARCH-031 / -032 drafting (per parent review §8 decision points being settled by the cutover).

## Pre-cutover gate checklist (verify before AC-001)

Before executing AC-001 (D-7 flip), all of these must be true:

- [ ] TASK-HMIG-006.1 completed (direct-mode TaskWork dispatch migrated)
- [ ] TASK-HMIG-006.2 completed (HarnessEvent helpers migrated; byte-compat parity inverted)
- [ ] TASK-HMIG-006.3 completed (Coach independent SDK invocation migrated)
- [ ] TASK-HMIG-010 completed (full feature validation passed ≥80% first-pass)
- [ ] TASK-HMIG-009A in `review_complete` or `completed` with cutover-decision documented (Reading 1/2/3 from canary-analysis §8.6)
- [ ] Operator has explicitly chosen which canary reading to ship under (Reading 2 was the working assumption post-Option-(a) sequencing 2026-06-04; verify still the operator's position)

## References

- **Parent review §7.4** (the spec this task implements): [`.claude/reviews/TASK-REV-HMIG-review-report.md`](../../../.claude/reviews/TASK-REV-HMIG-review-report.md) lines 1159-1167
- **Parent review §7.5** (what stays out of this window): same file, line 1167+
- **Code location for the flip**: [`guardkit/orchestrator/harness/selector.py:131`](../../../guardkit/orchestrator/harness/selector.py#L131)
- **Cutover-decision context**: [`docs/state/TASK-REV-HMIG/canary-analysis.md` §8.6](../../../docs/state/TASK-REV-HMIG/canary-analysis.md) — three readings (HALT / GO-with-caveat / need-larger-N)
- **Pre-cutover gate task**: [TASK-HMIG-010](./TASK-HMIG-010-full-feature-autobuild-validation.md)
- **Option (a) Wave-3 cleanup chain** (per operator 2026-06-04 decision): [TASK-HMIG-006.1](./TASK-HMIG-006.1-migrate-direct-mode-sdk-dispatch.md), [TASK-HMIG-006.2](./TASK-HMIG-006.2-migrate-helpers-to-harness-event-dispatch.md), [TASK-HMIG-006.3](./TASK-HMIG-006.3-migrate-coach-independent-sdk-invocation.md)
- **Cross-repo state at cutover time**: guardkitfactory's TASK-HMIG-002R, 002R-NOPERMS, 002R-NOVMODE, 001B, 007, 007F all completed; LangGraphHarness fully functional via the 5-layer fix chain proven by TASK-HMIG-009A run 6 + AC-003 batch.
