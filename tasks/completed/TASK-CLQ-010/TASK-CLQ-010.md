---
id: TASK-CLQ-010
title: Implement persistence & audit trail
status: completed
created: 2025-12-08T14:00:00Z
updated: 2025-12-10T00:00:00Z
completed: 2025-12-10T00:00:00Z
priority: medium
tags: [clarifying-questions, persistence, audit, wave-4]
complexity: 3
parent_feature: clarifying-questions
wave: 4
conductor_workspace: clarifying-questions-wave4-persistence
implementation_method: direct
completed_location: tasks/completed/TASK-CLQ-010/
organized_files:
  - TASK-CLQ-010.md
---

# Task: Implement persistence & audit trail

## Description

Implement persistence of clarification decisions to task frontmatter and create audit trail for tracking what questions were asked, what answers were given, and when. This enables reproducibility and debugging of AI planning decisions.

## Acceptance Criteria

- [x] Define YAML schema for clarification decisions in frontmatter
- [x] Implement `persist_to_frontmatter()` function in core.py
- [x] Store timestamp, question ID, answer, and rationale
- [x] Support loading previous decisions for task resumption
- [x] Add `load_from_frontmatter()` function for resuming interrupted tasks
- [x] Document schema in CLAUDE.md

## Technical Specification

### YAML Schema

```yaml
# Task frontmatter with clarification decisions
---
id: TASK-a3f8
title: Add user authentication
status: in_progress
complexity: 6
# ... other fields ...

clarification:
  context: implementation_planning  # or review_scope, implementation_prefs
  timestamp: 2025-12-08T14:30:00Z
  mode: full  # skip, quick, or full
  decisions:
    - question_id: scope
      category: scope
      question: "How comprehensive should this implementation be?"
      answer: standard
      answer_text: "Standard - With error handling"
      default_used: true
      rationale: "Matches typical implementation needs"

    - question_id: testing
      category: testing
      question: "What testing strategy?"
      answer: integration
      answer_text: "Integration tests included"
      default_used: false
      rationale: "User explicitly chose integration testing"

    - question_id: auth_method
      category: technology
      question: "Which authentication method?"
      answer: jwt
      answer_text: "JWT with refresh tokens"
      default_used: false
      rationale: "User selected based on review recommendations"
---
```

### Core Functions

```python
# In core.py - add to existing ClarificationContext

from datetime import datetime
from typing import Optional
import yaml

@dataclass
class ClarificationContext:
    context_type: str  # implementation_planning, review_scope, implementation_prefs
    decisions: List[Decision]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    mode: str = "full"  # skip, quick, full

    def persist_to_frontmatter(self, task_path: Path) -> None:
        """Persist clarification decisions to task frontmatter."""
        # Read existing frontmatter
        content = task_path.read_text()
        frontmatter, body = parse_frontmatter(content)

        # Add clarification section
        frontmatter['clarification'] = {
            'context': self.context_type,
            'timestamp': self.timestamp.isoformat(),
            'mode': self.mode,
            'decisions': [
                {
                    'question_id': d.question_id,
                    'category': d.category,
                    'question': d.question_text,
                    'answer': d.answer,
                    'answer_text': d.answer_display,
                    'default_used': d.default_used,
                    'rationale': d.rationale,
                }
                for d in self.decisions
            ]
        }

        # Write back
        new_content = serialize_frontmatter(frontmatter) + body
        task_path.write_text(new_content)

    @classmethod
    def load_from_frontmatter(cls, task_path: Path) -> Optional['ClarificationContext']:
        """Load previous clarification decisions from task frontmatter."""
        content = task_path.read_text()
        frontmatter, _ = parse_frontmatter(content)

        if 'clarification' not in frontmatter:
            return None

        clr = frontmatter['clarification']
        return cls(
            context_type=clr['context'],
            timestamp=datetime.fromisoformat(clr['timestamp']),
            mode=clr['mode'],
            decisions=[
                Decision(
                    question_id=d['question_id'],
                    category=d['category'],
                    question_text=d['question'],
                    answer=d['answer'],
                    answer_display=d['answer_text'],
                    default_used=d['default_used'],
                    rationale=d['rationale'],
                )
                for d in clr['decisions']
            ]
        )


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith('---'):
        return {}, content

    parts = content.split('---', 2)
    if len(parts) < 3:
        return {}, content

    frontmatter = yaml.safe_load(parts[1])
    body = parts[2]
    return frontmatter, body


def serialize_frontmatter(frontmatter: dict) -> str:
    """Serialize frontmatter dict to YAML string."""
    return '---\n' + yaml.dump(frontmatter, default_flow_style=False, sort_keys=False) + '---\n'
```

### Usage in Task Workflow

```python
# In task-work execution

def execute_task_work(task_id: str, flags: dict):
    task_path = get_task_path(task_id)

    # Check for existing clarification (task resumption)
    existing_clarification = ClarificationContext.load_from_frontmatter(task_path)

    if existing_clarification and not flags.get('reclarify'):
        # Use existing decisions
        print(f"Using previous clarification from {existing_clarification.timestamp}")
        clarification = existing_clarification
    else:
        # Run clarification flow
        clarification = run_clarification_phase(task, context, flags)

        # Persist decisions
        if clarification:
            clarification.persist_to_frontmatter(task_path)

    # Continue with planning using clarification context
    plan = create_implementation_plan(task, context, clarification)
```

### Audit Trail Query

```python
# Utility for querying clarification history

def get_clarification_summary(task_path: Path) -> str:
    """Generate human-readable summary of clarification decisions."""
    ctx = ClarificationContext.load_from_frontmatter(task_path)
    if not ctx:
        return "No clarification recorded"

    lines = [
        f"Clarification: {ctx.context_type}",
        f"Mode: {ctx.mode}",
        f"Timestamp: {ctx.timestamp}",
        f"Decisions ({len(ctx.decisions)}):",
    ]

    for d in ctx.decisions:
        default_marker = " (default)" if d.default_used else ""
        lines.append(f"  - {d.question_id}: {d.answer_display}{default_marker}")

    return "\n".join(lines)
```

## Files to Modify

1. `installer/global/commands/lib/clarification/core.py` - Add persistence functions
2. `installer/global/commands/lib/task_work_executor.py` - Integrate persistence calls

## Files to Create

None - all changes go into existing files

## Why Direct Implementation

- Straightforward YAML serialization
- Clear spec from review report
- Single file modifications
- Lower complexity (3/10)

## Dependencies

- Wave 1: core.py (ClarificationContext, Decision dataclasses must exist)

## Related Tasks

- TASK-CLQ-011 (documentation - parallel)
- TASK-CLQ-012 (testing - parallel)

## Reference

See [Review Report Section: Persistence & Audit Trail](./../../../.claude/reviews/TASK-REV-B130-review-report.md#persistence--audit-trail).
