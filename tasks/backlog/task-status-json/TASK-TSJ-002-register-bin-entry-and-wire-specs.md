---
id: TASK-TSJ-002
title: Register task-status-json bin entry and wire --json flag into task-status specs
task_type: documentation
parent_review: TASK-REV-9DDE
feature_id: FEAT-9DDE
wave: 2
implementation_mode: direct
complexity: 2
dependencies: [TASK-TSJ-001]
priority: high
status: backlog
created: 2026-06-11T12:08:26Z
updated: 2026-06-11T12:08:26Z
tags: [task-status, json-output, bin-entries, command-spec]
consumer_context:
  - task: TASK-TSJ-001
    consumes: task-status-json
    framework: "GuardKit markdown-driven slash command (Claude-as-runtime)"
    driver: "Bash shell-out to ~/.agentecflow/bin symlink"
    format_note: "bin-entries.txt path must point at the actual script location installer/core/commands/lib/task_status_json.py; symlink name derives from basename with underscores → hyphens (task-status-json)"
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Register task-status-json bin entry and wire --json flag into task-status specs

## Description

Make the producer script from TASK-TSJ-001 reachable from `/task-status --json`:

1. Add `installer/core/commands/lib/task_status_json.py` to `installer/core/commands/bin-entries.txt` (with a comment explaining it is the `/task-status --json` producer), so `install.sh` exposes it as `~/.agentecflow/bin/task-status-json`.
2. Add a `--json` flag section to **both** command specs:
   - `installer/core/commands/task-status.md`
   - `.claude/commands/task-status.md`

   The section must instruct Claude: *when `--json` is passed, execute `python3 ~/.agentecflow/bin/task-status-json [TASK-ID] --base-path .` via the Bash tool and output its stdout verbatim — do NOT reformat, reorder, or annotate the JSON.* Include the schema v1 example for reader reference.
3. Replace the orphaned `export:json` mention in `.claude/commands/task-status.md` with a pointer to `--json` (closing the existing runner-without-producer orphan).

## Acceptance Criteria

- [ ] `bin-entries.txt` contains the new line with an explanatory comment, following the existing R1/R2 comment style
- [ ] `installer/core/commands/task-status.md` documents the `--json` flag with the verbatim-output execution instruction and schema v1 example
- [ ] `.claude/commands/task-status.md` documents the `--json` flag identically and no longer lists `export:json` as an unproduced format
- [ ] Both specs state that `--json` combined with a `TASK-ID` emits a single-task object
- [ ] Default (no-flag) behaviour of both specs is unchanged

## Seam Tests

The following seam test validates the integration contract with the producer task. Implement this test to verify the boundary before integration.

```python
"""Seam test: verify task-status-json contract from TASK-TSJ-001."""
from pathlib import Path

import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("task-status-json")
def test_task_status_json_bin_entry_resolves():
    """Verify the bin-entries.txt line points at an existing script.

    Contract: bin-entries.txt path must point at the actual script location
    installer/core/commands/lib/task_status_json.py
    Producer: TASK-TSJ-001
    """
    repo_root = Path(__file__).resolve().parents[3]
    manifest = repo_root / "installer/core/commands/bin-entries.txt"
    entries = [
        line.strip()
        for line in manifest.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    target = "installer/core/commands/lib/task_status_json.py"
    assert target in entries, f"{target} not listed in bin-entries.txt"
    assert (repo_root / target).exists(), f"{target} does not exist on disk"
```

## Implementation Notes

- Depends on TASK-TSJ-001 (the script must exist before the manifest references it — `install.sh` symlinks would dangle otherwise).
- Direct mode: small mechanical edits, no architectural review needed.
- Keep the two spec sections consistent with each other; the installer spec is the canonical wording.
