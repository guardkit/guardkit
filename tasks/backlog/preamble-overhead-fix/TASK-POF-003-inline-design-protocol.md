---
id: TASK-POF-003
title: Inline design phase execution protocol in pre-loop SDK prompt
status: backlog
task_type: implementation
created: 2026-02-15T14:00:00Z
updated: 2026-02-15T14:00:00Z
priority: high
complexity: 5
tags: [autobuild, preamble, performance, main-fix]
parent_review: TASK-REV-A781
feature_id: preamble-overhead-fix
implementation_mode: task-work
wave: 2
parallel_group: wave-2
dependencies: [TASK-POF-001]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Inline Design Phase Execution Protocol

## Description

The pre-loop quality gate currently invokes `/task-work TASK-XXX --design-only` via SDK, which requires `setting_sources=["user", "project"]` to find the `/task-work` skill in `~/.claude/commands/`. This loads ~1MB of commands into the session context.

**Fix**: Instead of invoking the skill, inline a slim version of the Phases 1.5-2.8 execution protocol (~15-20KB) directly in the SDK prompt. Switch `setting_sources` to `["project"]` (~78KB), eliminating ~840KB of unnecessary context loading.

## Root Cause (from TASK-REV-A781)

```python
# Current: task_work_interface.py:352-361
options = ClaudeAgentOptions(
    setting_sources=["user", "project"],  # Loads ALL user commands (~839KB)
    # ... because the prompt is "/task-work TASK-XXX --design-only"
    # ... which requires finding the /task-work skill from ~/.claude/commands/
)
```

## Acceptance Criteria

- [ ] `TaskWorkInterface._build_design_prompt()` returns inline execution protocol, NOT `/task-work ...` skill invocation
- [ ] `TaskWorkInterface._execute_via_sdk()` uses `setting_sources=["project"]` (NOT `["user", "project"]`)
- [ ] Inline protocol covers Phases 1.5, 2, 2.5B, 2.7, 2.8 (the minimum needed for design)
- [ ] Inline protocol is ≤20KB (vs current 165KB full task-work spec)
- [ ] Pre-loop still produces valid `DesignPhaseResult` with plan, complexity, and architectural review
- [ ] Existing non-autobuild usage of task-work is unaffected
- [ ] Integration test: run pre-loop on a test task, verify plan output

## Files to Modify

1. `guardkit/orchestrator/quality_gates/task_work_interface.py`
   - `_build_design_prompt()` - Replace skill invocation with inline protocol
   - `_execute_via_sdk()` - Change setting_sources to `["project"]`
   - Add new method `_build_inline_design_protocol()` for the slim prompt
2. Possibly extract the execution protocol sections from `installer/core/commands/task-work.md` into a reusable template

## Implementation Notes

### What the inline protocol needs

The design phase prompt should instruct Claude to:
1. **Phase 1.5**: Read the task file, extract title/description/acceptance criteria
2. **Phase 2**: Generate implementation plan (files to modify, approach, test strategy)
3. **Phase 2.5B**: Run architectural review (SOLID/DRY/YAGNI scoring) - can be simplified for autobuild
4. **Phase 2.7**: Evaluate complexity (1-10 scale)
5. **Phase 2.8**: Auto-approve (no human present in autobuild)

### What it does NOT need

- Phase 1.6 (Clarification) - skipped in autobuild
- Phase 2.1 (Library Context / Context7) - optional, skip for speed
- Phase 2.5A (Pattern MCP) - optional, skip for speed
- The full task-work command spec (4,844 lines / 165KB)
- All 26 user command definitions
- Figma/Zeplin/template/agent commands

### Key constraint

The inline protocol must produce output that `_parse_design_result()` can still parse. Review the existing parser to ensure compatibility.

### Estimated savings

- Context: 1,078KB -> 78KB per session (93% reduction)
- First-turn processing: ~250K tokens -> ~25K tokens
- Expected time savings: ~600-800s per session
