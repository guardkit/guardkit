---
id: TASK-046
title: Implement template validation engine
status: backlog
created: 2025-11-01T16:11:00Z
priority: medium
complexity: 5
estimated_hours: 6
tags: [template-create, validation, quality-gates]
epic: EPIC-001
feature: pattern-extraction
dependencies: [TASK-042, TASK-043, TASK-044, TASK-045]
blocks: [TASK-047]
---

# TASK-046: Implement Template Validation Engine

## Objective

Validate generated templates before packaging:
- Validate manifest.json structure
- Check required files present
- Verify template placeholders
- Test template compilation
- Generate validation report

## Acceptance Criteria

- [ ] Validates manifest.json against schema
- [ ] Checks CLAUDE.md exists
- [ ] Checks settings.json exists
- [ ] Verifies templates/ directory exists
- [ ] Validates placeholder syntax
- [ ] Tests template compilation (fills placeholders, compiles)
- [ ] Returns validation report (pass/warnings/errors)
- [ ] Unit tests passing (>85% coverage)

## Implementation

```python
class TemplateValidator:
    def validate(self, template_path):
        results = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        # Check required files
        if not (template_path / "manifest.json").exists():
            results['errors'].append("Missing manifest.json")
            results['valid'] = False

        # Validate manifest structure
        manifest = json.load(open(template_path / "manifest.json"))
        if not manifest.get('name'):
            results['errors'].append("Manifest missing 'name' field")

        # Validate templates
        for template_file in (template_path / "templates").glob("**/*.template"):
            self._validate_template_file(template_file, results)

        return results
```

**Estimated Time**: 6 hours | **Complexity**: 5/10 | **Priority**: MEDIUM
