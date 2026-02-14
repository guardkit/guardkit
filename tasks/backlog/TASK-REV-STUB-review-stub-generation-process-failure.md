---
id: TASK-REV-STUB
title: "Review: Stub generation despite quality gates — system_plan.py forensic analysis"
status: backlog
created: 2026-02-13T14:00:00Z
priority: high
tags: [review, quality-gates, stub-prevention, process-failure, system-plan]
feature_id: FEAT-SP-001
task_type: review
complexity: 7
---

# Review: Stub Generation Despite Quality Gates

## Problem Statement

`guardkit/planning/system_plan.py` is a 70-line stub containing only a docstring and `pass`. It was created by TASK-SP-006 (currently `in_review`) and left in place while TASK-SP-007 created a 400+ line command spec that references it. The result: running `/system-plan` generates markdown files (Claude Code follows the command spec) but **no Graphiti persistence occurs** because the orchestrator function does nothing.

This is not an isolated incident. The pattern of stubs being created, marked complete, and blocking downstream functionality has been identified as a recurring failure mode.

## Forensic Evidence

### The Stub

```python
# guardkit/planning/system_plan.py — 70 lines total
async def run_system_plan(...) -> None:
    # Stub implementation - will be fully implemented later
    logger.info(f"run_system_plan called with ...")
    pass
```

### What Should Exist (per TASK-SP-006 acceptance criteria)

TASK-SP-006 acceptance criteria — **ALL unchecked**:
- [ ] `guardkit system-plan "description"` launches interactive planning
- [ ] `--mode=setup|refine|review` flag overrides auto-detection
- [ ] Mode auto-detected: setup when no Graphiti architecture, refine otherwise
- [ ] CLI registered in guardkit/cli/main.py
- [ ] Unit tests for CLI argument parsing and flag combinations
- [ ] Unit tests for mode detection integration

### What Already Exists (working code that the stub ignores)

| Module | Status | Lines | Purpose |
|--------|--------|-------|---------|
| `graphiti_arch.py` | ✅ Fully implemented | 358 | `upsert_component()`, `upsert_adr()`, `upsert_system_context()`, `upsert_crosscutting()` |
| `entities/component.py` | ✅ Built | ~80 | ComponentDef dataclass |
| `entities/system_context.py` | ✅ Built | ~60 | SystemContextDef dataclass |
| `entities/crosscutting.py` | ✅ Built | ~70 | CrosscuttingConcernDef dataclass |
| `entities/architecture_context.py` | ✅ Built | ~90 | ArchitectureDecision dataclass |
| `.claude/commands/system-plan.md` | ✅ Full spec | 400+ | Complete interactive flow specification |
| `system_plan.py` (orchestrator) | ❌ **STUB** | 70 | `pass` — the critical gap |

The persistence layer (`graphiti_arch.py`) and entity definitions are complete. The command spec is complete. The ONLY missing piece is the ~200-line orchestrator that connects them.

### Task Status Anomaly

TASK-SP-006 is in `tasks/in_review/` despite:
- All acceptance criteria unchecked ([ ] not [x])
- The primary deliverable being a stub with `pass`
- No tests created (acceptance criteria require unit tests)
- No mode detection logic implemented
- No CLI registration completed

**How did a task with zero acceptance criteria met end up in `in_review`?**

## Root Cause Analysis Required

This review must investigate:

### 1. Feature Plan Gap: No Anti-Stub Enforcement

The FEAT-SP-001 feature plan decomposes into 8 tasks (SP-001 through SP-008). Tasks SP-001 through SP-005 (Wave 1-2) built real code — entity definitions, Graphiti operations, architecture writer. But SP-006 (Wave 3, the glue task) produced a stub.

**Question**: Does the feature plan specify that implementations must be functional, not stubs? The FEAT-FP-002 spec includes `Word count > 1500 (comprehensive guide, not a stub)` for documentation tasks — but there's no equivalent machine-verifiable anti-stub criterion for code tasks.

### 2. Quality Gate Bypass

The quality gate pipeline includes:
- Phase 4.5: Test Enforcement (zero-test anomaly detection)
- Phase 5: Code Review (requirements audit)
- Phase 5.5: Plan Audit (scope creep detection)

**Question**: How did a file containing only `pass` clear Phase 4.5 (zero-test anomaly should have flagged no tests for a FEATURE task) and Phase 5 (code review should have caught zero acceptance criteria met)?

### 3. Task State Transition Without Verification

TASK-SP-006 moved from `in_progress` to `in_review` without meeting its own acceptance criteria. The task-workflow rules say tasks in `in_review` have "Passed quality gates."

**Question**: Is there a verification step that checks acceptance criteria before state transition? If not, that's the gap.

### 4. The "Will Be Implemented Later" Pattern

The stub comment says `# Stub implementation - will be fully implemented later`. This is a deferred implementation anti-pattern. The feature plan created SP-007 as the "slash command spec" task and SP-006 as the "CLI command" task — but Claude Code may have interpreted SP-006's scope as "create the file structure and argument parsing" rather than "implement the full orchestration."

**Question**: Does the task decomposition create ambiguity between "scaffolding" and "implementation"?

## Recommended Outputs

This review should produce:

### A. Anti-Stub Rule (for `.claude/rules/`)

An explicit rule that:
- Defines what constitutes a stub (function body is `pass`, `raise NotImplementedError`, `# TODO`, or returns only hardcoded defaults)
- Makes stub creation a quality gate violation for FEATURE and REFACTOR task types
- Requires Coach to verify that the primary function actually executes its stated purpose
- Adds machine-verifiable acceptance criterion: "Primary function is not a stub (body > 10 meaningful lines, contains actual logic)"

### B. Acceptance Criteria Verification Gate

A quality gate check that:
- Parses task file for `- [ ]` (unchecked) vs `- [x]` (checked) criteria
- Blocks IN_REVIEW transition when < 80% of criteria are checked
- Flags as anomaly when a task has zero criteria checked

### C. Feature Plan Template Update

Add to task template in `/feature-plan`:
- **Anti-stub criterion**: "Implementation is functional (not a stub, placeholder, or TODO)"
- **Minimum code coverage**: "Primary function has at least one test exercising actual logic"
- **Coach validation**: "Coach verifies function executes its stated purpose by running it or inspecting behavior"

### D. TASK-SP-006 Rework

The actual fix:
- Replace the stub `run_system_plan()` with working orchestration logic
- Connect mode detection → question flow → entity creation → `graphiti_arch.py` upserts → architecture writer
- Add the missing unit tests
- Check all acceptance criteria

## Scope

- **In scope**: Root cause analysis, anti-stub rule creation, quality gate enhancement, template update
- **Out of scope**: Actually implementing `run_system_plan()` (that's a separate implementation task)
- **Depth**: Standard (requirements + architecture review)
- **Estimated effort**: 2-3 hours for analysis and rule creation
