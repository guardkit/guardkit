---
id: TASK-FIX-RWOP1.4b
title: Delete FeatureSpecCommand Python dead surface + its tests + FEAT-1253 import gates
status: backlog
task_type: refactor
created: 2026-04-22T00:00:00Z
updated: 2026-04-22T00:00:00Z
priority: medium
complexity: 3
tags: [runner-without-producer, feature-spec, dead-code, delete, rwop1]
parent_task: TASK-FIX-RWOP1.4
parent_review: TASK-REV-RWOP1
feature_id: FEAT-RWOP1
depends_on:
  - rwop1-sweep-commit  # Commit the uncommitted RWOP1 artifacts first (see Preconditions)
related_to: TASK-FIX-RWOP1.4
related_tasks:
  - TASK-FIX-RWOP1.4
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Delete FeatureSpecCommand dead surface

## Decision Origin

Execution sub-task for Part B of [TASK-FIX-RWOP1.4](TASK-FIX-RWOP1.4-feature-spec-coach-gating-and-dead-surface.md). Decision rationale + verification greps captured in [.claude/reviews/TASK-FIX-RWOP1.4-decisions.md](../../../.claude/reviews/TASK-FIX-RWOP1.4-decisions.md) §Part B.

Verdict: **DELETE**.

## Problem Statement

`guardkit/commands/feature_spec.py` (FeatureSpecCommand + its private helpers `detect_stack`, `scan_codebase`, `_read_input_files`, `write_outputs`, `seed_to_graphiti`) is orphan-unreachable from production code. The live contract for `/feature-spec` is Claude interpreting `installer/core/commands/feature-spec.md` prose. The Python module exists to back tests that test itself.

Verification greps (run 2026-04-22, captured in the decision doc):

| Check | Result |
|---|---|
| `guardkit/cli/` imports | 0 |
| `guardkit/orchestrator/` imports | 0 |
| `installer/core/commands/bin-entries.txt` entry | absent |
| `guardkit/commands/__init__.py` re-exports | none |
| Non-test production callers | 0 |
| `tests/unit/commands/test_feature_spec.py` refs | 32 |
| `tests/integration/test_feature_spec_e2e.py` refs | 12 |

`seed_to_graphiti` verification: not a functional mirror of `guardkit/integrations/graphiti/parsers/feature_spec.py::FeatureSpecParser` (per-scenario + per-assumption vs whole-file parse). BUT `seed_to_graphiti` is only called from `FeatureSpecCommand.execute()` (line 482), which has zero production callers — so the per-scenario seeding path is dead code, not live-but-shadowed code. DELETE loses nothing that was running.

## Scope

### In-Scope

1. **Delete the module**: `guardkit/commands/feature_spec.py`.
2. **Delete the tests**:
   - `tests/unit/commands/test_feature_spec.py`
   - `tests/integration/test_feature_spec_e2e.py`
3. **Remove FEAT-1253 import-dependent quality gates**. Edit `.guardkit/quality-gates/FEAT-1253.yaml` and remove these four gate entries:
   - `lint` (line 7) — references `guardkit/commands/feature_spec.py`
   - `unit_tests` (line 12) — references `tests/unit/commands/test_feature_spec.py`
   - `integration_tests` (line 17) — references `tests/integration/test_feature_spec_e2e.py`
   - `import_check` (line 22) — smoke-import of the deleted module
   Keep the remaining five gates (`command_definition_size`, `command_frontmatter`, `command_methodology`, `installer_copy`, `documentation_size`) — those are about the Claude prose + docs and remain valid.
4. **Update `guardkit/commands/__init__.py`**: the file currently has no re-exports for feature_spec, so no change likely needed — verify after deletion and add an explicit no-op note if still empty.
5. **Verify `installer/core/commands/feature-spec.md` prose is unchanged**: line 337 is the WIRE path (TASK-FIX-RWOP1.4a's concern); the prose about the orchestrator Python module, if any, should be examined and removed/softened. The prose is meant to describe the Claude-runtime path only.
6. **Run the full test suite** after deletion to ensure no other tests depend transitively on the deleted module or its test fixtures.

### Out-of-Scope

- **Do NOT** build a PROMOTE-path CLI (`guardkit feature spec` subcommand, bin-entries.txt entry, imperative rewrite in feature-spec.md prose). The DELETE decision forecloses that.
- **Do NOT** port `seed_to_graphiti`'s per-scenario/per-assumption logic into `graphiti/parsers/feature_spec.py::FeatureSpecParser`. The verification in the decision doc confirms per-scenario seeding is dead code — never invoked — so there is no working behavior to preserve. If a future CLI path for `/feature-spec` is ever wanted, per-scenario seeding can be added at that time.
- Refactor of `guardkit/integrations/graphiti/parsers/feature_spec.py::FeatureSpecParser` — that is the live CLI-side parser used by `guardkit graphiti parse` and stays untouched.
- Touching the TASK-FIX-RWOP1.4a Coach-gating work (independent sub-task, can run in parallel).

## Acceptance Criteria

- [ ] `guardkit/commands/feature_spec.py` deleted.
- [ ] `tests/unit/commands/test_feature_spec.py` deleted.
- [ ] `tests/integration/test_feature_spec_e2e.py` deleted.
- [ ] `.guardkit/quality-gates/FEAT-1253.yaml` has four gates removed (`lint`, `unit_tests`, `integration_tests`, `import_check`); five gates retained; YAML remains valid.
- [ ] `guardkit/commands/__init__.py` inspected; updated only if it still references the deleted module.
- [ ] `grep -r "FeatureSpecCommand\|from guardkit.commands.feature_spec\|guardkit.commands.feature_spec" --include="*.py"` returns zero matches outside `tasks/`, `docs/research/`, and historical `tasks/completed/` (historical references in completed task markdown are acceptable).
- [ ] `pytest` green across the suite (no orphan imports, no missing-fixture errors).
- [ ] Post-execution rerun of the runner-without-producer grep for `feature-spec.md` per the parent review's method; combined with the 1.4a landing, wiring rate for `feature-spec.md` hard-module imperatives ≥ 50 %.
- [ ] `installer/core/commands/feature-spec.md` prose scanned for any reference to the Python orchestrator; removed or softened if present.

## Implementation Notes

- **Order of operations**:
  1. Delete the test files first (prevents import-fail spam during later steps).
  2. Delete the module.
  3. Edit FEAT-1253.yaml (removing four gates, keeping five).
  4. Run full pytest suite. Any failures are likely transitive — investigate and remove/update.
  5. Grep for `FeatureSpecCommand` one final time across `guardkit/` and `installer/` and `tests/` — should be zero hits.
- **Historical task markdown references** (in `tasks/completed/TASK-FS-002/`, `tasks/completed/TASK-FSRF-*/`, `docs/research/feature-spec/`) reference the deleted module by path. These are historical records — do NOT edit them. The grep acceptance criterion scopes the check to production/test code.
- **TASK-ABE-002 reference** (`tasks/completed/TASK-ABE-002/TASK-ABE-002.md:205` mentions `detect_stack()` as a secondary signal). Check if that reference is load-bearing — if it's referenced from a live script or rule that still imports `detect_stack`, either port the one function into a live module or accept the minor capability loss. The verification grep already confirmed no live import, so this is expected to be a docs-only reference, but double-check during implementation.
- **`seed_to_graphiti` twin note**: the live parser at `guardkit/integrations/graphiti/parsers/feature_spec.py` is a whole-file episode parser driven by filename-prefix matching in the `guardkit graphiti parse` CLI. Deletion of the orchestrator-side `seed_to_graphiti` has no impact on the live CLI path. Do not touch the live parser.
- **Do NOT block TASK-COH-RUN1** on this task.

## Preconditions

- **Commit the RWOP1 sweep first.** The working tree on `main` currently carries uncommitted RWOP1 artifacts (RWOP1.1 wiring, RWOP1.2 nudges, FEAT-RWOP1 guide, orphan-cleanup subfolder, decision doc, and sub-task definitions). Commit that sweep before starting this sub-task so the 1.4b diff is contained to the deletion itself.
- No dependency on TASK-FIX-RWOP1.4a — 1.4a and 1.4b are independent and can run in parallel Conductor workspaces.

## Related

- Decision doc: [.claude/reviews/TASK-FIX-RWOP1.4-decisions.md](../../../.claude/reviews/TASK-FIX-RWOP1.4-decisions.md) §Part B
- Parent task: [TASK-FIX-RWOP1.4](TASK-FIX-RWOP1.4-feature-spec-coach-gating-and-dead-surface.md)
- Parent review: [docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md](../../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md) §Per-file findings (feature-spec.md), §Orphans #1, #2, #4
- Live twin (DO NOT TOUCH): [guardkit/integrations/graphiti/parsers/feature_spec.py](../../../guardkit/integrations/graphiti/parsers/feature_spec.py)
- Feature guide: [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) §Track B
