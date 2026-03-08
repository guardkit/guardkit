---
id: TASK-CSC-001
title: Create data models and universal context gatherer
status: backlog
created: 2026-01-23T11:30:00Z
priority: high
tags: [context-sensitive-coach, data-models, git-diff, quality-gates]
task_type: feature
complexity: 4
parent_review: TASK-REV-CSC1
feature_id: FEAT-CSC
wave: 1
implementation_mode: task-work
conductor_workspace: csc-wave1-models
dependencies: []
---

# Task: Create Data Models and Universal Context Gatherer

## Description

Create the foundational data models and universal context gathering functionality for the context-sensitive Coach. This provides language-agnostic metrics that work for ALL programming languages.

## Acceptance Criteria

- [ ] `UniversalContext` dataclass with all required fields
- [ ] `ContextAnalysisResult` dataclass for AI analysis results
- [ ] `UniversalContextGatherer` class that gathers git diff statistics
- [ ] File categorization (source, test, config)
- [ ] Test file detection via naming conventions
- [ ] Unit tests with >80% coverage

## Implementation Notes

### Data Models Location

Create in: `guardkit/orchestrator/quality_gates/context_analysis/models.py`

### UniversalContext Fields

```python
@dataclass
class UniversalContext:
    # Git diff statistics
    lines_added: int
    lines_deleted: int
    lines_modified: int
    files_created: int
    files_modified: int
    files_deleted: int

    # File categorization
    file_extensions: Dict[str, int]  # {".py": 3, ".json": 1}
    source_files: int
    test_files: int
    config_files: int

    # Dependency indicators
    has_dependency_changes: bool
    new_external_dependencies: int
```

### Git Diff Analysis

Use `git diff --stat --numstat` to get line counts.
Use `git diff --name-status` to categorize file changes.

### Test File Detection Patterns

```python
TEST_PATTERNS = [
    "*_test.*", "*.test.*", "test_*.*",  # Python/Go
    "*_spec.*", "*.spec.*",              # JS/Ruby
    "*Tests.*", "*Test.*",               # C#/Java
]
```

### Config File Detection

```python
CONFIG_FILES = [
    "package.json", "requirements.txt", "go.mod",
    "Cargo.toml", "*.csproj", "pom.xml", "build.gradle",
    "pyproject.toml", "setup.py", "setup.cfg",
    ".env*", "*.yaml", "*.yml", "*.toml", "*.ini",
]
```

## Testing Strategy

- Unit test `UniversalContextGatherer` with mock git output
- Test file categorization with various extensions
- Test edge cases (empty diff, large diff, binary files)
