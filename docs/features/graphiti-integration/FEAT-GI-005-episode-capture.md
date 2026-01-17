# FEAT-GI-005: Episode Capture (Outcomes)

## Overview

**Feature ID**: FEAT-GI-005
**Title**: Episode Capture (Task Outcomes)
**Priority**: High (Enables learning from experience)
**Estimated Complexity**: Medium
**Dependencies**: FEAT-GI-001 (Core Infrastructure)

## Problem Statement

When tasks are completed, valuable information is generated:
- What implementation approach was used
- What patterns worked well
- What problems were encountered
- How long it took
- What tests were written

This information is currently **lost** - future sessions working on similar tasks have to rediscover everything from scratch.

## Strategic Context

This feature captures **outcomes** as Graphiti episodes, enabling future sessions to learn from past experience. When combined with Session Context Loading (FEAT-GI-003), sessions can see "Task X was similar and succeeded using Y approach."

This is how GuardKit **learns and improves** over time.

## Goals

1. Capture task completion outcomes as Graphiti episodes
2. Record what worked, what didn't, and lessons learned
3. Link outcomes to tasks, patterns, and ADRs
4. Enable "similar task" queries for context loading

## Non-Goals

- Real-time implementation logging (too noisy)
- Automated outcome analysis (just capture, query later)
- Performance metrics collection

## Technical Approach

### Outcome Entity Structure

```python
# guardkit/knowledge/entities/outcome.py

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

class OutcomeType(Enum):
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    REVIEW_PASSED = "review_passed"
    REVIEW_FAILED = "review_failed"
    PATTERN_SUCCESS = "pattern_success"
    PATTERN_FAILURE = "pattern_failure"

@dataclass
class TaskOutcome:
    """Outcome of a completed/failed task."""
    
    # Identity
    id: str  # OUT-XXXXXXXX
    outcome_type: OutcomeType
    
    # What task
    task_id: str
    task_title: str
    task_requirements: str  # For similarity matching
    
    # Result
    success: bool
    summary: str  # Brief description of what happened
    
    # Learnings
    approach_used: Optional[str] = None  # Implementation approach
    patterns_used: List[str] = field(default_factory=list)
    problems_encountered: List[str] = field(default_factory=list)
    lessons_learned: List[str] = field(default_factory=list)
    
    # Quality metrics
    tests_written: int = 0
    test_coverage: Optional[float] = None
    review_cycles: int = 0
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: datetime = field(default_factory=datetime.now)
    duration_minutes: Optional[int] = None
    
    # Relationships
    feature_id: Optional[str] = None
    related_adr_ids: List[str] = field(default_factory=list)
    
    def to_episode_body(self) -> dict:
        """Convert to Graphiti episode body."""
        return {
            "entity_type": "task_outcome",
            "id": self.id,
            "outcome_type": self.outcome_type.value,
            "task_id": self.task_id,
            "task_title": self.task_title,
            "task_requirements": self.task_requirements,
            "success": self.success,
            "summary": self.summary,
            "approach_used": self.approach_used,
            "patterns_used": self.patterns_used,
            "problems_encountered": self.problems_encountered,
            "lessons_learned": self.lessons_learned,
            "tests_written": self.tests_written,
            "test_coverage": self.test_coverage,
            "review_cycles": self.review_cycles,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat(),
            "duration_minutes": self.duration_minutes,
            "feature_id": self.feature_id,
            "related_adr_ids": self.related_adr_ids
        }
```

### Outcome Capture Functions

```python
# guardkit/knowledge/outcome_manager.py

import uuid
from typing import Optional, List

async def capture_task_outcome(
    task_id: str,
    task_title: str,
    task_requirements: str,
    success: bool,
    summary: str,
    approach_used: Optional[str] = None,
    patterns_used: Optional[List[str]] = None,
    problems_encountered: Optional[List[str]] = None,
    lessons_learned: Optional[List[str]] = None,
    tests_written: int = 0,
    test_coverage: Optional[float] = None,
    review_cycles: int = 0,
    started_at: Optional[datetime] = None,
    feature_id: Optional[str] = None
) -> TaskOutcome:
    """Capture outcome of a completed task."""
    
    graphiti = get_graphiti()
    
    outcome = TaskOutcome(
        id=f"OUT-{uuid.uuid4().hex[:8].upper()}",
        outcome_type=OutcomeType.TASK_COMPLETED if success else OutcomeType.TASK_FAILED,
        task_id=task_id,
        task_title=task_title,
        task_requirements=task_requirements,
        success=success,
        summary=summary,
        approach_used=approach_used,
        patterns_used=patterns_used or [],
        problems_encountered=problems_encountered or [],
        lessons_learned=lessons_learned or [],
        tests_written=tests_written,
        test_coverage=test_coverage,
        review_cycles=review_cycles,
        started_at=started_at,
        feature_id=feature_id,
        duration_minutes=calculate_duration(started_at) if started_at else None
    )
    
    if graphiti.enabled:
        await graphiti.add_episode(
            name=f"outcome_{outcome.id}",
            episode_body=json.dumps(outcome.to_episode_body()),
            group_id="task_outcomes"
        )
    
    return outcome


async def capture_pattern_outcome(
    pattern_name: str,
    task_id: str,
    success: bool,
    notes: str
):
    """Capture whether a pattern worked in a specific context."""
    
    graphiti = get_graphiti()
    
    outcome = {
        "entity_type": "pattern_outcome",
        "id": f"POUT-{uuid.uuid4().hex[:8].upper()}",
        "pattern_name": pattern_name,
        "task_id": task_id,
        "success": success,
        "notes": notes,
        "captured_at": datetime.now().isoformat()
    }
    
    if graphiti.enabled:
        await graphiti.add_episode(
            name=f"pattern_outcome_{outcome['id']}",
            episode_body=json.dumps(outcome),
            group_id="pattern_outcomes"
        )
```

### Outcome Extraction from Task Completion

```python
# guardkit/knowledge/outcome_extractor.py

async def extract_outcome_from_task_complete(
    task_id: str,
    completion_data: dict
) -> TaskOutcome:
    """Extract outcome information from task-complete data."""
    
    # Get task details
    task = await get_task_by_id(task_id)
    
    # Extract patterns used from implementation
    patterns_used = detect_patterns_in_implementation(
        completion_data.get('files_changed', [])
    )
    
    # Extract problems from test/review cycles
    problems = extract_problems_from_history(
        completion_data.get('review_history', [])
    )
    
    # Generate lessons learned
    lessons = generate_lessons(
        task=task,
        patterns_used=patterns_used,
        problems=problems,
        success=completion_data.get('success', True)
    )
    
    return await capture_task_outcome(
        task_id=task_id,
        task_title=task.title,
        task_requirements=task.requirements,
        success=completion_data.get('success', True),
        summary=completion_data.get('summary', ''),
        approach_used=completion_data.get('approach'),
        patterns_used=patterns_used,
        problems_encountered=problems,
        lessons_learned=lessons,
        tests_written=count_tests(completion_data.get('files_changed', [])),
        test_coverage=completion_data.get('coverage'),
        review_cycles=len(completion_data.get('review_history', [])),
        started_at=completion_data.get('started_at'),
        feature_id=completion_data.get('feature_id')
    )


def detect_patterns_in_implementation(files_changed: List[str]) -> List[str]:
    """Detect what patterns were used based on files changed."""
    
    patterns = []
    
    for file in files_changed:
        if 'crud' in file.lower():
            patterns.append('CRUD Base Classes')
        if 'repository' in file.lower():
            patterns.append('Repository Pattern')
        if 'dependencies' in file.lower() or 'Depends(' in file:
            patterns.append('Dependency Injection')
        if 'test_' in file or '_test' in file:
            patterns.append('Test-Driven Development')
    
    return list(set(patterns))


def generate_lessons(
    task,
    patterns_used: List[str],
    problems: List[str],
    success: bool
) -> List[str]:
    """Generate lessons learned from task completion."""
    
    lessons = []
    
    if success and patterns_used:
        lessons.append(f"Patterns {', '.join(patterns_used)} worked well for this type of task")
    
    if problems:
        lessons.append(f"Watch out for: {'; '.join(problems[:3])}")
    
    if not success:
        lessons.append("Task failed - review problems for future attempts")
    
    return lessons
```

### Integration with task-complete

```python
# In guardkit/commands/task_complete.py

async def complete_task(task_id: str, completion_data: dict):
    """Complete a task and capture outcome."""
    
    # Existing task completion logic...
    result = await finalize_task(task_id, completion_data)
    
    # NEW: Capture outcome
    await extract_outcome_from_task_complete(task_id, {
        **completion_data,
        'success': result.success,
        'summary': result.summary,
        'review_history': result.review_history,
        'files_changed': result.files_changed
    })
    
    return result
```

### Querying Outcomes for Context

```python
# guardkit/knowledge/outcome_queries.py

async def find_similar_task_outcomes(
    task_requirements: str,
    limit: int = 5
) -> List[TaskOutcome]:
    """Find outcomes of similar tasks."""
    
    graphiti = get_graphiti()
    
    if not graphiti.enabled:
        return []
    
    results = await graphiti.search(
        query=task_requirements,
        group_ids=["task_outcomes"],
        num_results=limit
    )
    
    return [TaskOutcome(**r['body']) for r in results]


async def find_pattern_success_rate(pattern_name: str) -> dict:
    """Find success rate of a pattern."""
    
    graphiti = get_graphiti()
    
    results = await graphiti.search(
        query=f"pattern {pattern_name}",
        group_ids=["pattern_outcomes"],
        num_results=50
    )
    
    successes = sum(1 for r in results if r['body'].get('success'))
    total = len(results)
    
    return {
        "pattern": pattern_name,
        "total_uses": total,
        "successes": successes,
        "success_rate": successes / total if total > 0 else 0
    }
```

## Acceptance Criteria

1. **Outcomes are captured**
   - Task completion creates outcome episode
   - Outcome includes task details, approach, patterns
   - Problems and lessons are recorded

2. **Outcomes are queryable**
   - Can find outcomes for similar tasks
   - Can see what patterns were used
   - Can see what problems were encountered

3. **Outcomes appear in context**
   - Session Context Loading (FEAT-GI-003) shows similar outcomes
   - Future sessions benefit from past learnings

4. **Pattern outcomes tracked**
   - Success/failure of patterns is recorded
   - Can query pattern success rates

## Testing Strategy

1. **Unit tests**: Test outcome entity, extraction logic
2. **Integration tests**: Test capture and query in Graphiti
3. **E2E tests**: Complete task, verify outcome appears in future context

## Files to Create/Modify

### New Files
- `guardkit/knowledge/entities/outcome.py`
- `guardkit/knowledge/outcome_manager.py`
- `guardkit/knowledge/outcome_extractor.py`
- `guardkit/knowledge/outcome_queries.py`
- `tests/knowledge/test_outcome_manager.py`

### Modified Files
- `guardkit/commands/task_complete.py` (add outcome capture)

## Example Outcomes

**Successful task:**
```json
{
  "id": "OUT-A1B2C3D4",
  "outcome_type": "task_completed",
  "task_id": "TASK-AUTH-042",
  "task_title": "Implement OAuth2 login endpoint",
  "task_requirements": "Add OAuth2 authentication with Google provider...",
  "success": true,
  "summary": "Successfully implemented OAuth2 with FastAPI dependencies",
  "approach_used": "Used FastAPI OAuth2PasswordBearer with custom token validation",
  "patterns_used": ["Dependency Injection", "Repository Pattern"],
  "problems_encountered": ["Initial token refresh logic was incorrect"],
  "lessons_learned": [
    "Patterns Dependency Injection, Repository Pattern worked well",
    "Watch out for: token refresh timing"
  ],
  "tests_written": 8,
  "test_coverage": 85.5,
  "review_cycles": 2,
  "duration_minutes": 120
}
```

**Failed task:**
```json
{
  "id": "OUT-E5F6G7H8",
  "outcome_type": "task_failed",
  "task_id": "TASK-DB-099",
  "task_title": "Add database connection pooling",
  "success": false,
  "summary": "Failed due to incompatible asyncpg version",
  "problems_encountered": [
    "asyncpg 0.28 incompatible with SQLAlchemy 2.0 async",
    "Connection pool exhaustion under load"
  ],
  "lessons_learned": [
    "Task failed - verify library version compatibility before starting"
  ],
  "review_cycles": 3
}
```

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Outcomes too verbose | Keep summary concise, details in lists |
| Pattern detection inaccurate | Start simple, improve over time |
| Lessons too generic | Tie lessons to specific context |

## Open Questions

1. Should we capture intermediate states (not just completion)?
2. How detailed should pattern detection be?
3. Should lessons be human-reviewed before storage?

---

## Related Documents

- [FEAT-GI-001: Core Infrastructure](./FEAT-GI-001-core-infrastructure.md)
- [FEAT-GI-003: Session Context Loading](./FEAT-GI-003-session-context-loading.md)
- [Unified Data Architecture Decision](../../research/knowledge-graph-mcp/unified-data-architecture-decision.md)
