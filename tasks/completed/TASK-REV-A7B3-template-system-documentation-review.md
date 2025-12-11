---
id: TASK-REV-A7B3
title: Template System Documentation Review
status: completed
task_type: review
created: 2025-12-10T10:00:00Z
updated: 2025-12-10T10:00:00Z
priority: normal
tags: [documentation, architecture, templates, agents, progressive-disclosure]
complexity: 5
review_mode: architectural
review_depth: standard
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Template System Documentation Review

## Description

Comprehensive review and explanation of how GuardKit's template system works, including:

1. **Template Files** - Structure, organization, and purpose of template directories
2. **Agent Files** - How agents are defined, discovered, and enhanced
3. **CLAUDE.md** - The main configuration file and how it provides guidance
4. **Progressive Disclosure** - The core/extended file splitting pattern for context optimization
5. **Manifest Metadata** - Template manifest structure and fields
6. **Settings Metadata** - Template settings extraction and configuration

## Review Scope

### Primary Areas
- `installer/core/templates/` - Reference templates (react-typescript, fastapi-python, nextjs-fullstack, default, react-fastapi-monorepo)
- `installer/core/agents/` - Core agent definitions
- Template manifest.json structure
- Template settings.json structure
- Progressive disclosure pattern implementation
- CLAUDE.md generation and structure

### Key Questions to Address
1. How are template files organized and what does each file do?
2. How do agent files work and what metadata do they contain?
3. What is the relationship between CLAUDE.md and template configuration?
4. How does progressive disclosure optimize context window usage?
5. What fields are in manifest.json and what do they control?
6. What fields are in settings.json and how are they extracted?
7. How do agents get discovered and matched to tasks?

## Acceptance Criteria

- [x] Clear explanation of template directory structure
- [x] Documentation of agent file format and frontmatter metadata
- [x] Explanation of CLAUDE.md purpose and structure
- [x] Description of progressive disclosure pattern (core vs extended files)
- [x] Complete manifest.json field reference
- [x] Complete settings.json field reference
- [x] Examples from actual templates in the codebase

## Implementation Notes

This is a review/documentation task. The output should be a comprehensive explanation that can help new users understand the template system architecture.

## Test Execution Log
[Automatically populated by /task-review]
