---
id: TASK-040
title: Implement naming convention inference
status: backlog
created: 2025-11-01T16:05:00Z
priority: medium
complexity: 5
estimated_hours: 5
tags: [template-create, naming-conventions]
epic: EPIC-001
feature: pattern-extraction
dependencies: [TASK-038]
blocks: [TASK-043]
---

# TASK-040: Implement Naming Convention Inference

## Objective

Automatically infer naming conventions from codebase:
- Class naming patterns (suffix/prefix)
- File naming conventions
- Namespace/package structure
- Variable naming patterns

## Acceptance Criteria

- [ ] Detects ViewModel suffix convention
- [ ] Detects Repository suffix convention
- [ ] Detects Page/View suffix convention
- [ ] Infers file naming (PascalCase, kebab-case, camelCase)
- [ ] Extracts namespace patterns
- [ ] Returns naming rules for settings.json
- [ ] Unit tests passing (>85% coverage)

## Implementation

```python
class NamingConventionInferencer:
    def infer_conventions(self, project_path, arch_result):
        # Analyze file names and class names
        # Detect patterns: {Verb}{Entity}, {Entity}ViewModel, I{Entity}Repository
        # Return structured naming rules
        pass
```

**Estimated Time**: 5 hours | **Complexity**: 5/10 | **Priority**: MEDIUM
