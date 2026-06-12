---
id: TASK-QAWE-003
title: MOCKED_SEAM evidence — wire the mock-seam scan into the bundle
task_type: feature
parent_task: TASK-HMIG-BDDWIRE
feature_id: FEAT-C332
wave: 3
implementation_mode: task-work
complexity: 4
dependencies: [TASK-QAWE-001]
priority: medium
status: completed
updated: '2026-06-12T20:06:40'
---

# Task: MOCKED_SEAM evidence integration (Wave 2)

## Description

Wire the Wave-0 `WiringAnalyzer` MOCKED_SEAM scan into the `mocked_seam` bundle field
(the analyzer + dialects already exist from Wave 0). Detects acceptance/integration
glue that mocks the authored production seam the scenario claims to verify. Advisory
only — no code override. Per `docs/features/qa-verifier-wiring-probes-scope.md` §4.2.
Independent of BDDWIRE.

## Acceptance Criteria

- [ ] **AC (MOCKED field wiring):** `mocked_seam` field populated at the
  complete-path return; surfaces via `_render_evidence_bundle_section`; `ran:false`
  + `skip_reason` when no acceptance files authored.
- [ ] **AC-006 (external-mock control):** acceptance file mocking allow-listed
  externals (`httpx`/`boto3` py; `fetch`/`axios` js; `HttpClient` c#) → no `warning`,
  recorded under `external_mocks_ignored`.
- [ ] **AC (advisory only):** MOCKED_SEAM produces **no** code override of the verdict
  (asserted by test); it is advisory evidence the synthesis verdict weighs.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation
- `pytest tests/orchestrator -k "mocked_seam or wiring" -v`
- Lint/format pass with zero errors.
