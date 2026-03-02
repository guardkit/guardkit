# Findings: Stale AutoBuild Architecture Documentation

## Problem Statement

The AutoBuild documentation describes a **subprocess delegation** architecture where the Player agent shells out to `guardkit task-work --implement-only`. This was replaced by an **inline prompt builder pattern** (TASK-ACO-002) to reduce context window usage from ~1,078KB to ~93KB per Player turn. Multiple documentation sources still reference the old architecture.

## Evidence

### Actual Architecture (Code)

**File**: `guardkit/orchestrator/agent_invoker.py`

The method `_invoke_task_work_implement()` (line ~3914) no longer invokes a subprocess. Instead it:

1. Calls `_build_autobuild_implementation_prompt()` (line ~3575) which:
   - Loads `autobuild_execution_protocol.md` via `load_protocol()`
   - Injects 7 sections: header, turn context, requirements, feedback, Graphiti context, protocol, plan locations
2. Invokes `claude_agent_sdk.query()` directly with `setting_sources=["project"]`
3. Reduced from `setting_sources=["user", "project"]` — saving ~985KB per Player turn

The Coach uses `_build_coach_prompt()` and also invokes the SDK directly.

**Vestigial naming**: The method name `_invoke_task_work_implement()` and the flag `use_task_work_delegation=True` are retained but no longer reflect subprocess delegation. The `USE_TASK_WORK_DELEGATION` environment variable defaults to `"false"` while `autobuild.py` hardcodes `True`.

### Stale Documentation

**1. `.claude/rules/autobuild.md`** (PRIMARY — highest impact)

Still describes:
- "Player delegates to task-work" architecture
- Subprocess invocation diagram showing `guardkit task-work --implement-only`
- Old context loading behavior

This file is loaded as a project rule, meaning every Claude Code session receives incorrect architecture guidance.

**2. Graphiti knowledge graph** (POTENTIAL)

May contain episodes seeded from the old documentation or from sessions where the old architecture was discussed. Stale Graphiti knowledge would propagate incorrect context to future AutoBuild sessions via the `digest+graphiti` profile.

**3. In-code comments and docstrings** (MINOR)

The method names (`_invoke_task_work_implement`, `use_task_work_delegation`) and some inline comments in `agent_invoker.py` still reference "task-work delegation" despite the implementation being inline prompt building.

## Impact

| Area | Severity | Description |
|------|----------|-------------|
| `.claude/rules/autobuild.md` | High | Every Claude Code session receives incorrect architecture docs |
| Instrumentation tasks | Medium | TASK-INST-005 and TASK-INST-007 needed updates (already done) |
| Graphiti knowledge | Medium | Stale architecture may propagate to future sessions |
| Developer onboarding | Low | New contributors may misunderstand the architecture |
| In-code naming | Low | Vestigial method/flag names — functional but misleading |

## Scope of Updates Needed

### Must Update

1. **`.claude/rules/autobuild.md`**
   - Replace subprocess delegation diagram with prompt builder pattern
   - Document `_build_autobuild_implementation_prompt()` as the Player entry point
   - Document `_build_coach_prompt()` as the Coach entry point
   - Document `setting_sources=["project"]` and context budget (~93KB)
   - Reference TASK-ACO-002 as the change that introduced this

2. **Graphiti knowledge audit**
   - Search for episodes referencing "task-work delegation" or "shells out to task-work"
   - Update or deprecate stale episodes
   - Seed correct architecture description

### Should Update

3. **In-code naming** (lower priority, can be separate task)
   - Consider renaming `_invoke_task_work_implement()` → `_invoke_player_implementation()`
   - Consider renaming `use_task_work_delegation` flag → `use_inline_prompt_builder`
   - Update associated docstrings and comments

### Already Updated

- `tasks/backlog/autobuild-instrumentation/TASK-INST-005-instrument-agent-invoker.md` — Architecture Note added
- `tasks/backlog/autobuild-instrumentation/TASK-INST-007-role-specific-digests.md` — Integration with Prompt Builder Pattern section added

## Recommended Approach

This is a documentation/refactoring task, not a feature. Suggested workflow:

```bash
# Option A: Single task for doc updates
/task-create "Update stale AutoBuild architecture documentation" priority:high

# Option B: Review first, then implement
/task-review TASK-XXX --mode=technical-debt --depth=quick
```

The primary deliverable is updating `.claude/rules/autobuild.md` to accurately describe the prompt builder pattern. The Graphiti audit and in-code renaming can be follow-up tasks.

## Key Code References

| Component | File | Line(s) | Description |
|-----------|------|---------|-------------|
| Player prompt builder | `guardkit/orchestrator/agent_invoker.py` | ~3575 | `_build_autobuild_implementation_prompt()` |
| Player SDK invocation | `guardkit/orchestrator/agent_invoker.py` | ~3914 | `_invoke_task_work_implement()` |
| Coach prompt builder | `guardkit/orchestrator/agent_invoker.py` | — | `_build_coach_prompt()` |
| Execution protocol | `guardkit/orchestrator/prompts/autobuild_execution_protocol.md` | — | Multi-stack aware protocol loaded by prompt builder |
| Stale documentation | `.claude/rules/autobuild.md` | — | Still describes subprocess delegation |
| Delegation flag | `guardkit/orchestrator/agent_invoker.py` | ~100 | `USE_TASK_WORK_DELEGATION` env var |

## Context

- **Change origin**: TASK-ACO-002 (context optimization)
- **Motivation**: Reduce prefill from ~1,078KB to ~93KB per Player turn
- **When changed**: Prior to current session
- **Related feature**: FEAT-INST (AutoBuild Instrumentation) — the instrumentation tasks were updated to reflect the correct architecture during feature planning
