---
id: TASK-045
title: Implement code template generator with placeholders
status: backlog
created: 2025-11-01T16:10:00Z
priority: high
complexity: 7
estimated_hours: 8
tags: [template-create, template-generation, placeholders]
epic: EPIC-001
feature: pattern-extraction
dependencies: [TASK-039]
blocks: [TASK-047]
---

# TASK-045: Implement Code Template Generator with Placeholders

## Objective

Generate .template files from extracted code patterns with placeholders:
- Convert extracted patterns to template files
- Insert placeholders ({{ComponentName}}, {{Entity}}, {{Verb}})
- Support TypeScript, C#, Python templates
- Generate templates for: components, operations, repositories, services, tests

## Acceptance Criteria

- [ ] Generates .template files from CodePattern objects
- [ ] Inserts appropriate placeholders
- [ ] Supports React component templates
- [ ] Supports .NET domain operation templates
- [ ] Supports repository templates
- [ ] Supports service templates
- [ ] Supports test templates
- [ ] Templates compile when placeholders filled
- [ ] Unit tests passing (>85% coverage)

## Implementation

```python
class CodeTemplateGenerator:
    PLACEHOLDERS = {
        'class_name': '{{ClassName}}',
        'entity': '{{Entity}}',
        'verb': '{{Verb}}',
        'operation': '{{OperationName}}',
        'component': '{{ComponentName}}',
        'return_type': '{{ReturnType}}',
        'parameters': '{{Parameters}}'
    }

    def generate_templates(self, patterns: List[CodePattern]):
        templates = []
        for pattern in patterns:
            if pattern.pattern_type == "react_component":
                template = self._generate_react_template(pattern)
            elif pattern.pattern_type == "domain_operation":
                template = self._generate_domain_template(pattern)
            # ... etc
            templates.append(template)
        return templates

    def _generate_react_template(self, pattern):
        # Replace specific names with placeholders
        # ProductList → {{ComponentName}}
        # product → {{entity}}
        pass
```

**Estimated Time**: 8 hours | **Complexity**: 7/10 | **Priority**: HIGH
