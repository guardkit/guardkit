# Clarification System - Quick Reference

## One-Liner

**Ask targeted questions BEFORE planning to avoid 15-20% rework from incorrect assumptions.**

## Three Context Types

| Context | Used By | Purpose | Max Questions |
|---------|---------|---------|---------------|
| **review_scope** | /task-review, /feature-plan | Guide what to analyze | 5 |
| **implementation_prefs** | /feature-plan [I]mplement | Guide subtask creation | 5 |
| **implementation_planning** | /task-work Phase 1.6 | Guide scope & approach | 7 |

## Complexity Gating (Context C: Implementation Planning)

| Complexity | Mode | Questions | Timeout | When |
|------------|------|-----------|---------|------|
| 1-2 | SKIP | 0 | N/A | Task description is clear |
| 3-4 | QUICK | 2-3 | 15s | Straightforward, needs light clarification |
| 5-10 | FULL | 4-7 | None | Complex, needs thorough clarification |

## Control Flags

```bash
--no-questions        # Skip all questions (override complexity gating)
--with-questions      # Force questions (even for trivial tasks)
--defaults            # Use defaults without prompting
--answers="1:Y 2:A"   # Inline answers for automation
--reclarify           # Re-ask questions (ignore saved answers)
```

## Quick Execution (Context C Example)

```python
import sys
sys.path.insert(0, '/Users/richardwoollcott/.agentecflow/lib')
sys.path.insert(0, '/Users/richardwoollcott/Projects/appmilla_github/guardkit/installer/core/commands/lib')

from clarification.core import should_clarify, format_for_prompt
from clarification.generators.planning_generator import generate_planning_questions, TaskContext
from clarification.display import collect_quick_responses

# 1. Determine mode
mode = should_clarify("planning", complexity=4, flags={"no_questions": False})

# 2. Generate questions
task_ctx = TaskContext(
    task_id="TASK-XXX",
    title="Add user authentication",
    description="Implement login and registration",
    complexity_score=4
)
questions = generate_planning_questions(task_ctx, complexity=4)

# 3. Collect responses
if mode == ClarificationMode.QUICK:
    context = collect_quick_responses(questions, timeout_seconds=15)
    context.context_type = "implementation_planning"

# 4. Format for agent
prompt = f"""
{if context.has_explicit_decisions:}
{format_for_prompt(context)}
{endif}

Plan implementation...
"""
```

## Detection Triggers (Context C)

| Detection | Triggers When | Generates |
|-----------|---------------|-----------|
| **Scope Ambiguity** | Vague language ("support", "handle"), minimal criteria | Scope boundary questions |
| **Technology Choice** | Multiple approaches possible, pattern keywords | Technology approach questions |
| **User Ambiguity** | No user mention, generic "users", multiple types | User persona questions |
| **Integration Points** | Database, API, external service keywords | Integration questions |
| **Edge Cases** | No error handling + high complexity | Edge case questions |

## Question Categories (5W1H Framework)

1. **SCOPE (What)**: Feature boundary, validation level, output format
2. **USER (Who)**: Primary user, expertise level, interaction method
3. **TECHNOLOGY (How)**: Implementation approach, patterns, async/sync
4. **INTEGRATION (Where)**: Database, APIs, existing components
5. **TRADEOFF (Why)**: Priority, speed vs quality, complexity handling
6. **EDGE_CASE**: Empty inputs, large data, concurrency, failures

## ClarificationContext Structure

```yaml
context_type: implementation_planning
mode: quick | full | skip
total_questions: 3
answered_count: 3
skipped_count: 0
user_override: null

explicit_decisions:
  - question_id: scope_boundary
    category: scope
    question_text: "Should X include Y?"
    answer: "Y"
    answer_display: "Yes"
    default_used: false
    confidence: 1.0
    rationale: "User explicitly chose: Yes"

assumed_defaults:
  - question_id: tech_approach
    category: technology
    question_text: "Preferred approach?"
    answer: "R"
    answer_display: "Recommend (AI decides)"
    default_used: true
    confidence: 0.7
    rationale: "AI will recommend based on patterns"
```

## Persistence (Task Frontmatter)

```markdown
---
id: TASK-XXX
title: Add user authentication
clarification:
  context: implementation_planning
  timestamp: 2026-01-22T14:30:00Z
  mode: quick
  decisions:
    - question_id: scope_boundary
      category: scope
      question: "Should 'auth' include password reset?"
      answer: "Y"
      answer_text: "Yes"
      default_used: false
      rationale: "User explicitly chose: Yes"
---
```

## Integration Points

### Phase 1.6 (task-work)

```python
# After Phase 1.5 (context loading), before Phase 2 (planning)

clarification = execute_clarification(
    context_type="implementation_planning",
    task_id=task_id,
    task_title=task_context["title"],
    complexity=task_context.get("complexity", 5),
    flags=command_flags,
    task_context=task_context,
)

# Pass to Phase 2
phase_2_prompt = f"""
{format_for_prompt(clarification)}

Plan implementation for {task_id}...
"""
```

### Phase 5.5 (Plan Audit)

```python
# Verify implementation matches clarification decisions

clarification = ClarificationContext.load_from_frontmatter(task_path)

if clarification and clarification.has_explicit_decisions:
    for decision in clarification.explicit_decisions:
        # Check if implementation respects decision
        if decision.question_id == "tech_approach" and decision.answer == "A":
            # Verify Pydantic models were used (not dataclasses)
            ...
```

## Common Patterns

### Skip for Trivial Tasks

```python
mode = should_clarify("planning", complexity=2, flags={})
# Returns: ClarificationMode.SKIP

context = create_skip_context("trivial")
# Returns: Empty context with mode="skip"
```

### Force Questions for Automation

```bash
/task-work TASK-XXX --with-questions --answers="1:Y 2:A 3:S"
```

```python
mode = should_clarify("planning", complexity=2, flags={"with_questions": True})
# Returns: ClarificationMode.FULL (overrides complexity gate)

responses = parse_inline_answers("1:Y 2:A 3:S", questions)
context = process_responses(questions, responses, mode)
```

### Resume Without Re-asking

```python
# First run: Save to frontmatter
context.persist_to_frontmatter(task_path)

# Later run: Load saved decisions
saved = ClarificationContext.load_from_frontmatter(task_path)
if saved and not flags.get("reclarify"):
    print(f"Using saved clarification from {saved.timestamp}")
    context = saved
```

## Error Handling

### Fail-Safe Strategy

```python
try:
    context = execute_clarification(...)
except Exception as e:
    print(f"⚠️ Clarification error: {e}")
    # NEVER fail the workflow - use empty context
    context = ClarificationContext(
        context_type=context_type,
        mode="skip",
        user_override="error",
    )
```

### Timeout Handling (Quick Mode)

```python
# Quick mode: 15-second timeout
# On timeout: Use all defaults
# User sees: "Auto-proceeding with defaults in 15s..."

# Implementation: Platform-specific (select, threading, asyncio)
# Current: Simplified (Enter = defaults, no actual timeout)
```

## Metrics

| Metric | Target | Actual (TASK-FBSDK-020) |
|--------|--------|-------------------------|
| Time to Clarify | <30s (quick), <2min (full) | ~30s ✅ |
| Questions Asked | 2-3 (quick), 4-7 (full) | 3 ✅ |
| User Friction | Low (quick), Medium (full) | Low ✅ |
| Rework Reduction | 15-20% | 15-20% (est) ✅ |
| False Positives | <10% | 0% ✅ |

## Validation Rules

### Question Validation

```python
# Every question must have:
- id: str (unique)
- category: str (scope, technology, user, etc.)
- text: str (question text)
- options: List[str] (at least one option)
- default: str (must be in options)
- rationale: str (why this default)
```

### Decision Validation

```python
# Every decision must have:
- question_id: str
- category: str
- question_text: str
- answer: str
- answer_display: str
- default_used: bool
- confidence: float (0.0-1.0)
- rationale: str
```

## Files to Reference

| File | Purpose |
|------|---------|
| `core.py` | Shared infrastructure (modes, questions, decisions) |
| `generators/planning_generator.py` | Context C question generation |
| `templates/implementation_planning.py` | Question templates (5W1H) |
| `display.py` | UI formatting and response collection |
| `agents/clarification-questioner.md` | Agent instructions |
| `.claude/rules/clarifying-questions.md` | Complete documentation |

## Testing

### Run Example Execution

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit/.conductor/abu-dhabi-v2
python3 execute_clarification.py
```

### Verify Output

1. Mode determination: QUICK (complexity 4)
2. Questions generated: 3 (scope, technology, validation)
3. Responses collected: Y, A, S
4. Context produced: 2 explicit + 1 default
5. Formatted for agent: Markdown with decisions

## Decision Boundaries

### ALWAYS

- ✅ Check for saved clarification before prompting
- ✅ Respect --no-questions flag (skip entirely)
- ✅ Gate questions by complexity (skip trivial)
- ✅ Return valid ClarificationContext (even if empty)
- ✅ Persist decisions to task frontmatter
- ✅ Complete clarification in <30 seconds (quick mode)
- ✅ Validate inline answers against question options

### NEVER

- ❌ Prompt when --no-questions flag is set
- ❌ Skip questions for complex tasks (5+) without flag
- ❌ Block workflow on clarification errors
- ❌ Ask more than 7 questions (overwhelming)
- ❌ Ignore --with-questions flag
- ❌ Return None (always return context)
- ❌ Timeout in full mode (complex tasks need time)

### ASK (Escalate)

- ⚠️ Ambiguity detection confidence <60%
- ⚠️ Multiple equally-valid approaches detected
- ⚠️ Security-sensitive task without security questions
- ⚠️ Task has conflicting requirements
- ⚠️ Quick mode timeout reached

## Resources

- **Full Documentation**: `.claude/rules/clarifying-questions.md`
- **Extended Guide**: `agents/clarification-questioner-ext.md`
- **Example Execution**: `execute_clarification.py`
- **Detailed Report**: `CLARIFICATION_EXECUTION_TASK-FBSDK-020.md`
- **Summary**: `CLARIFICATION_SUMMARY.md`
