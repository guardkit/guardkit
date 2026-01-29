---
id: TASK-GE-002
title: Turn State Episodes for Cross-Turn Learning
status: backlog
priority: 1
task_type: feature
created_at: 2026-01-29T00:00:00Z
parent_review: TASK-REV-7549
feature_id: FEAT-GE
implementation_mode: task-work
wave: 2
conductor_workspace: graphiti-enhancements-wave2-1
complexity: 6
estimated_minutes: 180
dependencies:
  - TASK-GE-001
tags:
  - graphiti
  - episodes
  - learning
  - feature-build
---

# TASK-GE-002: Turn State Episodes for Cross-Turn Learning

## Overview

**Priority**: Critical (Enables learning across turns)
**Dependencies**: TASK-GE-001 (Feature Overview Entity)

## Problem Statement

From TASK-REV-7549 analysis: "Cross-Turn Learning Failure" was identified as a systemic issue:
- Each turn starts from zero knowledge about previous turns
- Turn 5 makes the same mistakes as Turn 1
- No progress trajectory - just random walk through solution space
- Cumulative acceptance criteria status not tracked

Sessions don't know what previous turns learned or why they failed.

## Goals

1. Create TurnStateEntity to capture state at end of each feature-build turn
2. Capture Player decision, Coach decision, blockers, and cumulative progress
3. Add context loading for turn continuation (Turn N loads Turn N-1 summary)
4. Enable queries like "What did we try last turn and why did it fail?"

## Technical Approach

### Entity Definition

```python
# guardkit/knowledge/entities/turn_state.py

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum

class TurnMode(Enum):
    FRESH_START = "fresh_start"
    RECOVERING_STATE = "recovering_state"
    CONTINUING_WORK = "continuing_work"

@dataclass
class TurnStateEntity:
    """Captures state at the end of each feature-build turn."""

    # Identity
    id: str  # TURN-{feature_id}-{turn_number}
    feature_id: str
    task_id: str
    turn_number: int

    # What happened
    player_summary: str  # What Player implemented/attempted
    player_decision: str  # "implemented" | "failed" | "blocked"
    coach_decision: str  # "approved" | "feedback" | "rejected"
    coach_feedback: Optional[str]  # Specific feedback if not approved

    # Progress tracking
    mode: TurnMode  # State machine mode
    blockers_found: List[str] = field(default_factory=list)
    progress_summary: str = ""  # Brief description of progress made

    # Acceptance criteria tracking
    acceptance_criteria_status: Dict[str, str] = field(default_factory=dict)
    # Format: {"criterion_1": "verified", "criterion_2": "rejected", "criterion_3": "pending"}

    # Quality metrics
    tests_passed: Optional[int] = None
    tests_failed: Optional[int] = None
    coverage: Optional[float] = None
    arch_score: Optional[int] = None

    # Timing
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime = field(default_factory=datetime.now)
    duration_seconds: Optional[int] = None

    # Learning
    lessons_from_turn: List[str] = field(default_factory=list)
    what_to_try_next: Optional[str] = None

    def to_episode_body(self) -> dict:
        """Convert to Graphiti episode body."""
        return {
            "entity_type": "turn_state",
            "id": self.id,
            "feature_id": self.feature_id,
            "task_id": self.task_id,
            "turn_number": self.turn_number,
            "player_summary": self.player_summary,
            "player_decision": self.player_decision,
            "coach_decision": self.coach_decision,
            "coach_feedback": self.coach_feedback,
            "mode": self.mode.value,
            "blockers_found": self.blockers_found,
            "progress_summary": self.progress_summary,
            "acceptance_criteria_status": self.acceptance_criteria_status,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "coverage": self.coverage,
            "arch_score": self.arch_score,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "lessons_from_turn": self.lessons_from_turn,
            "what_to_try_next": self.what_to_try_next
        }
```

### Capture Function

```python
# guardkit/knowledge/turn_state_manager.py

async def capture_turn_state(
    feature_id: str,
    task_id: str,
    turn_number: int,
    player_summary: str,
    player_decision: str,
    coach_decision: str,
    coach_feedback: Optional[str] = None,
    mode: TurnMode = TurnMode.CONTINUING_WORK,
    **kwargs
) -> TurnStateEntity:
    """Capture turn state at end of feature-build turn."""

    graphiti = get_graphiti()

    turn_state = TurnStateEntity(
        id=f"TURN-{feature_id}-{turn_number}",
        feature_id=feature_id,
        task_id=task_id,
        turn_number=turn_number,
        player_summary=player_summary,
        player_decision=player_decision,
        coach_decision=coach_decision,
        coach_feedback=coach_feedback,
        mode=mode,
        **kwargs
    )

    if graphiti.enabled:
        await graphiti.add_episode(
            name=f"turn_state_{turn_state.id}",
            episode_body=json.dumps(turn_state.to_episode_body()),
            group_id="turn_states"
        )

    return turn_state
```

### Context Loading for Turn Continuation

```python
# guardkit/knowledge/context_loader.py

async def load_turn_continuation_context(
    feature_id: str,
    current_turn: int
) -> Optional[str]:
    """Load context for Turn N when N > 1."""

    if current_turn <= 1:
        return None  # No previous turn to learn from

    graphiti = get_graphiti()
    if not graphiti.enabled:
        return None

    # Load previous turn state
    prev_turn = await graphiti.search(
        query=f"turn_state {feature_id} turn {current_turn - 1}",
        group_ids=["turn_states"],
        num_results=1
    )

    if not prev_turn:
        return None

    body = prev_turn[0].get('body', {})

    # Format as actionable context
    context_lines = [
        f"## Previous Turn Summary (Turn {current_turn - 1})",
        f"**What was attempted**: {body.get('player_summary', 'Unknown')}",
        f"**Coach decision**: {body.get('coach_decision', 'Unknown')}",
    ]

    if body.get('coach_feedback'):
        context_lines.append(f"**Feedback**: {body['coach_feedback']}")

    if body.get('blockers_found'):
        context_lines.append(f"**Blockers found**: {', '.join(body['blockers_found'])}")

    if body.get('lessons_from_turn'):
        context_lines.append(f"**Lessons learned**: {'; '.join(body['lessons_from_turn'])}")

    if body.get('what_to_try_next'):
        context_lines.append(f"**Suggested focus for this turn**: {body['what_to_try_next']}")

    # Acceptance criteria status
    ac_status = body.get('acceptance_criteria_status', {})
    if ac_status:
        context_lines.append("\n**Acceptance Criteria Status**:")
        for criterion, status in ac_status.items():
            icon = "✓" if status == "verified" else "✗" if status == "rejected" else "○"
            context_lines.append(f"  {icon} {criterion}: {status}")

    return "\n".join(context_lines)
```

### Integration with AutoBuild Orchestrator

```python
# In guardkit/orchestrator/autobuild.py

async def _post_turn_capture(self, turn_result: TurnResult):
    """Capture turn state after each turn completes."""

    await capture_turn_state(
        feature_id=self.feature_id,
        task_id=self.task_id,
        turn_number=self.current_turn,
        player_summary=turn_result.player_summary,
        player_decision=turn_result.player_decision,
        coach_decision=turn_result.coach_decision,
        coach_feedback=turn_result.coach_feedback,
        mode=self._determine_mode(),
        blockers_found=turn_result.blockers,
        progress_summary=turn_result.progress_summary,
        acceptance_criteria_status=self._get_ac_status(),
        tests_passed=turn_result.tests_passed,
        tests_failed=turn_result.tests_failed,
        coverage=turn_result.coverage,
        arch_score=turn_result.arch_score,
        lessons_from_turn=turn_result.lessons,
        what_to_try_next=self._suggest_next_focus(turn_result)
    )
```

## Acceptance Criteria

- [ ] TurnStateEntity dataclass created with all fields
- [ ] capture_turn_state function works with Graphiti
- [ ] Turn continuation context loads previous turn summary
- [ ] AutoBuild orchestrator captures turn state after each turn
- [ ] Acceptance criteria status tracked across turns
- [ ] Unit tests for entity and capture functions
- [ ] Integration test confirms cross-turn context available

## Files to Create/Modify

### New Files
- `guardkit/knowledge/entities/turn_state.py`
- `guardkit/knowledge/turn_state_manager.py`
- `tests/knowledge/test_turn_state.py`

### Modified Files
- `guardkit/knowledge/context_loader.py` (add turn continuation)
- `guardkit/orchestrator/autobuild.py` (add post-turn capture)

## Testing Strategy

1. **Unit tests**: Test entity, capture, and query functions
2. **Integration tests**: Capture multiple turns, verify cumulative learning
3. **E2E test**: Run multi-turn feature-build, verify Turn N sees Turn N-1 context
