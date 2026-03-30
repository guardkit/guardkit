---
id: TASK-TI-027
title: Implement template extends mechanism in installer
status: completed
created: 2026-03-30T00:30:00Z
updated: 2026-03-30T10:35:00Z
completed: 2026-03-30T10:35:00Z
priority: p1
tags: [installer, template, extends, inheritance]
complexity: 5
parent_review: TASK-REV-32D2
feature_id: FEAT-TI
wave: 4
implementation_mode: task-work
depends_on: []
previous_state: in_review
state_transition_reason: "All acceptance criteria met, quality gates passed"
completed_location: tasks/completed/TASK-TI-027/
test_results:
  status: passed
  coverage: 65
  tests_passed: 127
  tests_failed: 0
  last_run: 2026-03-30T10:30:00Z
---

# Task: Implement Template Extends Mechanism in Installer

## Description

The `langchain-deepagents-weighted-evaluation` template uses `"extends": "langchain-deepagents"` in its manifest.json. The installer now supports this inheritance mechanism so that installing the extension template also installs the base template's components.

## Acceptance Criteria

- [x] `extends` field in manifest.json is parsed and honoured
- [x] Base template files installed before extension overlay
- [x] Extension files correctly override base files where paths match
- [x] `guardkit init langchain-deepagents-weighted-evaluation` works end-to-end
- [x] `guardkit init langchain-deepagents` still works independently
- [x] Tests verify the extends mechanism

## Implementation Summary

### New Functions (guardkit/cli/init.py)

1. `_load_manifest(template_dir)` - Loads manifest.json from a template directory
2. `_resolve_extends_chain(template_name)` - Walks the extends field to build base→extension install order, with circular reference protection
3. `_merge_manifests(base, extension)` - Merges two manifests (scalars: ext wins, dicts: shallow merge, lists: concatenate + dedup)
4. `_apply_single_template(template_dir, target_dir, overwritable=)` - Inner copy routine with overwrite control

### Modified Functions

5. `apply_template(template_name, target_dir, *, base_only=False)` - Now resolves extends chain, validates all templates exist, applies base-first overlay, writes merged manifest
6. `_cmd_init(...)` - Threads `base_only` parameter through
7. `init(...)` - CLI now has `--base-only` flag

### Key Design Decisions

- **Overwritable set pattern**: Tracks files created by previous templates in the chain. Extension templates can overwrite base template files, but pre-existing user files are never clobbered.
- **Circular reference protection**: `_resolve_extends_chain` uses a visited set to prevent infinite loops.
- **Backward compatibility**: Single-template chains (no extends) behave identically to the old code.

### Tests (tests/cli/test_init_extends.py)

25 tests covering:
- Manifest loading (valid, missing, invalid JSON)
- Chain resolution (single, extends, circular, multi-level)
- Manifest merging (scalars, dicts, lists with dedup)
- Full apply_template with extends (overlay, merged manifest, base-only flag, independence)
- Real template integration tests (langchain-deepagents + weighted-evaluation)

### Files Changed

- `guardkit/cli/init.py` — 4 new functions, modified `apply_template` + CLI wiring
- `tests/cli/test_init_extends.py` — New test file (25 tests)
