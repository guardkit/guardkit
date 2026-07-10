---
id: TASK-LBL-004
title: "CLI: guardkit label record + guardkit label coverage"
status: backlog
created: 2026-07-10T12:40:00Z
updated: 2026-07-10T12:40:00Z
priority: high
task_type: feature
parent_review: TASK-REV-3359
feature_id: FEAT-0D1C
wave: 3
implementation_mode: task-work
complexity: 4
dependencies: [TASK-LBL-001, TASK-LBL-002, TASK-LBL-003]
tags: [observability, labels, obs-6, cli, d-s10-1]
consumer_context:
  - task: TASK-LBL-001
    consumes: append_label_record
    framework: "guardkit.labels writer (single shared producer)"
    driver: "guardkit/labels/writer.py"
    format_note: "ALL label writes route through append_label_record; the CLI must never open outcome_labels.jsonl itself"
  - task: TASK-LBL-002
    consumes: resolve_run_identity
    framework: "guardkit.labels identity resolver"
    driver: "guardkit/labels/identity.py"
    format_note: "Returns (Optional[str], Optional[int]); None means absent — serialize as null, never fabricate"
  - task: TASK-LBL-003
    consumes: resolve_label_target
    framework: "guardkit.labels paths resolver"
    driver: "guardkit/labels/paths.py"
    format_note: "Returns LabelTarget(directory, location, error); on error the CLI warns and exits 0 in --non-blocking mode"
---

# Task: CLI — `guardkit label record` + `guardkit label coverage`

## Description

Add the `label` Click group (`guardkit/cli/label.py`, registered in
`guardkit/cli/main.py`) exposing the hybrid writer surface (ASSUM-007) and the
D-S10-1 coverage report. Follow the repo's Layer A/B split
(`guardkit/cli/task.py:44-46`): plain functions do the work, Click commands are
thin wrappers. Do NOT build a parallel write path — everything routes through
the LBL-001 writer (see consumer_context).

## Subcommand 1: `guardkit label record`

Flags: `--task-id` (required), `--source` (required, see mapping table),
`--source-ref` (required, e.g. the TASK-REV id or `merge-review:FEAT-X`),
`--feature-id`, `--dc-class`, `--verdict-class` (explicit override of the
mapping), `--repo-root` (default cwd), `--non-blocking/--strict`
(default `--non-blocking`: any failure prints a warning and exits 0 — the
sidecar is an observer, never a gate; `--strict` exits non-zero for tests).

**Disposition-source → verdict-class mapping table (FROZEN — the contract
LBL-005's markdown hooks and the manual paths share):**

| `--source` value | verdict_class |
|---|---|
| `task-review` (coach verdict upheld at review) | `coach_correct` |
| `task-fix` (TASK-FIX close / operator-found defect) | `operator_caught` |
| `operator` (manual operator observation) | `operator_caught` |
| `merge-review` (feature-complete merge-review finding) | `merge_review_caught` |
| `live-gate` (production/live-gate observation, manual) | `live_gate_caught` |

Behaviour: resolve target dir (LBL-003) → resolve identity (LBL-002, from the
resolved dir so archived evidence still joins) → build record + label_id
(LBL-001) → append (LBL-001 writer). Echo the label_id and target path on
success.

## Subcommand 2: `guardkit label coverage`

Flags: `--dc-classes` (default `DC-03,DC-05,DC-08,DC-14` — the D-S10-1
mandatory set), `--floor` (default `10`), `--repo-root`, `--include-archive/
--no-archive` (default include: scan live `.guardkit/autobuild/*/outcome_labels.jsonl`
AND `archive_root/*/*/outcome_labels.jsonl`).

Output: per-dc_class label counts (deduped by `label_id` — content-addressed,
so dedupe is mechanical), unattributed count (records with `dc_class: null`),
and a ✅/❌ per mandatory class against the floor. Corrupt lines are skipped
with a warning, never fail the whole read. Exit 0 always (reporting, not
gating); `--strict` exits 1 when any mandatory class is under-floor.

## Acceptance Criteria

- [ ] `guardkit label record --task-id X --source task-review --source-ref TASK-REV-Y` writes one record with verdict_class coach_correct adjacent to X's evidence artifacts and prints the label_id
- [ ] Every row of the mapping table produces its documented verdict_class; an unknown --source errors listing valid values
- [ ] Re-running the identical record command yields a record with the SAME label_id (content-addressed idempotency); coverage dedupes them to one
- [ ] With no live evidence dir and an archived copy present, the record lands in the archive home (joinable by task_id)
- [ ] In --non-blocking mode an unwritable destination prints a warning and exits 0; --strict exits non-zero
- [ ] `guardkit label coverage` reports per-class counts across live + archive and flags classes under the floor
- [ ] No fleet service is contacted by either subcommand (node-local only)
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Test Requirements

- [ ] Unit tests in `tests/unit/cli/test_label_cli.py` via `click.testing.CliRunner`; archive-path tests pin `GUARDKIT_ARCHIVE_ROOT` hermetically (the only env var this feature reads, via LBL-003)

## Seam Tests

The following seam tests validate the integration contracts with the producer
tasks. Implement these to verify the boundaries before integration.

```python
"""Seam tests: verify LBL-001/002/003 contracts from the CLI consumer."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("append_label_record")
def test_record_routes_through_shared_writer(monkeypatch, tmp_path):
    """Contract: ALL writes go through guardkit.labels.writer.append_label_record.

    Producer: TASK-LBL-001
    Patch append_label_record at its definition site; invoke `guardkit label
    record`; assert the patched writer received the call (the CLI must not
    open outcome_labels.jsonl itself).
    """


@pytest.mark.seam
@pytest.mark.integration_contract("resolve_run_identity")
def test_absent_identity_serializes_as_null(tmp_path):
    """Contract: (None, None) from LBL-002 lands as JSON null, never a fabricated id.

    Producer: TASK-LBL-002
    Record against an evidence dir with no events.jsonl; parse the written
    line; assert record["run_id"] is None and record["attempt"] is None.
    """


@pytest.mark.seam
@pytest.mark.integration_contract("resolve_label_target")
def test_archive_fallback_uses_shared_root_resolver(monkeypatch, tmp_path):
    """Contract: archive target honours GUARDKIT_ARCHIVE_ROOT via the SHARED helper.

    Producer: TASK-LBL-003
    monkeypatch.setenv("GUARDKIT_ARCHIVE_ROOT", str(tmp_path / "arch")); no live
    dir; assert the record file appears under that root's <id>/<id>/ nesting.
    """
```
