---
id: TASK-CRS-014.7
title: Update tests for rules/guidance/ naming
status: completed
task_type: implementation
created: 2025-12-11T15:00:00Z
updated: 2025-12-11T15:00:00Z
priority: high
tags: [rules-structure, naming, tests]
complexity: 2
parent_task: TASK-CRS-014
implementation_mode: direct
estimated_hours: 0.5
depends_on: [TASK-CRS-014.1]
---

# Task: Update tests for rules/guidance/ naming

## Background

After renaming `rules/agents/` to `rules/guidance/` in the RulesStructureGenerator (CRS-014.1), the corresponding tests need updating.

## Changes Required

### File: `installer/core/lib/template_generator/tests/test_rules_generator.py`

**Line 218-220** (test assertions):
```python
# Before:
assert "rules/agents/repository-specialist.md" in rules
assert "rules/agents/api-specialist.md" in rules
assert "rules/agents/testing-specialist.md" in rules

# After:
assert "rules/guidance/repository-specialist.md" in rules
assert "rules/guidance/api-specialist.md" in rules
assert "rules/guidance/testing-specialist.md" in rules
```

**Lines 383, 395, 408** (test methods for _generate_agent_rules):
- If method is renamed to `_generate_guidance_rules`, update test method names
- Update any assertions checking output paths

### Additional Test Updates

Search for any other test files that reference `rules/agents`:

```bash
grep -r "rules/agents" tests/
```

Update all found references.

## Acceptance Criteria

- [x] All test assertions updated to use `rules/guidance/`
- [x] Tests pass with new naming
- [x] No hardcoded `rules/agents` references remain in tests

## Verification

```bash
# Run the specific test file
pytest tests/lib/template_generator/test_rules_generator.py -v

# Run full test suite to catch any other breakages
pytest tests/ -v --tb=short
```

## Notes

- Must be done after CRS-014.1 (generator update)
- Can be done in parallel with template renames (CRS-014.2-6)
