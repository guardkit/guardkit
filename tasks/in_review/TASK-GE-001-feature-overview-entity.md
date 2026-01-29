---
complexity: 5
conductor_workspace: graphiti-enhancements-wave1-1
created_at: 2026-01-29 00:00:00+00:00
dependencies: []
estimated_minutes: 120
feature_id: FEAT-GE
id: TASK-GE-001
implementation_mode: task-work
parent_review: TASK-REV-7549
priority: 1
status: in_review
tags:
- graphiti
- entity
- context-loading
- critical-path
task_type: feature
title: Feature Overview Entity for Graphiti
wave: 1
---

# TASK-GE-001: Feature Overview Entity

## Overview

**Priority**: Critical (Foundation for feature-build context)
**Dependencies**: None (uses existing Graphiti infrastructure)

## Problem Statement

From TASK-REV-7549 analysis: Every context loss scenario involved forgetting what feature-build was supposed to do. Sessions would:
- Start asking for human guidance (violating autonomous principle)
- Forget that worktrees should never auto-merge
- Confuse Player and Coach responsibilities

There is no "big picture" entity that captures what a major feature IS.

## Goals

1. Create a FeatureOverviewEntity dataclass for capturing feature identity
2. Add seeding function to populate feature-build overview
3. Integrate with session context loading to inject overview at session start
4. Add query function to retrieve feature overview

## Technical Approach

### Entity Definition

```python
# guardkit/knowledge/entities/feature_overview.py

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

@dataclass
class FeatureOverviewEntity:
    """Captures the 'big picture' of a major feature."""

    id: str  # FEAT-XXX or feature name
    name: str  # "feature-build"
    tagline: str  # "Autonomous task implementation with Player-Coach validation"

    # Purpose
    purpose: str  # What it exists to do
    what_it_is: List[str]  # Positive definitions
    what_it_is_not: List[str]  # Negative definitions (misconceptions)

    # Constraints
    invariants: List[str]  # Rules that must NEVER be violated

    # Architecture
    architecture_summary: str  # 2-3 sentence architecture
    key_components: List[str]  # Main components involved
    key_decisions: List[str]  # ADR IDs

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_episode_body(self) -> dict:
        """Convert to Graphiti episode body."""
        return {
            "entity_type": "feature_overview",
            "id": self.id,
            "name": self.name,
            "tagline": self.tagline,
            "purpose": self.purpose,
            "what_it_is": self.what_it_is,
            "what_it_is_not": self.what_it_is_not,
            "invariants": self.invariants,
            "architecture_summary": self.architecture_summary,
            "key_components": self.key_components,
            "key_decisions": self.key_decisions,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
```

### Feature-Build Overview Content

```python
FEATURE_BUILD_OVERVIEW = FeatureOverviewEntity(
    id="feature-build",
    name="feature-build",
    tagline="Autonomous task implementation with Player-Coach validation",

    purpose="Execute multi-task features autonomously using the Player-Coach adversarial pattern, preserving worktrees for human review",

    what_it_is=[
        "An autonomous orchestrator that runs tasks without human guidance",
        "A quality enforcement system using Player-Coach validation",
        "A worktree-based isolation system for parallel development"
    ],

    what_it_is_not=[
        "NOT an assistant that asks for guidance mid-feature",
        "NOT a code reviewer (that's the Coach's job)",
        "NOT a human replacement (prepares work for human approval)",
        "NOT an auto-merger (preserves worktrees for human review)"
    ],

    invariants=[
        "Player implements, Coach validates - NEVER reverse roles",
        "Implementation plans are REQUIRED before Player runs",
        "Quality gates are task-type specific (scaffolding != feature)",
        "State recovery takes precedence over fresh starts",
        "Wave N depends on Wave N-1 completion",
        "Worktrees preserved for human review - NEVER auto-merge"
    ],

    architecture_summary="Feature-build orchestrates multiple tasks in waves. Each task uses the Player-Coach pattern: Player implements code, Coach validates against quality gates. Tasks run in isolated worktrees that are preserved for human review.",

    key_components=[
        "FeatureOrchestrator - Wave execution",
        "AutoBuildOrchestrator - Player-Coach loop",
        "CoachValidator - Quality gate checks",
        "TaskWorkInterface - Pre-loop design phase"
    ],

    key_decisions=[
        "ADR-FB-001",  # SDK query() not subprocess
        "ADR-FB-002",  # FEAT-XXX paths not TASK-XXX
        "ADR-FB-003"   # Pre-loop must invoke real task-work
    ]
)
```

### Seeding Function

```python
async def seed_feature_overview(graphiti, overview: FeatureOverviewEntity):
    """Seed a feature overview into Graphiti."""

    await graphiti.add_episode(
        name=f"feature_overview_{overview.id}",
        episode_body=json.dumps(overview.to_episode_body()),
        group_id="feature_overviews"
    )
```

### Context Loading Integration

```python
# In guardkit/knowledge/context_loader.py

async def load_feature_overview(feature_name: str) -> Optional[FeatureOverviewEntity]:
    """Load feature overview for context injection."""

    graphiti = get_graphiti()
    if not graphiti.enabled:
        return None

    results = await graphiti.search(
        query=f"feature_overview {feature_name}",
        group_ids=["feature_overviews"],
        num_results=1
    )

    if results:
        body = results[0].get('body', {})
        return FeatureOverviewEntity(**body)
    return None
```

## Acceptance Criteria

- [ ] FeatureOverviewEntity dataclass created with all fields
- [ ] Feature-build overview content defined and seeded
- [ ] Query function retrieves overview by feature name
- [ ] Session context loading includes overview when available
- [ ] Unit tests for entity serialization/deserialization
- [ ] Integration test confirms overview appears in context

## Files to Create/Modify

### New Files
- `guardkit/knowledge/entities/feature_overview.py`
- `guardkit/knowledge/seed_feature_overviews.py`
- `tests/knowledge/test_feature_overview.py`

### Modified Files
- `guardkit/knowledge/context_loader.py` (add overview loading)
- `guardkit/knowledge/seed_system_context.py` (call seed_feature_overviews)

## Testing Strategy

1. **Unit tests**: Test entity serialization, validation
2. **Integration tests**: Seed and query overview in real Graphiti
3. **E2E test**: Run feature-build, verify overview in session context