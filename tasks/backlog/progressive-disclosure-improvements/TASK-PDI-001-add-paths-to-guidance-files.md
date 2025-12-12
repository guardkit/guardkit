---
id: TASK-PDI-001
title: Add paths frontmatter to guidance files for conditional loading
status: backlog
created: 2025-12-12T11:45:00Z
updated: 2025-12-12T11:45:00Z
priority: low
tags: [progressive-disclosure, rules-structure, guidance, optimization]
complexity: 2
parent_review: TASK-REV-PD01
implementation_mode: direct
---

# Task: Add paths frontmatter to guidance files for conditional loading

## Description

Add `paths:` frontmatter to guidance files in `.claude/rules/guidance/` to enable automatic loading when editing files that match the agent's specialty.

Currently, guidance files are loaded via agent invocation but not automatically when editing relevant files. Adding path hints would optimize context loading.

## Problem

Guidance files in `rules/guidance/` lack `paths:` frontmatter:
```markdown
---
agent: realm-repository-specialist
---
```

Should include path hints:
```markdown
---
agent: realm-repository-specialist
paths: **/Repositories/**/*.cs, **/*Repository.cs
---
```

## Acceptance Criteria

- [ ] All 9 guidance files have appropriate `paths:` frontmatter
- [ ] Path patterns match the agent's specialty domain
- [ ] Template-create generates guidance files with paths
- [ ] Guardkit init copies paths correctly

## Implementation

### Path Mappings

| Guidance File | Suggested Paths |
|--------------|-----------------|
| realm-repository-specialist | `**/Repositories/**/*.cs, **/*Repository.cs` |
| business-logic-engine-specialist | `**/Engines/**/*.cs, **/*Engine.cs` |
| erroror-railway-oriented-programming-specialist | `**/*.cs` (broad - ErrorOr used everywhere) |
| maui-mvvm-viewmodel-specialist | `**/ViewModels/**/*.cs, **/*ViewModel.cs` |
| maui-xaml-ui-specialist | `**/*.xaml, **/Views/**/*.cs` |
| reactive-extensions-rx-specialist | `**/*.cs` (Rx can be used anywhere) |
| riok-mapperly-code-generator-specialist | `**/Mapper/**/*.cs, **/*Mapper.cs` |
| xunit-nsubstitute-testing-specialist | `**/*.test.cs, **/Tests/**/*.cs, **/*Tests.cs` |
| http-api-service-specialist | `**/Services/**/*.cs, **/*Service.cs` |

### Files to Update

1. Update guidance file template in template-create
2. Update existing mydrive template guidance files
3. Verify guardkit init preserves paths

## Notes

- Low priority - system works without this
- Improves context optimization for path-specific loading
- Implementation is straightforward file edits
