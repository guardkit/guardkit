---
id: TASK-064
title: Implement distribution helper utilities
status: backlog
created: 2025-11-01T16:33:00Z
priority: low
complexity: 4
estimated_hours: 4
tags: [distribution, utilities, documentation]
epic: EPIC-001
feature: distribution
dependencies: [TASK-061]
blocks: []
---

# TASK-064: Implement Distribution Helper Utilities

## Objective

Add utilities to help teams distribute templates:
- Git commit/tag helpers
- Generate usage instructions
- Create sharing guide (git, package, registry)
- Add installation verification

## Acceptance Criteria

- [ ] Git commit helper (creates commit with template)
- [ ] Git tag helper (creates semantic version tag)
- [ ] Generates usage instructions
- [ ] Creates sharing guide (markdown)
- [ ] Provides installation verification script
- [ ] Unit tests passing

## Implementation

```python
class DistributionHelpers:
    def generate_usage_instructions(self, template_name):
        return f"""
# Using {template_name} Template

## Installation
```bash
# Copy template to local templates
cp -r installer/local/templates/{template_name} .claude/templates/

# Use template
agentic-init {template_name}
```

## Sharing with Team
1. Git: git add installer/local/templates/{template_name}
2. Package: Create tar.gz and distribute
3. Registry: Publish to internal registry
        """

    def create_git_commit(self, template_path):
        # Helper to commit template to git
        pass
```

**Estimated Time**: 4 hours | **Complexity**: 4/10 | **Priority**: LOW
