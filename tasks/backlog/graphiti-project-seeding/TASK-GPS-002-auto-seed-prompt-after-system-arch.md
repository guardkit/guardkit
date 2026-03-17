---
id: TASK-GPS-002
title: Add auto-seed prompt after /system-arch generates architecture artefacts
status: backlog
task_type: implementation
created: 2026-03-17T15:00:00Z
updated: 2026-03-17T15:00:00Z
priority: medium
tags: [graphiti, system-arch, ux, workflow]
parent_review: TASK-REV-5B3A
feature_id: FEAT-GPS1
implementation_mode: task-work
wave: 1
complexity: 4
---

# Task: Add auto-seed prompt after /system-arch generates architecture artefacts

## Description

When `/system-arch` completes and generates architecture artefacts (ARCHITECTURE.md, ADRs, domain-model.md, etc.), it should check if Graphiti is available and offer to seed the generated files:

```
Architecture artefacts generated at docs/architecture/

Graphiti is available. Seed architecture to knowledge graph?
  [Y]es - Run: guardkit graphiti add-context docs/architecture/ --pattern "**/*.md"
  [N]o  - Skip (you can seed later with the command above)
```

This closes the workflow gap where `/system-arch` output is never persisted to Graphiti unless the user manually runs `add-context`.

## Acceptance Criteria

- [ ] After `/system-arch` completes, checks if Graphiti is configured (`.guardkit/graphiti.yaml` exists)
- [ ] If Graphiti available, prompts user to seed generated artefacts
- [ ] If user accepts, runs `add-context` on the generated architecture directory
- [ ] If Graphiti not available, prints informational message about manual seeding
- [ ] Works for both initial generation and regeneration
- [ ] No test regressions

## Implementation Notes

The `/system-arch` command is defined in `installer/core/commands/system-arch.md` and executed by Claude Code. The auto-seed prompt should be added as a post-generation step in the command specification.

Need to check:
- Where `/system-arch` output path is determined
- How to invoke `add-context` programmatically vs suggesting the CLI command
- Whether to also handle YAML files (assumptions.yaml)
