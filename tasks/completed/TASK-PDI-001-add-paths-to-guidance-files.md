---
id: TASK-PDI-001
title: Add paths frontmatter to guidance files for conditional loading
status: completed
created: 2025-12-12T11:45:00Z
updated: 2025-12-12T12:30:00Z
completed: 2025-12-12T12:30:00Z
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

- [x] All 9 guidance files have appropriate `paths:` frontmatter
- [x] Path patterns match the agent's specialty domain
- [x] Template-create generates guidance files with paths
- [x] Guardkit init copies paths correctly

## Implementation Summary (Revised - Technology Agnostic)

Updated `installer/core/lib/guidance_generator/path_patterns.py` to be **technology-agnostic**:

1. **Removed all technology-specific keyword patterns** - No hardcoded .NET/MAUI patterns
2. **Added explicit `paths` field support** - Agents can define their own path patterns in frontmatter
3. **Expanded language support** - Added Go, Rust, Java, Kotlin, Swift, Ruby, PHP stacks
4. **Added generic capabilities** - services, controllers, views (not technology-specific)

### Priority Order:
1. **Explicit `paths` field** (highest priority - passthrough from agent metadata)
2. **Phase patterns** (testing, database, api, ui)
3. **Capability patterns** (generic concepts only)
4. **Stack patterns** (file extensions only, e.g., `**/*.py`, `**/*.cs`)

### Key Design Decision:
Technology-specific patterns (like `**/Repositories/**/*.cs`) should be defined in **agent frontmatter**, not hardcoded in the core library. This allows templates to customize patterns without modifying core code.

### Updated Tests (10 technology-agnostic tests):
- `test_generate_path_patterns_explicit_paths_passthrough`
- `test_generate_path_patterns_explicit_paths_override_stack`
- `test_generate_path_patterns_api_phase`
- `test_generate_path_patterns_ui_phase`
- `test_generate_path_patterns_services_capability`
- `test_generate_path_patterns_controllers_capability`
- `test_generate_path_patterns_go_stack`
- `test_generate_path_patterns_rust_stack`
- `test_generate_path_patterns_java_stack`
- `test_generate_path_patterns_capability_case_insensitive`

All 44 tests pass.

## How Templates Define Custom Paths

Agents can now define technology-specific paths in their frontmatter:

```markdown
---
agent: realm-repository-specialist
stack: [dotnet]
paths: "**/Repositories/**/*.cs, **/*Repository.cs"
---
```

The `paths` field takes highest priority and is passed through directly.

## Notes

- Technology-agnostic design - core library doesn't favor any stack
- Templates can customize via `paths` field in agent metadata
- Re-running `/template-create` on mydrive will use agent metadata paths
