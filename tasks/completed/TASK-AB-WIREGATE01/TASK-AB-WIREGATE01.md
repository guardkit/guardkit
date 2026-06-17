---
id: TASK-AB-WIREGATE01
title: Post-wave mocked-seam + composition-root wiring gate
status: completed
task_type: feature
priority: high
complexity: 7
created: 2026-06-17T11:00:00Z
updated: 2026-06-17T11:00:00Z
completed: 2026-06-17T11:00:00Z
completed_location: tasks/completed/TASK-AB-WIREGATE01/
previous_state: in_review
state_transition_reason: "task-complete: all ACs delivered, 86 tests green across both repos"
tags: [autobuild, quality-gate, wiring, false-green, stack-agnostic]
source: docs/retro/autobuild-retro-xref-2026-06-17.md
provenance: lpa-platform-poc FEAT-POC-006 (voice autobuild retro)
---

# Task: Post-wave mocked-seam + composition-root wiring gate

## Description

A whole feature can pass **every per-task Coach + the full unit suite** yet be
**non-functional**, because the "integration" tests mock the very seam they claim to
integrate and the composition root wires services up wrong. Observed in FEAT-POC-006
(lpa-platform-poc): router/integration tests did `AsyncMock(spec=VoiceService)` of the
primary in-repo service, and `main.py` constructed a service with the wrong/missing
`__init__` args — 345 tests green, feature dead.

This is the same **green ≠ correct** class FEAT-FAUD exposed locally (synthetic tests
that encode the implementation's own wrong assumption), and a genuine extension of
`.claude/rules/evidence-boundary-narrower-than-write-surface.md`: per-task Coach
isolation is an evidence aperture **narrower than the assembled-feature write surface**.

Current guardkit has only *partial* coverage: `mocked_seam` / `UNWIRED_PATH` wiring
evidence (`coach_evidence.py:204-239`) and a `direct_mode_wiring_gap` *must_fix*
(`autobuild.py:6349-6369`) — but that gate fires **only on a registered bin-entry in
direct mode**, not for a normal feature wave, and does not assert seam-mocking or
constructor arity.

## Acceptance Criteria

- [x] A **post-wave** wiring gate that runs after a feature wave completes (not just
      per-task) and surfaces findings as Player feedback (not a hard terminator — per
      `smoke-gate-is-feedback-not-terminator.md`).
      → `FeatureOrchestrator._run_post_wave_wiring_gate` (feature_orchestrator.py),
      wired into the wave loop after the smoke gate; bounded by
      `GUARDKIT_WIRING_GATE_MAX_RETRIES` (default 1); never hard-terminates on findings.
- [x] **Mocked-seam check:** flags an integration-tier test that mocks a **primary
      in-repo service seam** (e.g. `AsyncMock(spec=<Service>)` / `MagicMock(spec=...)`
      / `patch("<pkg>.<Service>")`) where `<Service>` is a first-party module the
      feature is supposed to wire together. Pure third-party / boundary mocks
      (HTTP clients, DB drivers) are NOT flagged.
      → extended `mock_call_query` in guardkitfactory `wiring/dialects/python.py`
      (spec-mock constructors + `create_autospec`); authored-seam attribution +
      external-mock allowlist already in the analyzer.
- [x] **Composition-root arity check:** asserts the composition root (`main.py` /
      app factory / DI wiring) constructs each first-party service with all required
      `__init__` args — no missing/extra positional args vs the service's signature.
      → new `CTOR_ARITY` analysis in guardkitfactory `wiring/analyzer.py`
      (`_extract_ctor_signatures` / `_summarise_params` / `_summarise_call_args`).
- [x] **Stack-agnostic** per `.claude/rules/stack-plugin-architecture.md`: the static
      analysis uses **tree-sitter + per-language dialect descriptors**, NOT a
      Python-`ast` monolith. Day-one Python; the design must not hard-code one stack.
      → all new analysis is dialect query DATA on `WiringDialect`; js/ts/c# are clean
      no-ops (absent signal) until they populate the new fields.
- [x] **Absence-of-failure-safe** per `absence-of-failure-is-not-success.md`: when the
      analyzer cannot run (unsupported stack, no composition root found), the result is
      **absent/neutral**, never a silent pass and never a hard block.
      → `CtorArityResult` `ran=False` / `skipped_*` / `unsupported_stack` / `error`;
      gate collector returns `[]` for every absent signal; gate never terminates.
- [x] Regression fixtures reproducing the FEAT-POC-006 shape: (a) an integration test
      that `spec`-mocks a first-party service → flagged; (b) a composition root missing
      a required ctor arg → flagged; (c) a legitimate boundary mock → NOT flagged.
      → `guardkitfactory/tests/wiring/test_ctor_arity.py` (18 tests) +
      `tests/unit/orchestrator/test_wiring_gate.py` (21) +
      `tests/orchestrator/test_wiring_ctor_arity_seam.py` (4 cross-repo seam).

## Implementation Notes

- Builds on the existing `coach_evidence.py` `mocked_seam` / `UNWIRED_PATH` slices —
  widen from bin-entry-only to a post-wave wave-level gate.
- Likely lives alongside the post-wave smoke gate in `feature_orchestrator.py`
  (`_run_post_wave_smoke_gate` is the placement precedent) so a finding feeds back as
  turn-1 `seed_feedback`, bounded by a retry budget.
- Pair the design with a short companion `.claude/rules/` entry under the existing
  meta-frame: *"per-task-green is not feature-green; a mocked primary seam is absent
  integration evidence."*

## Provenance

FEAT-POC-006 voice autobuild retro (lpa-platform-poc). See the cross-reference report
`docs/retro/autobuild-retro-xref-2026-06-17.md` §3.1 (highest-value still-open item —
the only one that changes a correctness outcome, not just operator friction).
