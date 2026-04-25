---
id: TASK-OSI-002
title: "Validation gate refactor: credit orchestrator-invoked phases"
status: in_progress
created: 2026-04-25T00:00:00Z
updated: 2026-04-25T00:00:00Z
previous_state: backlog
state_transition_reason: "Automatic transition for task-work execution"
priority: high
task_type: feature
parent_review: TASK-REV-119C1
feature_id: FEAT-AB59
wave: 1
implementation_mode: task-work
complexity: 4
dependencies: []
tags: [autobuild, orchestrator, validation-gate, OSI, F4A1-followup]
consumer_context:
  - task: TASK-OSI-004
    consumes: SPECIALIST_RESULTS_JSON
    framework: "AgentInvoker._compute_agent_invocations_validation"
    driver: "json file at .guardkit/autobuild/{task_id}/specialist_results.json"
    format_note: "JSON object with phase_4 and phase_5 keys; each block has status/duration_seconds/error and phase-specific output fields"
---

# Task: Validation gate refactor — credit orchestrator-invoked phases

## Description

Extend `AgentInvoker` so that `_compute_agent_invocations_validation` (line
~5562 in `guardkit/orchestrator/agent_invoker.py`) credits orchestrator-
invoked specialists the same way it currently credits Player-invoked ones,
without modifying TASK-FIX-7A07's classifier.

Add a new method `_inject_specialist_records_into_task_work_results` that
merges Phase 4/5 records from `specialist_results.json` (produced by
TASK-OSI-004 and TASK-OSI-005) into `task_work_results.json` under the
`agent_invocations` key, tagged `source: "orchestrator"`. Player-emitted
Phase 4/5 entries (no source tag or `source: "player"`) are dropped during
the merge — structural double-count prevention.

Also audit `get_expected_phases` to ensure `workflow_mode == "direct"` is
treated as expecting Phase 3 only, so `direct` mode tasks do not trigger
false Phase 4/5 violations after this feature lands.

## Acceptance Criteria

- [ ] New method `_inject_specialist_records_into_task_work_results` on
      `AgentInvoker` reads `.guardkit/autobuild/{task_id}/
      specialist_results.json` and merges Phase 4/5 records into
      `task_work_results.json`'s `agent_invocations` list, tagged
      `source: "orchestrator"`.
- [ ] Player-emitted Phase 4/5 entries (entries with `phase` in
      `{"4", "5"}` and `source` absent or `"player"`) are dropped during
      the merge — orchestrator entries are the single source of truth.
- [ ] Method re-runs `_compute_agent_invocations_validation` after the
      merge and writes the updated `agent_invocations_validation` block
      back to `task_work_results.json`.
- [ ] If `specialist_results.json` is absent, method logs a warning and
      inserts empty Phase 4/5 records with `status: "skipped"` so the
      gate can still produce a structured `validator_error` shape — never
      raises.
- [ ] `get_expected_phases("direct")` returns a count that treats `direct`
      as Phase 3 only — no gate violation for `direct` mode tasks.
- [ ] Unit tests cover: (a) merge with no prior Phase 4/5 entries,
      (b) merge with stale Player-emitted Phase 4/5 entries (dedup
      verified), (c) `direct` mode bypass (validation passes with only
      Phase 3), (d) absent `specialist_results.json` produces structured
      `validator_error` not exception.
- [ ] All modified files pass project-configured lint/format checks with
      zero errors.

## Seam Tests

The following seam test validates the integration contract with the
producer task. Implement this test to verify the boundary before
integration.

```python
"""Seam test: verify SPECIALIST_RESULTS_JSON contract from TASK-OSI-004."""
import json
import pytest
from pathlib import Path


@pytest.mark.seam
@pytest.mark.integration_contract("SPECIALIST_RESULTS_JSON")
def test_specialist_results_json_format(tmp_path: Path):
    """Verify specialist_results.json matches the expected format.

    Contract: JSON object with phase_4 and phase_5 keys; each block has
              status/duration_seconds/error and phase-specific output fields.
    Producer: TASK-OSI-004 (test-orchestrator runner)
    """
    autobuild_dir = tmp_path / ".guardkit" / "autobuild" / "TASK-TEST-001"
    autobuild_dir.mkdir(parents=True)
    results_file = autobuild_dir / "specialist_results.json"
    results_file.write_text(json.dumps({
        "phase_4": {
            "status": "passed",
            "duration_seconds": 142.3,
            "error": None,
            "tests_run": 45,
            "tests_failed": 0,
            "coverage_pct": 87.0,
        },
        "phase_5": {
            "status": "passed",
            "duration_seconds": 38.1,
            "error": None,
            "issues": [],
            "quality_score": 8.5,
        },
    }))

    data = json.loads(results_file.read_text())
    assert "phase_4" in data, "specialist_results.json must contain phase_4 block"
    assert "phase_5" in data, "specialist_results.json must contain phase_5 block"
    for block_name in ("phase_4", "phase_5"):
        block = data[block_name]
        assert "status" in block, f"{block_name} must have status field"
        assert block["status"] in ("passed", "failed", "skipped"), \
            f"{block_name}.status must be passed/failed/skipped"
        assert "duration_seconds" in block, f"{block_name} must have duration_seconds"
```

## Implementation Notes

- Read `_compute_agent_invocations_validation` and
  `_extract_invocations_from_result_data` carefully before refactoring;
  the input source priority is `agent_invocations` list, fallback to
  `phases` dict.
- The dedup logic lives in the new merge helper only; do not pollute
  `_extract_invocations_from_result_data` with source-tag awareness.
- `get_expected_phases` audit may require a small tweak for `"direct"`
  workflow_mode — verify by reading the function and the `"direct"`
  call site (`_write_direct_mode_results` at line 4093).
- Reference: TASK-FIX-7A07 introduced the gate; do NOT modify the
  classifier logic, only the input ledger and the expected-phases map.

## Notes

- Wave 1, parallel-safe with TASK-OSI-001 and TASK-OSI-003.
- Producer of the Gate-Credit Contract (§4.2 in review report).
- Consumer of SPECIALIST_RESULTS_JSON (produced by TASK-OSI-004).
