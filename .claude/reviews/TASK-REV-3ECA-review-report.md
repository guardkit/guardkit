# Review Report: TASK-REV-3ECA (Revised)

## Executive Summary

Review of the Graphiti knowledge graph seed functions for the FalkorDB migration. **Five findings** (revised from three after ADR analysis):

1. **FINDING-1 (High)**: `seed_command_workflows.py` has 7 episodes but 12+ CLI commands/workflows are missing
2. **FINDING-2 (Medium)**: `_cmd_seed()` display lists 13 categories but `seed_all_system_context()` seeds 18
3. **FINDING-3 (Low)**: Test `test_seed_command_workflows_creates_episodes` asserts exactly 7 episodes and will break after FINDING-1 fix
4. **FINDING-4 (High)**: 9 project ADRs exist but NONE are seeded by `guardkit graphiti seed` - only 3 feature-build ADRs are available via separate `seed-adrs` command
5. **FINDING-5 (Medium)**: `seed_architecture_decisions.py` duplicates the 3 feature-build ADRs in condensed form, creating redundancy

## Review Details

- **Mode**: Code Quality Review (Revised with ADR analysis)
- **Depth**: Standard
- **Task**: TASK-REV-3ECA - Review and update seed function for FalkorDB migration
- **Branch**: `graphiti-falkorDB-migration`

---

## FINDING-1: Missing Command Workflow Episodes (HIGH)

**File**: [seed_command_workflows.py](guardkit/knowledge/seed_command_workflows.py)

**Current state**: 7 episodes seeded (lines 26-127):
1. `workflow_overview` - Core 3-command workflow
2. `command_task_create` - /task-create
3. `command_task_work` - /task-work
4. `command_task_complete` - /task-complete
5. `command_feature_plan` - /feature-plan
6. `command_feature_build` - /feature-build
7. `workflow_feature_to_build` - Feature planning to build flow

**Missing commands** (confirmed against `installer/core/commands/` and `guardkit/cli/main.py`):

### Slash Commands (Claude Code skills)
| Command | Spec File | Priority |
|---------|-----------|----------|
| `/task-review` | `task-review.md` | HIGH - core workflow |
| `/task-refine` | `task-refine.md` | HIGH - core workflow |
| `/task-status` | `task-status.md` | HIGH - core workflow |
| `/feature-complete` | `feature-complete.md` | HIGH - core workflow |
| `/debug` | `debug.md` | MEDIUM |
| `/system-overview` | `system-overview.md` | MEDIUM |
| `/impact-analysis` | `impact-analysis.md` | MEDIUM |
| `/context-switch` | `context-switch.md` | LOW |

### CLI Commands (guardkit binary)
| Command | Source | Priority |
|---------|--------|----------|
| `guardkit review` | `guardkit/cli/review.py` | HIGH |
| `guardkit system-plan` | `guardkit/cli/system_plan.py` | MEDIUM |
| `guardkit graphiti capture` | `graphiti.py:capture` | MEDIUM |
| `guardkit graphiti search` | `graphiti.py:search` | LOW |
| `guardkit graphiti list` | `graphiti.py:list_knowledge` | LOW |
| `guardkit graphiti show` | `graphiti.py:show` | LOW |
| `guardkit graphiti clear` | `graphiti.py:clear` | LOW |
| `guardkit graphiti add-context` | `graphiti.py:add_context` | LOW |

### Missing Workflows
| Workflow | Priority |
|----------|----------|
| Review workflow: `/task-create task_type:review` -> `/task-review` -> `[I]mplement` -> `/task-work` | HIGH |
| Design-first workflow: `/task-work --design-only` -> approve -> `/task-work --implement-only` | MEDIUM (referenced in `workflow_overview` but no dedicated episode) |
| Debug workflow: `/debug` -> investigate -> fix -> verify | LOW |

**Recommendation**: Add 12 new episodes (8 commands + 2 CLI commands + 2 workflows), bringing total from 7 to 19.

### Proposed New Episodes

```
command_task_review       - /task-review with modes and decision checkpoint
command_task_refine       - /task-refine iterative refinement
command_task_status       - /task-status progress dashboard
command_feature_complete  - /feature-complete merge and archive
command_debug             - /debug systematic investigation
command_system_overview   - /system-overview architecture summary
command_impact_analysis   - /impact-analysis pre-task validation
command_context_switch    - /context-switch multi-project navigation
cli_guardkit_review       - guardkit review CLI with --capture-knowledge
cli_guardkit_graphiti     - guardkit graphiti subcommands (seed, status, verify, capture, search, show, list, clear, add-context)
workflow_review_to_implement - Review -> Decision -> [I]mplement -> task-work flow
workflow_design_first     - Design-only -> checkpoint -> implement-only flow
```

---

## FINDING-2: _cmd_seed() Display List Out of Sync (MEDIUM)

**File**: [graphiti.py:127-141](guardkit/cli/graphiti.py#L127-L141)

**Current display** (13 categories, lines 127-141):
```python
categories = [
    "product_knowledge",
    "command_workflows",
    "quality_gate_phases",
    "technology_stack",
    "feature_build_architecture",
    "architecture_decisions",
    "failure_patterns",
    "component_status",
    "integration_points",
    "templates",
    "agents",
    "patterns",
    "rules",
]
```

**Actual seeded categories** (18 categories, `seeding.py:150-168`):
```python
categories = [
    ("product_knowledge", ...),
    ("command_workflows", ...),
    ("quality_gate_phases", ...),
    ("technology_stack", ...),
    ("feature_build_architecture", ...),
    ("architecture_decisions", ...),
    ("failure_patterns", ...),
    ("component_status", ...),
    ("integration_points", ...),
    ("templates", ...),
    ("agents", ...),
    ("patterns", ...),
    ("rules", ...),
    ("project_overview", ...),         # MISSING from display
    ("project_architecture", ...),     # MISSING from display
    ("failed_approaches", ...),        # MISSING from display
    ("quality_gate_configs", ...),     # MISSING from display
    ("pattern_examples", ...),         # MISSING from display
]
```

**Missing from display** (5 categories):
1. `project_overview` (added by TASK-CR-005)
2. `project_architecture` (added by TASK-CR-005)
3. `failed_approaches` (added by TASK-GE-004)
4. `quality_gate_configs` (added by TASK-GE-005)
5. `pattern_examples` (added by TASK-CR-006-FIX)

**Recommendation**: Add the 5 missing categories to the display list in `_cmd_seed()`.

---

## FINDING-3: Test Episode Count Assertion Will Break (LOW)

**File**: [test_seeding.py:180-182](tests/knowledge/test_seeding.py#L180-L182)

```python
async def test_seed_command_workflows_creates_episodes(self):
    ...
    assert mock_client.add_episode.call_count == 7
```

After FINDING-1 fix adds ~12 new episodes, this assertion will need updating from `== 7` to `== 19` (or whatever the final count is). The docstring at `seed_command_workflows.py:18` also says "Creates 7 episodes" and will need updating.

---

## FINDING-4: Project ADRs Not Seeded (HIGH)

### Current ADR Seeding Architecture

There are **two separate ADR seeding paths**, neither of which covers all project ADRs:

| Path | Function | Invocation | What it seeds |
|------|----------|------------|---------------|
| Main seed | `seed_architecture_decisions()` | `guardkit graphiti seed` | 3 condensed feature-build lessons (not full ADRs) |
| Separate CLI | `seed_feature_build_adrs()` | `guardkit graphiti seed-adrs` | 3 full feature-build ADRs (ADR-FB-001/002/003) |

### Project ADRs NOT Seeded Anywhere

9 ADR documents exist on disk but **none** are seeded by either path:

| ADR | Title | Status | Priority to Seed |
|-----|-------|--------|-----------------|
| `0001-adopt-agentic-flow.md` | Adopt GuardKit System | Accepted | HIGH - foundational decision |
| `ADR-001-graphiti-integration-scope.md` | Graphiti Integration Scope | Accepted | HIGH - defines Graphiti's role |
| `ADR-003-falkordb-migration.md` | Migrate from Neo4j to FalkorDB | Accepted | HIGH - active migration, current branch |
| `ADR-GR-001-upsert-strategy.md` | Episode Upsert Strategy | Accepted | HIGH - core Graphiti pattern |
| `ADR-GBF-001-unified-episode-serialization.md` | Unified Episode Serialization | Accepted | MEDIUM - implementation pattern |
| `ADR-005-upfront-complexity-refactored-architecture.md` | Upfront Complexity Architecture | Proposed | MEDIUM - active subsystem |
| `ADR-002-figma-react-architecture.md` | Figma-to-React Architecture | Proposed | LOW - not yet implemented |
| `0003-remove-taskwright-python-template.md` | Remove guardkit-python Template | Accepted | LOW - historical, already done |
| `ADR-002-agent-discovery-strategy.md` (in `docs/adrs/`) | Agent Discovery Strategy | Proposed | LOW - not yet implemented |

### Recommendation

**Option A (Recommended)**: Use `guardkit graphiti add-context` with the `adr` parser type. This already works:
```bash
guardkit graphiti add-context docs/adr/ --type adr
guardkit graphiti add-context docs/architecture/ADR-GBF-001-unified-episode-serialization.md --type adr
```
Advantages: No code changes needed, uses existing infrastructure, ADR parser already handles ADR format.

**Option B**: Create a new `seed_project_adrs()` function in `seeding.py` that auto-discovers and seeds all ADR files from `docs/adr/` and `docs/architecture/`.
Advantages: Included in `guardkit graphiti seed --force` automatically.
Disadvantages: More code, duplicates `add-context` functionality.

**Option C**: Integrate into `seed_all_system_context()` by adding the existing `seed_feature_build_adrs` as a category AND adding a new file-based ADR scanner.
Advantages: Single `guardkit graphiti seed` command does everything.
Disadvantages: Mixing file-based and hardcoded seeding approaches.

### My Recommendation: Option A + integrate `seed_feature_build_adrs` into main seed

1. Add `seed_feature_build_adrs` to `seed_all_system_context()` categories list (currently only accessible via `seed-adrs` CLI)
2. Document that project ADRs should be seeded via `guardkit graphiti add-context docs/adr/ --type adr`
3. Add this as a step in the `_cmd_seed()` success output: "Run 'guardkit graphiti add-context docs/adr/ --type adr' to seed project ADRs"
4. Optionally: add `--include-adrs` flag to `guardkit graphiti seed` that auto-runs the `add-context` step

---

## FINDING-5: Duplicate ADR Content (MEDIUM)

**Files**:
- [seed_architecture_decisions.py](guardkit/knowledge/seed_architecture_decisions.py) - 3 condensed episodes
- [seed_feature_build_adrs.py](guardkit/knowledge/seed_feature_build_adrs.py) - 3 full ADR episodes

Both seed the same 3 decisions about feature-build (SDK invocation, FEAT-XXX paths, pre-loop design phase), but:

| Aspect | `seed_architecture_decisions` | `seed_feature_build_adrs` |
|--------|------------------------------|--------------------------|
| Episode names | `issue_sdk_not_subprocess`, `issue_feature_mode_paths`, `issue_preloop_must_invoke` | `adr_fb_001`, `adr_fb_002`, `adr_fb_003` |
| Group ID | `architecture_decisions` | `architecture_decisions` |
| Detail level | Condensed (decision + rationale) | Full (context, rationale, rejected alternatives, violation symptoms) |
| In main seed? | YES (`seed_all_system_context`) | NO (separate `seed-adrs` CLI only) |

**Problem**: If both are invoked, the same knowledge exists twice in the graph under different episode names. The condensed versions provide less value than the full ADRs.

**Recommendation**:
1. Replace the 3 condensed episodes in `seed_architecture_decisions.py` with a call to `seed_feature_build_adrs()`, OR
2. Remove `seed_architecture_decisions.py` entirely and integrate `seed_feature_build_adrs` into `seed_all_system_context()`
3. This also resolves the "not in main seed" problem from FINDING-4

---

## Implementation Tasks

### TASK-1: Add missing command workflow episodes (FINDING-1 + FINDING-3)
- **File**: `guardkit/knowledge/seed_command_workflows.py`
- **Action**: Add 12 new episodes for missing commands and workflows
- **Also**: Update docstring episode count, update test assertion in `test_seeding.py`
- **Effort**: ~30 min
- **Priority**: HIGH

### TASK-2: Sync _cmd_seed() display with actual categories (FINDING-2)
- **File**: `guardkit/cli/graphiti.py`
- **Action**: Add 5 missing categories to the display list at lines 127-141
- **Effort**: ~5 min
- **Priority**: MEDIUM

### TASK-3: Consolidate ADR seeding and add project ADRs (FINDING-4 + FINDING-5)
- **Files**: `guardkit/knowledge/seeding.py`, `guardkit/knowledge/seed_architecture_decisions.py`
- **Action**:
  1. Replace 3 condensed episodes in `seed_architecture_decisions` with call to `seed_feature_build_adrs`
  2. Add `seed_feature_build_adrs` to `seed_all_system_context()` categories list
  3. Add post-seed hint to `_cmd_seed()` about seeding project ADRs via `add-context`
  4. Update test that asserts `seed_architecture_decisions` creates 3 episodes
- **Effort**: ~20 min
- **Priority**: HIGH

### TASK-4: Run seed against FalkorDB and verify (AC-003, AC-004)
- **Action**: After TASK-1/2/3, run `guardkit graphiti seed --force` and `guardkit graphiti verify`
- **Prerequisite**: TASK-1, TASK-2, TASK-3
- **Effort**: ~10 min
- **Priority**: HIGH (validation gate)

---

## Verification Plan

After implementing all fixes:
1. `pytest tests/knowledge/test_seeding.py -v` - No regressions
2. `guardkit graphiti seed --force` - Seeds all 18+ categories including feature-build ADRs
3. `guardkit graphiti verify` - All test queries pass
4. `guardkit graphiti status --verbose` - All categories show episode counts
5. `guardkit graphiti add-context docs/adr/ --type adr` - Seeds 9 project ADRs
6. `guardkit graphiti search "FalkorDB migration"` - Returns ADR-003 content

---

## Risk Assessment

- **Low risk**: All changes are additive (new episodes, updating display list)
- **No breaking changes**: Existing episodes unchanged, only additions
- **Idempotent**: `upsert_episode()` ensures safe re-seeding
- **FalkorDB validated**: TASK-FKDB-001 confirmed 8/8 acceptance criteria pass
- **ADR consolidation**: Removing condensed duplicates is safe since full versions have strictly more information
