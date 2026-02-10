---
complexity: 5
created: 2026-02-10 11:20:00+00:00
dependencies:
- TASK-SC-004
- TASK-SC-006
feature_id: FEAT-SC-001
id: TASK-SC-009
implementation_mode: task-work
parent_review: TASK-REV-AEA7
priority: high
status: design_approved
tags:
- coach
- autobuild
- integration
- task-work
task_type: feature
title: Wire coach integration into coach_validator.py + task-work preflight
updated: 2026-02-10 11:20:00+00:00
wave: 4
---

# Task: Wire coach integration into coach_validator.py + task-work preflight

## Description

Two integration wiring tasks:

1. **Add architecture context to coach prompt** in `guardkit/orchestrator/quality_gates/coach_validator.py`
2. **Add pre-flight architecture suggestion** to task-work command specs

## Key Implementation Details

### Part 1: CoachValidator Integration

The existing `coach_validator.py` already has a Graphiti integration pattern (lines 44-50):

```python
try:
    from guardkit.knowledge.quality_gate_queries import get_quality_gate_config
    GRAPHITI_AVAILABLE = True
except ImportError:
    GRAPHITI_AVAILABLE = False
```

Follow this same pattern to add architecture context:

```python
# Add to imports section
try:
    from guardkit.planning.coach_context_builder import build_coach_context
    ARCH_CONTEXT_AVAILABLE = True
except ImportError:
    ARCH_CONTEXT_AVAILABLE = False
    build_coach_context = None
```

Find the method that builds the coach prompt (likely `validate()` or a prompt builder method) and add:

```python
# After existing prompt assembly, before LLM call
arch_context = ""
if ARCH_CONTEXT_AVAILABLE and build_coach_context:
    try:
        arch_context = await build_coach_context(
            task=task,
            client=client,  # From existing Graphiti integration
            project_id=project_id,
        )
    except Exception as e:
        logger.warning(f"[Graphiti] Failed to build coach architecture context: {e}")
        arch_context = ""

# Inject into coach prompt
if arch_context:
    prompt = f"{prompt}\n\n{arch_context}"
```

### Part 2: Task-work Preflight Suggestion

Add to both `.claude/commands/task-work.md` and `installer/core/commands/task-work.md`:

```markdown
### Pre-Implementation Architecture Check (Complexity >= 7)

If task complexity is 7 or higher and Graphiti has architecture context:

    This is a high-complexity task. Architecture context available:
       /impact-analysis TASK-XXX - see what this task affects
       /system-overview - review current architecture

    Proceeding with task-work...

This is informational only - it does not block or require user action.
```

### Existing CoachValidator Structure

Before modifying, read the full `coach_validator.py` to understand:
- Where the coach prompt is assembled
- How `task` dict is passed through
- Where `client` (GraphitiClient) is available
- What the validation return type looks like

The coach context should be injected into the prompt BEFORE the LLM validation call, not after.

## Acceptance Criteria

- [ ] `coach_validator.py` imports `build_coach_context` with graceful ImportError handling
- [ ] Architecture context injected into coach prompt for complexity >= 4
- [ ] No architecture context for complexity 1-3 (budget = 0)
- [ ] Import failure doesn't break CoachValidator (ARCH_CONTEXT_AVAILABLE = False)
- [ ] `build_coach_context` exception caught and logged, doesn't break validation
- [ ] Task-work preflight suggestion added to both command specs
- [ ] Preflight suggestion only shown for complexity >= 7
- [ ] Existing CoachValidator tests still pass (no regressions)

## Test Requirements

### Unit Tests (extend existing tests/unit/test_coach_validator.py or new file)

- `test_coach_context_injected_medium_complexity` — complexity 5, verify arch context in prompt
- `test_coach_context_skipped_simple_task` — complexity 2, no arch context
- `test_coach_context_import_failure` — ARCH_CONTEXT_AVAILABLE=False, validator works
- `test_coach_context_exception_handled` — build_coach_context raises, validator still works
- `test_coach_context_graphiti_unavailable` — client not connected, empty context

### Regression Tests

Run existing CoachValidator tests to verify no regressions:
```bash
pytest tests/unit/test_coach_validator.py -v
```

## Implementation Notes

- Read `coach_validator.py` thoroughly before modifying — it's a critical path
- Follow the EXACT pattern of existing `GRAPHITI_AVAILABLE` / `try: import / except ImportError`
- The coach prompt injection must be APPEND only — never modify existing prompt content
- Log with `[Graphiti]` prefix for consistency
- task-work.md modification is a small markdown addition (non-breaking)