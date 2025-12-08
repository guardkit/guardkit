---
id: TASK-CLQ-002
title: Create ambiguity detection algorithms
status: backlog
created: 2025-12-08T14:00:00Z
updated: 2025-12-08T14:00:00Z
priority: high
tags: [clarifying-questions, detection, algorithms, wave-1]
complexity: 7
parent_feature: clarifying-questions
wave: 1
conductor_workspace: clarifying-questions-wave1-detection
implementation_method: task-work
---

# Task: Create ambiguity detection algorithms

## Description

Create the detection module that analyzes task context to identify areas of ambiguity that require clarification. This is the "intelligence" behind question generation - it detects what needs clarification based on task description, codebase context, and complexity.

## Acceptance Criteria

- [ ] Create `installer/global/commands/lib/clarification/detection.py` with:
  - [ ] `detect_scope_ambiguity()` - Find unclear feature boundaries
  - [ ] `detect_technology_choices()` - Find technology decisions needed
  - [ ] `detect_integration_points()` - Find external system connections
  - [ ] `detect_user_ambiguity()` - Find unclear user/persona targets
  - [ ] `detect_tradeoff_needs()` - Find priority decisions needed
  - [ ] `detect_unhandled_edge_cases()` - Find obvious gaps
- [ ] Each function returns structured detection results
- [ ] Include heuristics for common patterns (auth → password reset, list → pagination)
- [ ] Support both task-only analysis and codebase-aware analysis
- [ ] Create unit tests in `tests/unit/lib/clarification/test_detection.py`

## Technical Specification

### detect_scope_ambiguity()

```python
@dataclass
class ScopeAmbiguity:
    feature: str
    unmentioned_extensions: List[str]
    confidence: float

def detect_scope_ambiguity(task_context: TaskContext) -> Optional[ScopeAmbiguity]:
    """
    Detect if task scope has ambiguous boundaries.

    Looks for:
    - Feature + common extensions not explicitly included/excluded
    - Vague scope words ("implement", "add" without specifics)
    - Missing acceptance criteria
    """
    feature_extensions = {
        "auth": ["password reset", "2FA", "OAuth", "session management"],
        "user": ["profile", "settings", "preferences", "avatar"],
        "api": ["pagination", "filtering", "sorting", "caching"],
        "form": ["validation", "error handling", "auto-save"],
        "list": ["pagination", "search", "filtering", "sorting"],
        "upload": ["progress", "resume", "validation", "preview"],
    }
    # ... implementation
```

### detect_technology_choices()

```python
@dataclass
class TechChoice:
    domain: str
    existing: Optional[str]
    alternatives: List[str]
    recommendation: str

@dataclass
class TechChoices:
    choices: List[TechChoice]

def detect_technology_choices(
    task_context: TaskContext,
    codebase_context: Optional[CodebaseContext] = None
) -> Optional[TechChoices]:
    """
    Detect if there are technology decisions to be made.

    Looks for:
    - Multiple libraries for same purpose in ecosystem
    - Existing patterns vs new approach
    - Stack-specific alternatives
    """
    tech_alternatives = {
        "data_fetching": {
            "react": ["React Query", "SWR", "Apollo Client", "fetch"],
            "vue": ["Vue Query", "Pinia", "fetch"],
        },
        "state_management": {
            "react": ["Redux", "Zustand", "Jotai", "Context API"],
        },
        # ... more domains
    }
```

### detect_integration_points()

```python
@dataclass
class IntegrationPoint:
    system: str
    integration_type: str  # "extend", "replace", "new"
    confidence: float

def detect_integration_points(
    task_context: TaskContext,
    codebase_context: Optional[CodebaseContext] = None
) -> List[IntegrationPoint]:
    """
    Detect external system connections.

    Looks for:
    - Import statements for external services
    - API client patterns in codebase
    - Configuration for external services
    """
```

## Files to Create

1. `installer/global/commands/lib/clarification/detection.py`
2. `tests/unit/lib/clarification/test_detection.py`

## Dependencies

- TASK-CLQ-001 (imports from core.py) - but can develop in parallel, just need interface agreement

## Related Tasks

- TASK-CLQ-001 (core.py - parallel)
- TASK-CLQ-003 (display.py - parallel)

## Reference

See [Review Report Section: Question Generation Algorithm](./../../../.claude/reviews/TASK-REV-B130-review-report.md#question-generation-algorithm) for detailed specification.
