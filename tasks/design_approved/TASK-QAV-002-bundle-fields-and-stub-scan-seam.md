---
complexity: 5
consumer_context:
- consumes: analyze_stub_scan
  driver: guardkitfactory.wiring
  format_note: dict via .to_dict() with status + findings keys; status never maps
    to pass; None = probe did not run
  framework: guardkit CoachValidator lazy-import seam
  task: TASK-QAV-001
dependencies:
- TASK-QAV-001
feature_id: FEAT-10AC
id: TASK-QAV-002
implementation_mode: task-work
parent_review: TASK-REV-QAVG
priority: high
status: design_approved
task_type: feature
title: CoachEvidenceBundle sibling fields (stub_scan, coverage, behavioural_oracle)
  + stub_scan seam wiring
wave: 2
---

# Task: Bundle fields + stub_scan seam wiring

## Description

Extend `CoachEvidenceBundle`
(`guardkit/orchestrator/quality_gates/coach_evidence.py`) with THREE new
sibling fields directly after the existing Wave-1 wiring fields
(`wiring`/`mocked_seam`/`spec_gap`, ~L295-297):

```python
stub_scan: Optional[Dict[str, Any]] = None           # L2 anti-stub (this task)
coverage: Optional[Dict[str, Any]] = None            # L3 (populated by TASK-QAV-003)
behavioural_oracle: Optional[Dict[str, Any]] = None  # L4 (populated by TASK-QAV-004)
```

Wire `stub_scan` population into `CoachValidator`'s complete-path
`gather_evidence` return (beside the existing `_run_wiring_analysis()` bridge,
`coach_validator.py` ~L584-611) via the same **lazy import** seam
(`try/except ImportError → field stays None`). Render all three fields in
`_render_evidence_bundle_section` with the established findings-truncation
(first 20 + count), and append an advisory guard sentence for stub findings to
the absence-of-failure guards block. `coverage` and `behavioural_oracle` are
declared + rendered here but populated by Waves 3-4.

## Acceptance Criteria

- [ ] **AC-1:** the three fields exist as `Optional[Dict[str, Any]] = None`
  siblings; `to_dict()` carries them with no special-casing; docstring slots
  follow the existing wiring-field pattern.
- [ ] **AC-2 (absent-vs-empty):** for `stub_scan`, `findings:[]` with positive
  status is asserted distinct from the field being `None`; the partial/honesty
  early returns leave all three fields `None`.
- [ ] **AC-3 (seam):** with guardkitfactory importable, `stub_scan` is
  populated from `analyze_stub_scan` on the complete path for FEATURE /
  REFACTOR / INTEGRATION tasks; with the import absent, all three fields stay
  `None` and `gather_evidence` does not crash.
- [ ] **AC-4 (render):** >20 stub findings render as first 20 + "... and N
  more"; advisory guard sentence appears in the guards block; `coverage` /
  `behavioural_oracle` render when present (fixture dicts) without code change.
- [ ] **AC-5 (cross-repo seam test):** a seam test (mirroring
  `tests/orchestrator/test_wiring_ctor_arity_seam.py`) asserts the REAL
  installed `guardkitfactory.wiring` exposes `analyze_stub_scan` with the
  documented result keys — a factory version skew fails in CI, not on a live
  run.
- [ ] **AC-6 (behavioural check, dogfood):** an integration test drives
  `gather_evidence` end-to-end over a fixture worktree containing a stubbed
  authored file and asserts the rendered Coach prompt contains the stub
  finding — not a mock of the factory seam (the real dependency, per A2).
- [ ] **AC-7 (advisory only):** stub findings NEVER change the Coach decision
  deterministically in this task — no verdict override is added here.
- [ ] **AC-8:** existing guardkit suites remain green; all modified files pass
  project-configured lint/format checks with zero errors.

## Seam Tests

The following seam test validates the integration contract with TASK-QAV-001.

```python
"""Seam test: verify analyze_stub_scan contract from TASK-QAV-001."""
import pytest

pytest.importorskip("guardkitfactory.wiring")


@pytest.mark.seam
@pytest.mark.integration_contract("analyze_stub_scan")
def test_analyze_stub_scan_contract():
    """Verify analyze_stub_scan exists and returns the documented dict shape.

    Contract: dict via .to_dict() with status + findings keys; None = probe
    did not run. Producer: TASK-QAV-001.
    """
    from guardkitfactory.wiring import analyze_stub_scan  # real install, no mock
    import inspect

    params = inspect.signature(analyze_stub_scan).parameters
    assert "authored_files" in params
    assert "worktree_path" in params
    assert "task_type" in params
```

## Implementation Notes

- Reuse the authored-set discipline: `files_authored` when present, else
  `files_created ∪ files_modified`; never the git-enriched peer-contaminated
  set.
- The absent-signal invariant must survive serialization
  (`.claude/rules/absence-must-survive-every-reconciliation-layer.md`): a
  `None` field stays absent through `to_dict()` and any downstream reader.
- The bundle schema change is additive + versioned — it is the seam forge
  consumes; note the addition in the task completion summary for the
  dependable-forge overview update.