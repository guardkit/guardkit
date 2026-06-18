# TASK-AB-WIREGATE01 — Implementation Plan

Post-wave mocked-seam + composition-root wiring gate. Complexity 7, cross-repo
(guardkit + guardkitfactory). Source: FEAT-POC-006 green≠correct retro.

## Design decisions (confirmed with operator, 2026-06-17)

1. **Cross-repo scope.** New composition-root constructor-arity (CTOR_ARITY)
   static analysis lands in `guardkitfactory.wiring` (the existing stack-agnostic
   tree-sitter engine), not a guardkit-side ast monolith. AC#4 satisfied by
   construction.
2. **Gate teeth.** The post-wave wiring gate feeds findings back to the Player as
   turn-1 `seed_feedback` and re-enters the wave, bounded by a new env
   `GUARDKIT_WIRING_GATE_MAX_RETRIES` (default 1). Absence-of-failure-safe.
3. **Feedback scope.** Only the two high-confidence correctness signals are
   turn-rejecting: (a) an integration-tier test mocking a **primary in-repo
   service seam** (mocked_seam findings with `authored_this_turn=True`), and
   (b) a **composition-root ctor-arity mismatch**. UNWIRED_PATH stays advisory
   (already surfaced to Coach as evidence; lower-confidence heuristic).

## Why the existing engine covers most of it

`guardkitfactory.wiring.analyze_wiring` already does MOCKED_SEAM + UNWIRED_PATH
over tree-sitter CSTs with per-language `WiringDialect` descriptors (python, js,
ts, c#), absence-of-failure-safe (`None` / `unsupported_stack` / `parse_degraded`
/ `error`, never a silent pass). guardkit already calls it **per-task** in
`coach_validator._run_wiring_analysis` (advisory evidence) and has a
`direct_mode_wiring_gap` must_fix that only fires on a registered bin-entry in
direct mode. The two real gaps are: **(1)** no post-wave, wave-aggregate gate that
feeds back, and **(2)** ctor-arity analysis does not exist.

## Phase A — guardkitfactory (analysis substrate)

- **A1. `WiringDialect` new fields** (frozen dataclass, all defaulted so js/ts/c#
  records and the guardkit consumer stay valid; ctor-arity is a no-op for
  dialects that leave them empty):
  - `composition_root_markers: tuple[str,...] = ()` — path substrings of
    composition roots (python: `("/main.py","main.py","__main__.py","/app.py",
    "app.py","/factory","container","/wiring","/di/","/bootstrap")`).
  - `constructor_signature_query: str = ""` — captures a class `@class` and its
    `__init__` parameters node `@params`.
  - `constructor_call_query: str = ""` — captures a constructor call's callee
    `@class` + argument list `@args`.
  - `param_self_names: tuple[str,...] = ()` — `("self","cls")` for python
    (excluded from required-arg count).
  - `param_default_node_types: tuple[str,...] = ()` — param node types that carry
    a default (python: `default_parameter`, `typed_default_parameter`).
  - `param_splat_node_types: tuple[str,...] = ()` — param node types that make
    arity unknowable (python: `list_splat_pattern`, `dictionary_splat_pattern`,
    `keyword_separator`). Presence ⇒ bias OK (no finding).
  - `param_required_node_types: tuple[str,...] = ()` — param node types that are a
    required positional-or-keyword param (python: `identifier`,
    `typed_parameter`).
  - `arg_keyword_node_types: tuple[str,...] = ()` — call-arg node types that are
    keyword args (python: `keyword_argument`).
  - `arg_splat_node_types: tuple[str,...] = ()` — call-arg splat (python:
    `list_splat`, `dictionary_splat`). Presence ⇒ bias OK.
- **A2. Populate python dialect** with the above.
- **A3. `_analyze_ctor_arity`** analyzer pass (one extra CST walk per dialect,
  reusing the already-parsed trees where practical):
  1. Build the **first-party service signature map** from authored targets: for
     each class with an `__init__`, count required params (required_node_types,
     minus self), record `has_splat`, `total_params`.
  2. Scan **composition-root files** (path matches `composition_root_markers`,
     non-test) for `constructor_call_query` matches whose `@class` is a
     first-party authored class.
  3. Emit a `CTOR_ARITY` finding (severity `warning`) when, for a call with no
     splat arg: `positional + keyword_named < required` (missing required arg) OR
     `positional > total_params` (extra positional) — and the callee class has a
     discoverable `__init__` with no `*args`/`**kwargs`. Bias OK on any
     uncertainty (splat in call or signature, no `__init__`, inherited ctor).
  4. Nest the result under a new top-level key `"ctor_arity"` in the
     `analyze_wiring` dict (mirrors `"mocked_seam"`): `{status, ran, skip_reason,
     dialect, language, findings}`. `ran=False` / skipped when no composition
     root or no signature query (unsupported dialect) — never a pass, never a
     block. Threaded through the `error` and `unsupported_stack` early-return
     dicts too.
- **A4. `smoke_test()`** compiles the new queries when present (malformed S-expr
  fails in Wave 0, not as a silent `unsupported_stack`).
- **A5. guardkitfactory tests** (`tests/wiring/test_ctor_arity.py`) +
  **AC#6 regression fixtures** at analyzer level: (a) integration test
  `AsyncMock(spec=VoiceService)` of a first-party seam → MOCKED_SEAM flagged;
  (b) `main.py` constructs `VoiceService(x)` but `__init__(self, x, y)` requires
  two → CTOR_ARITY flagged; (c) `patch("httpx.AsyncClient")` boundary mock → NOT
  flagged.

## Phase B — guardkit (orchestrator gate)

- **B1.** Read `GUARDKIT_WIRING_GATE_MAX_RETRIES` (default 1) in
  `FeatureOrchestrator.__init__`, next to `_smoke_gate_max_retries`. `0` disables
  feed-back (gate still runs + logs → advisory-only).
- **B2.** `_wave_authored_files(task_ids)` helper: for each task, read
  `task_work_results.json` from `_autobuild_candidate_dirs(task_id)`, union via
  the same presence-based logic as `coach_validator._compute_authored_set`
  (`files_authored` else `files_created ∪ files_modified`).
- **B3.** `_build_wiring_feedback(findings)` + `_run_post_wave_wiring_gate(...)`,
  modelled on `_run_post_wave_smoke_gate`:
  - Call `analyze_wiring(authored_files=<wave union>, worktree_path,
    task_type="feature", stack=<resolved from feature/template>)`.
  - Collect turn-rejecting findings = mocked_seam findings with
    `authored_this_turn=True` **+** ctor_arity findings. UNWIRED stays advisory.
  - Absence-of-failure-safe: result `None` / `status in {error,
    unsupported_stack, parse_degraded}` / no turn-rejecting findings ⇒ neutral
    (no feedback, no termination).
  - With findings and retries remaining: feed back as `seed_feedback`, re-enter
    the wave, decrement budget, re-run gate (REPLACE `wave_results[-1]`, never
    append). Honour `stop_on_failure` on a Coach-rejected re-run.
  - **Never hard-terminates** the feature (findings are warning-severity
    heuristics): on exhausted budget, log a prominent warning and continue. This
    is the literal "not a hard terminator" reading of AC#1.
- **B4.** Wire into the wave-enumerate loop right after the smoke-gate block
  (skip if smoke already terminated). Extend the `_mark_wave_completed` gating so
  a wave with unresolved turn-rejecting wiring findings is still marked completed
  after the retry budget is spent (a heuristic warning must not block resume) —
  but is NOT marked completed mid-retry.
- **B5.** guardkit tests: gate feeds back mocked-seam + ctor-arity, bounded retry,
  UNWIRED stays advisory, absence-of-failure-safe (None/error/unsupported ⇒ no
  feedback), replace-not-append, wave-aggregate authored union.

## Phase C — cross-cutting

- **C1.** Cross-repo seam test (`tests/orchestrator/...`): assert the real
  installed `guardkitfactory.wiring.analyze_wiring` returns the `ctor_arity` key
  and `WiringDialect` exposes the new fields — a factory version skew is a red CI
  build, not a runtime miss (mirrors `test_xrepo_contract_seam.py` /
  `test_evidence_repos_seam.py`).
- **C2.** Companion `.claude/rules/per-task-green-is-not-feature-green.md` under
  the existing meta-frame; cross-link the five sibling rules.
- **C3.** Run both suites; route state; commit.

## Absence-of-failure / meta-frame compliance

The gate pairs its binary verdict with positive-evidence preconditions:
mocked_seam requires a real `authored_this_turn=True` finding; ctor-arity
requires a discoverable signature + a real arity shortfall with no splat. Every
"can't tell" path (unsupported stack, no composition root, splat, parse-degraded)
is absent-signal — neutral, never a pass, never a block. Disposition = feed back
bounded, never bare-terminate (smoke-gate-is-feedback-not-terminator).
