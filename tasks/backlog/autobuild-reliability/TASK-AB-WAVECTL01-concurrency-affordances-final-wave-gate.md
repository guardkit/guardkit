---
id: TASK-AB-WAVECTL01
title: Wire recommended_parallel into ParallelConfig, final-wave smoke-gate validation, auto-serialise-overlap default-on
status: backlog
created: 2026-07-04T09:34:00Z
priority: high
tags: [autobuild, parallel-waves, max-parallel, feature-yaml, smoke-gate, feature-plan]
complexity: 5
source: docs/retro/autobuild-retro-xref-2026-07-04.md
---

# Task: Concurrency affordances — recommended_parallel wiring, final-wave gate validation, overlap default

> **Implementation in progress 2026-07-04 (same session that filed this task); this
> file is the tracking record.**

## Description

Sourced from the 2026-07-04 retro cross-reference, §5 items 6+10 (R2/R3).
Three related affordance gaps:

1. **`recommended_parallel` is dead config (C2).** It is parsed
   (`feature_loader.py:272-274`) and written by the planner
   (`generate_feature_yaml.py:~836`) but consumed by **nothing** in the
   orchestrator — a false affordance. FEAT-SMP-001.yaml's
   `recommended_parallel: 2` was inert; the R2 retro's "resolution" of
   setting it to 1 would have done nothing. Wire it into `ParallelConfig` as
   a static input with **documented precedence: env > flag > YAML >
   auto-detect** (or delete it from the schema — wiring is preferred since
   the planner already emits it).
2. **The cloud default is unbounded.** Auto-detect caps `max_parallel=1`
   only for **local** backends (`cli/autobuild.py:982-987`); a cloud SDK run
   resolves to `None` → `bound_concurrency` returns the coroutines
   **unbounded** (`parallel_strategy.py:153-154`). Revisit as part of the
   precedence wiring.
3. **Final-wave gate aperture (R3).** `after_wave: [2,3,4]` left the final
   waves ungated and `tests/` outside every gate. Add a loader warning when
   `smoke_gates.after_wave` does not cover the final wave, plus planner
   guidance to make the last gate full-suite (`tests/`). Note §4: full-suite
   last-wave gating is expressible **today** via
   `smoke_gates.after_wave: "all"` — this is validation + guidance, not a
   new mechanism.
4. **Plan-time overlap guard is opt-in.** The A7B3 `wave_overlap_detector`
   can auto-split overlapping waves but `--auto-serialise-overlap` is
   opt-in. Flip it **default-on** at plan time (with an explicit opt-out).

Corrections that scope this task (xref §2): `--max-parallel` +
`GUARDKIT_MAX_PARALLEL_TASKS` have existed on `autobuild feature` since
2026-02-27 (`cli/autobuild.py:781-801`, resolution `:967-987`) — do NOT file
a `--serial` flag; this task wires the *YAML* tier into the existing
resolution chain.

## Acceptance Criteria

- [ ] AC-001: `recommended_parallel` from the feature YAML is consumed by
      the orchestrator's concurrency resolution with documented precedence
      **env > flag > YAML > auto-detect**. `GUARDKIT_MAX_PARALLEL_TASKS`
      and `--max-parallel` continue to win over the YAML value.
- [ ] AC-002: The YAML tier feeds `resolve_max_parallel` (the single
      resolution point) so display and executor consume ONE decision — no
      second resolution path.
- [ ] AC-003: The precedence is documented in the feature-YAML schema docs
      and the `--max-parallel` help text.
- [ ] AC-004: Loader emits a warning when `smoke_gates.after_wave` is a list
      that does not include the final wave (and suggests
      `after_wave: "all"` or listing the final wave). No new opt-in boolean
      is added — this extends existing config validation.
- [ ] AC-005: `/feature-plan` planner guidance updated: the last smoke gate
      should be full-suite (`tests/`) — reflected in
      `generate_feature_yaml.py` output guidance and the feature-plan docs.
- [ ] AC-006: `--auto-serialise-overlap` defaults ON at plan time; an
      explicit flag disables it. Existing behaviour for plans with no
      detected overlap is unchanged.
- [ ] AC-007: Regression tests: (a) YAML `recommended_parallel` honoured
      when no env/flag set; (b) env/flag override YAML; (c) loader warning
      fires on final-wave gap and stays silent for `"all"`/covering lists;
      (d) plan-time default-on overlap serialisation with opt-out.

## Implementation Notes

File:line anchors from the xref (§2 C1/C2, §3 R2 items 2-3, §5 items 6+10):

- `guardkit/tasks/feature_loader.py:272-274` — `recommended_parallel` parse
  (currently dead).
- `guardkit/planning/generate_feature_yaml.py:~836` — planner writes it.
- `guardkit/cli/autobuild.py:781-801` — existing `--max-parallel` /
  `--max-parallel-strategy` flags; resolution at `:967-987`; local-only
  auto-detect cap at `:982-987`.
- `guardkit/orchestrator/parallel_strategy.py:153-154` —
  `bound_concurrency` returns coroutines unbounded when cap is `None` (the
  cloud default hazard).
- `resolve_max_parallel` (`parallel_strategy.py:50-118`) — the single
  resolution point both display (`feature_orchestrator.py:2280-2289`,
  `log=False`) and executor (`feature_orchestrator.py:3018-3030`) consume;
  the YAML tier plugs in here.
- `guardkit/tasks/feature_loader.py:1235-1265` — feature-YAML validation
  (currently dependencies only; add the final-wave smoke-gate warning here).
- A7B3 `wave_overlap_detector` + `--auto-serialise-overlap` (plan-time) —
  flip the default.

## Regression constraints

From xref §5/§6 — load-bearing, verify each before merging:

- **One resolution point for concurrency** (§6;
  `.claude/rules/display-must-derive-from-enforcement-source-not-proxy.md`):
  the YAML tier must be added *inside* `resolve_max_parallel` so the wave
  banner and the executor cannot diverge. Fingerprints to keep:
  two `resolve_max_parallel` calls in `feature_orchestrator.py` (display
  read-only `log=False` + executor authoritative);
  `min(max_parallel, wave_size)` in `cli/display.py`.
- **No new opt-in boolean for the gate validation**
  (`.claude/rules/activate-by-artefact-not-opt-in-flag.md`; xref §5 item 6
  "extend existing config (rule-compliant), no new opt-in boolean"): the
  final-wave check derives from the artefact (`smoke_gates.after_wave` vs
  the wave count), never from a new flag.
- **A7B2 overlap-forces-feedback veto and the contention amnesty are
  load-bearing** (§6): default-on serialisation at plan time does NOT
  justify removing the runtime contention machinery — operators can still
  hand-author overlapping waves.
- **Do not re-file solved things** (§4): `--max-parallel` /
  `GUARDKIT_MAX_PARALLEL_TASKS` exist; A7B3 plan-time detection and A7B2
  runtime gating exist. This task only wires the dead YAML tier, changes a
  default, and adds validation/guidance.
- **Smoke gates stay feedback, not terminators**
  (`.claude/rules/smoke-gate-is-feedback-not-terminator.md`): adding a
  final-wave gate via config keeps the existing bounded
  `seed_feedback` disposition; nothing here touches the retry budget or the
  C1 mark-gating.
