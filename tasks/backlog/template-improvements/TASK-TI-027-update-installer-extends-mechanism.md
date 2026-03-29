---
id: TASK-TI-027
title: Implement template extends mechanism in installer
status: backlog
created: 2026-03-30T00:30:00Z
updated: 2026-03-30T00:30:00Z
priority: p1
tags: [installer, template, extends, inheritance]
complexity: 5
parent_review: TASK-REV-32D2
feature_id: FEAT-TI
wave: 4
implementation_mode: task-work
depends_on: []
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Implement Template Extends Mechanism in Installer

## Description

The `langchain-deepagents-weighted-evaluation` template uses `"extends": "langchain-deepagents"` in its manifest.json. The installer needs to support this inheritance mechanism so that installing the extension template also installs the base template's components.

## What to Build

### Extends Behaviour

When `guardkit init langchain-deepagents-weighted-evaluation` is run:

1. Installer reads extension manifest, finds `"extends": "langchain-deepagents"`
2. Installer installs the base template first (all files from `langchain-deepagents`)
3. Installer overlays the extension template files on top
4. Extension files override base files where they share the same path
5. Extension-only files are added alongside base files

### Conflict Resolution

- Extension files with same path as base → extension wins (overlay)
- Base-only files → kept as-is
- Extension-only files → added
- manifest.json → merged (extension values override base values, arrays concatenated)

### Installer Changes

- Update `install.sh` or Python installer to handle `extends` field
- Add validation: base template must exist in the template registry
- Add `--base-only` flag to install just the base without extension (for simple use cases)

## Acceptance Criteria

- [ ] `extends` field in manifest.json is parsed and honoured
- [ ] Base template files installed before extension overlay
- [ ] Extension files correctly override base files where paths match
- [ ] `guardkit init langchain-deepagents-weighted-evaluation` works end-to-end
- [ ] `guardkit init langchain-deepagents` still works independently
- [ ] Tests verify the extends mechanism

## Effort Estimate

3-4 hours
