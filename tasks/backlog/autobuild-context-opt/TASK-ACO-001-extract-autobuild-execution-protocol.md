---
id: TASK-ACO-001
title: Extract AutoBuild execution protocol from task-work spec
task_type: scaffolding
parent_review: TASK-REV-A781
feature_id: FEAT-ACO
wave: 1
implementation_mode: task-work
complexity: 4
dependencies: []
status: pending
priority: high
---

# TASK-ACO-001: Extract AutoBuild Execution Protocol

## Objective

Create two focused protocol reference files by extracting the AutoBuild-relevant subset of the full task-work specification (~165KB). These files are read at runtime by prompt builders, not injected via SDK setting_sources.

## Deliverables

### 1. `guardkit/orchestrator/prompts/autobuild_execution_protocol.md` (~15-20KB)

Extract from the full task-work.md only:
- **Phase 3**: Implementation (core execution loop)
- **Phase 4**: Testing and validation
- **Phase 5**: Code review and quality gates
- Report format specification (PLAYER_REPORT_SCHEMA)
- Quality gate thresholds (compilation 100%, tests 100%, line coverage >=80%, branch >=75%)
- File count constraints by documentation level
- Anti-stub rules (critical for quality)

### 2. `guardkit/orchestrator/prompts/autobuild_design_protocol.md` (~10-15KB)

Extract from the full task-work.md:
- **Phase 1.5**: Task context loading
- **Phase 2**: Implementation planning
- **Phase 2.5B**: Architectural review (simplified for autobuild — skip subagent, inline check only)
- **Phase 2.7**: Complexity evaluation
- Output format specifications

### 3. `guardkit/orchestrator/prompts/__init__.py`

Create a protocol loading utility:

```python
def load_protocol(protocol_name: str) -> str:
    """Load a protocol file by name. Cached per process."""
    ...
```

## Acceptance Criteria

- [ ] `autobuild_execution_protocol.md` contains phases 3-5 with all quality gate thresholds
- [ ] `autobuild_design_protocol.md` contains phases 1.5-2.8 with simplified arch review
- [ ] Protocol files are self-contained (no references to "see section X" in the full spec)
- [ ] `__init__.py` provides `load_protocol()` function with file caching
- [ ] Total size of both protocol files is 25-35KB (not a bloated copy of the full spec)
- [ ] Anti-stub rules are preserved verbatim from the original spec
- [ ] Report format JSON schema is included in execution protocol

## Technical Notes

- The full task-work.md is at `~/.claude/commands/task-work.md` (158KB, 4,844 lines)
- These protocols are loaded once per Python process, not per SDK session
- The design protocol must encode phase-skipping decisions (skip 1.6, 2.1, 2.5A; lightweight 2.5B; auto-approve 2.8)
- Keep the PLAYER_REPORT_SCHEMA exactly as-is — TaskWorkStreamParser depends on it

## Files to Create

| File | Description |
|------|-------------|
| `guardkit/orchestrator/prompts/autobuild_execution_protocol.md` | Phases 3-5 execution protocol |
| `guardkit/orchestrator/prompts/autobuild_design_protocol.md` | Phases 1.5-2.8 design protocol |
| `guardkit/orchestrator/prompts/__init__.py` | Protocol loading utility |
