---
id: TASK-CRS-014.1
title: Rename rules/agents/ to rules/guidance/ in RulesStructureGenerator
status: backlog
task_type: implementation
created: 2025-12-11T15:00:00Z
updated: 2025-12-11T15:00:00Z
priority: high
tags: [rules-structure, naming, refactor]
complexity: 2
parent_task: TASK-CRS-014
implementation_mode: direct
estimated_hours: 0.5
---

# Task: Rename rules/agents/ to rules/guidance/ in RulesStructureGenerator

## Background

The review TASK-CRS-014 identified a naming confusion: using "agents" for both:
- `agents/` directory (full specialist definitions for Task tool and /agent-enhance)
- `.claude/rules/agents/` directory (path-based contextual guidance)

**Decision**: Rename `.claude/rules/agents/` to `.claude/rules/guidance/` to clearly distinguish these two different concepts.

## Changes Required

### File: `installer/core/lib/template_generator/rules_structure_generator.py`

**Line 75** (docstring example):
```python
# Before:
"rules/agents/api-specialist.md": "---\npaths: **/api/**\n---\n..."

# After:
"rules/guidance/api-specialist.md": "---\npaths: **/api/**\n---\n..."
```

**Line 97** (output path):
```python
# Before:
rules[f"rules/agents/{agent_slug}.md"] = self._generate_agent_rules(agent)

# After:
rules[f"rules/guidance/{agent_slug}.md"] = self._generate_agent_rules(agent)
```

**Line 146** (CLAUDE.md reference):
```python
# Before:
- **Agents**: `.claude/rules/agents/`

# After:
- **Guidance**: `.claude/rules/guidance/`
```

**Optional**: Consider renaming `_generate_agent_rules()` to `_generate_guidance_rules()` for consistency.

## Acceptance Criteria

- [ ] RulesStructureGenerator outputs to `rules/guidance/` instead of `rules/agents/`
- [ ] CLAUDE.md template references `rules/guidance/`
- [ ] Docstrings updated with correct path
- [ ] Existing tests still pass (will be updated in CRS-014.4)

## Verification

```bash
# Run tests (expect some failures until CRS-014.4 completes)
pytest tests/lib/template_generator/test_rules_generator.py -v

# Generate a test template and verify output
python3 -c "
from installer.core.lib.template_generator.rules_structure_generator import RulesStructureGenerator
# Quick smoke test that paths are correct
"
```

## Notes

- This is a straightforward find-replace task
- Tests will need updating separately (CRS-014.4)
- All future templates will use the new naming
- Existing templates need separate renaming tasks (CRS-014.2, CRS-014.3, etc.)
