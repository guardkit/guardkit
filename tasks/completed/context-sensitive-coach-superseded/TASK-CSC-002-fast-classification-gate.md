---
id: TASK-CSC-002
title: Implement fast classification gate
status: backlog
created: 2026-01-23T11:30:00Z
priority: high
tags: [context-sensitive-coach, classification, performance, quality-gates]
task_type: feature
complexity: 3
parent_review: TASK-REV-CSC1
feature_id: FEAT-CSC
wave: 1
implementation_mode: task-work
conductor_workspace: csc-wave1-classifier
dependencies: []
---

# Task: Implement Fast Classification Gate

## Description

Implement the fast classification gate that determines if AI analysis is needed. This gate allows trivial and obviously complex cases to bypass AI analysis entirely, improving performance.

## Acceptance Criteria

- [ ] `FastClassifier` class with `classify()` method
- [ ] `_is_obviously_trivial()` returns True for <30 LOC, 1-2 files
- [ ] `_is_obviously_complex()` returns True for >300 LOC, >10 files
- [ ] Returns classification result with confidence and rationale
- [ ] Logging for classification decisions
- [ ] Unit tests with >80% coverage

## Implementation Notes

### Location

Create in: `guardkit/orchestrator/quality_gates/context_analysis/classifier.py`

### Classification Categories

```python
class ScopeCategory(Enum):
    TRIVIAL = "trivial"      # Skip AI, use minimal profile
    SIMPLE = "simple"        # May skip AI with light profile
    UNCERTAIN = "uncertain"  # Requires AI analysis
    COMPLEX = "complex"      # Skip AI, use strict profile
    CRITICAL = "critical"    # Skip AI, use maximum profile
```

### FastClassifier Interface

```python
@dataclass
class ClassificationResult:
    category: ScopeCategory
    confidence: float  # 0.0-1.0
    rationale: str
    needs_ai_analysis: bool
    recommended_profile: str

class FastClassifier:
    def classify(self, context: UniversalContext) -> ClassificationResult:
        """Classify implementation scope without AI."""
        ...
```

### Thresholds

| Metric | Trivial | Simple | Uncertain | Complex |
|--------|---------|--------|-----------|---------|
| Lines Added | <30 | 30-100 | 100-300 | >300 |
| Files | 1-2 | 3-5 | 5-10 | >10 |
| Test Files | Any | Any | Any | Any |
| Deps Changed | No | No | Maybe | Yes |

### Risk Tags for Critical

```python
CRITICAL_TAGS = ["security", "authentication", "payment", "database", "migration"]
```

## Testing Strategy

- Test each category with boundary values
- Test risk tag detection
- Test confidence calculation
- Test rationale generation
