---
complexity: 5
conductor_workspace: graphiti-enhancements-wave2-2
created_at: 2026-01-29 00:00:00+00:00
dependencies: []
estimated_minutes: 120
feature_id: FEAT-GE
id: TASK-GE-004
implementation_mode: task-work
parent_review: TASK-REV-7549
priority: 2
status: design_approved
tags:
- graphiti
- episodes
- learning
- failure-prevention
task_type: feature
title: Failed Approach Episodes with Prevention Guidance
wave: 2
---

# TASK-GE-004: Failed Approach Episodes with Prevention Guidance

## Overview

**Priority**: High (Prevents repeated mistakes)
**Dependencies**: None (uses existing Graphiti infrastructure)

## Problem Statement

From TASK-REV-7549 analysis: Problems repeated because failures weren't captured for future reference:
- Session 1 tries subprocess, fails
- Session 2 tries subprocess again, fails again
- Session 3 finally discovers SDK query() works
- Session 4 tries subprocess again...

The existing `failure_patterns` group captures symptoms and fixes, but lacks:
- Prevention guidance (how to avoid making this mistake)
- Link to related ADRs
- Occurrence tracking (how often this happens)
- Context where the failure was encountered

## Goals

1. Create FailedApproachEpisode with prevention guidance
2. Enhance capture to include context and prevention
3. Add query function to surface relevant failures for current context
4. Track occurrence count for prioritization

## Technical Approach

### Episode Definition

```python
# guardkit/knowledge/entities/failed_approach.py

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

@dataclass
class FailedApproachEpisode:
    """Captures an approach that was tried and failed."""

    # Identity
    id: str  # FAIL-{hash}

    # What went wrong
    approach: str  # What was tried
    symptom: str  # What went wrong (error message or behavior)
    root_cause: str  # Why it failed

    # Resolution
    fix_applied: str  # How it was resolved
    prevention: str  # How to avoid in future (key for learning)

    # Context
    context: str  # Where this happened (feature-build, task-work, etc.)
    task_id: Optional[str] = None  # Task where this occurred
    feature_id: Optional[str] = None  # Feature where this occurred
    file_path: Optional[str] = None  # File involved if relevant

    # Related knowledge
    related_adrs: List[str] = field(default_factory=list)  # ADR IDs to check
    similar_failures: List[str] = field(default_factory=list)  # Related FAIL-XXX

    # Tracking
    occurrences: int = 1  # How many times this happened
    first_occurred: datetime = field(default_factory=datetime.now)
    last_occurred: datetime = field(default_factory=datetime.now)

    # Severity
    severity: str = "medium"  # "low" | "medium" | "high" | "critical"
    time_to_fix_minutes: Optional[int] = None

    def to_episode_body(self) -> dict:
        """Convert to Graphiti episode body."""
        return {
            "entity_type": "failed_approach",
            "id": self.id,
            "approach": self.approach,
            "symptom": self.symptom,
            "root_cause": self.root_cause,
            "fix_applied": self.fix_applied,
            "prevention": self.prevention,
            "context": self.context,
            "task_id": self.task_id,
            "feature_id": self.feature_id,
            "file_path": self.file_path,
            "related_adrs": self.related_adrs,
            "similar_failures": self.similar_failures,
            "occurrences": self.occurrences,
            "first_occurred": self.first_occurred.isoformat(),
            "last_occurred": self.last_occurred.isoformat(),
            "severity": self.severity,
            "time_to_fix_minutes": self.time_to_fix_minutes
        }
```

### Initial Failed Approaches to Seed

```python
INITIAL_FAILED_APPROACHES = [
    FailedApproachEpisode(
        id="FAIL-SUBPROCESS",
        approach="Using subprocess.run() to invoke guardkit task-work",
        symptom="subprocess.CalledProcessError: Command 'guardkit task-work' not found",
        root_cause="CLI command doesn't exist - task-work is a Claude Code slash command",
        fix_applied="Use SDK query() to invoke '/task-work TASK-XXX' as a subagent",
        prevention="BEFORE implementing task-work invocation, check ADR-FB-001. "
                   "If symptom contains 'subprocess' or 'Command not found', use SDK query() instead.",
        context="feature-build",
        related_adrs=["ADR-FB-001"],
        severity="critical",
        occurrences=3
    ),

    FailedApproachEpisode(
        id="FAIL-TASK-PATH",
        approach="Using TASK-XXX ID for worktree path construction",
        symptom="FileNotFoundError at .guardkit/worktrees/TASK-XXX/...",
        root_cause="In feature mode, worktree is shared and named after feature (FEAT-XXX), not individual tasks",
        fix_applied="Use feature_worktree_id for path construction",
        prevention="BEFORE constructing worktree paths, check ADR-FB-002. "
                   "In feature mode, always use FEAT-XXX, never TASK-XXX.",
        context="feature-build",
        related_adrs=["ADR-FB-002"],
        severity="high",
        occurrences=2
    ),

    FailedApproachEpisode(
        id="FAIL-MOCK-PRELOOP",
        approach="TaskWorkInterface.execute_design_phase() returning mock data",
        symptom="Pre-loop returns suspiciously round values (complexity=5, arch_score=80)",
        root_cause="Stub implementation returning placeholder data instead of invoking real task-work",
        fix_applied="Implement execute_design_phase() with SDK query() to '/task-work --design-only'",
        prevention="BEFORE trusting pre-loop results, verify they come from real task-work invocation. "
                   "Check ADR-FB-003. Suspiciously round numbers indicate mock data.",
        context="feature-build",
        related_adrs=["ADR-FB-003"],
        severity="critical",
        occurrences=2
    ),

    FailedApproachEpisode(
        id="FAIL-SCHEMA-MISMATCH",
        approach="Writing results to 'quality_gates' but reading from 'test_results'",
        symptom="Coach can't find test results, defaults to score=0",
        root_cause="Schema mismatch between task-work writer and CoachValidator reader",
        fix_applied="Aligned schema to use 'quality_gates' consistently",
        prevention="BEFORE reading/writing shared JSON files, verify schema alignment between writer and reader. "
                   "Check for existing field names in both components.",
        context="feature-build",
        severity="high",
        occurrences=4
    ),

    FailedApproachEpisode(
        id="FAIL-ALL-TESTS",
        approach="Running 'pytest tests/' to verify task-specific changes",
        symptom="Unrelated test failures from other tasks in shared worktree",
        root_cause="In feature mode, tests/ contains tests from ALL tasks, not just current task",
        fix_applied="Implemented task-specific test filtering",
        prevention="BEFORE running tests in feature mode, filter to task-specific tests only. "
                   "Or use --ignore patterns to exclude other task tests.",
        context="feature-build",
        severity="medium",
        occurrences=4
    )
]
```

### Capture Function

```python
async def capture_failed_approach(
    approach: str,
    symptom: str,
    root_cause: str,
    fix_applied: str,
    prevention: str,
    context: str,
    **kwargs
) -> FailedApproachEpisode:
    """Capture a failed approach for future prevention."""

    import hashlib
    approach_hash = hashlib.sha256(approach.encode()).hexdigest()[:8]

    graphiti = get_graphiti()

    failure = FailedApproachEpisode(
        id=f"FAIL-{approach_hash.upper()}",
        approach=approach,
        symptom=symptom,
        root_cause=root_cause,
        fix_applied=fix_applied,
        prevention=prevention,
        context=context,
        **kwargs
    )

    if graphiti.enabled:
        await graphiti.add_episode(
            name=f"failed_approach_{failure.id}",
            episode_body=json.dumps(failure.to_episode_body()),
            group_id="failed_approaches"
        )

    return failure
```

### Context Loading for Prevention

```python
async def load_relevant_failures(query_context: str, limit: int = 5) -> List[dict]:
    """Load failed approaches relevant to current context."""

    graphiti = get_graphiti()
    if not graphiti.enabled:
        return []

    results = await graphiti.search(
        query=f"failed approach {query_context}",
        group_ids=["failed_approaches"],
        num_results=limit
    )

    # Format as warnings
    warnings = []
    for result in results:
        body = result.get('body', {})
        warnings.append({
            "symptom": body.get('symptom', ''),
            "prevention": body.get('prevention', ''),
            "related_adrs": body.get('related_adrs', [])
        })

    return warnings
```

## Acceptance Criteria

- [ ] FailedApproachEpisode dataclass created with all fields
- [ ] Initial 5 failed approaches seeded from review findings
- [ ] Capture function works with Graphiti
- [ ] Query function retrieves relevant failures for context
- [ ] Prevention guidance appears in session context
- [ ] Unit tests for entity and capture functions
- [ ] Integration test confirms failures queryable

## Files to Create/Modify

### New Files
- `guardkit/knowledge/entities/failed_approach.py`
- `guardkit/knowledge/failed_approach_manager.py`
- `guardkit/knowledge/seed_failed_approaches.py`
- `tests/knowledge/test_failed_approaches.py`

### Modified Files
- `guardkit/knowledge/context_loader.py` (add failure loading)
- `guardkit/knowledge/seed_system_context.py` (call seed_failed_approaches)

## Testing Strategy

1. **Unit tests**: Test entity, capture, and query functions
2. **Integration tests**: Seed failures, verify prevention appears in context
3. **Manual test**: Trigger known failure scenario, verify warning appears