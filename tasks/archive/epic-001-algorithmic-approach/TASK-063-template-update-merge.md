---
id: TASK-063
title: Implement template update/merge functionality
status: backlog
created: 2025-11-01T16:32:00Z
priority: medium
complexity: 6
estimated_hours: 6
tags: [distribution, merging, updates]
epic: EPIC-001
feature: distribution
dependencies: [TASK-062]
blocks: []
---

# TASK-063: Implement Template Update/Merge Functionality

## Objective

Handle template updates when name conflicts occur:
- Detect existing template with same name
- Prompt: Overwrite, Merge, Cancel
- Implement merge logic (preserve customizations)
- Update version number
- Add changelog entry

## Acceptance Criteria

- [ ] Detects existing template by name
- [ ] Prompts user with options (Overwrite/Merge/Cancel)
- [ ] Implements overwrite (replace all files)
- [ ] Implements merge (preserve custom agents, update patterns)
- [ ] Bumps version number on merge
- [ ] Adds changelog entry
- [ ] Unit tests passing

## Implementation

```python
class TemplateMerger:
    def merge_templates(self, existing_path, new_path):
        # Compare templates
        diff = self._compare_templates(existing_path, new_path)

        # Preserve custom agents
        custom_agents = self._identify_custom_agents(existing_path, new_path)

        # Update patterns from new template
        # Preserve customizations
        # Bump version
        # Update changelog

        return merged_template
```

**Estimated Time**: 6 hours | **Complexity**: 6/10 | **Priority**: MEDIUM
