---
id: TASK-GPS-003
title: Seed agentic-dataset-factory architecture artefacts to Graphiti
status: backlog
task_type: implementation
created: 2026-03-17T15:00:00Z
updated: 2026-03-17T15:00:00Z
priority: high
tags: [graphiti, agentic-dataset-factory, manual]
parent_review: TASK-REV-5B3A
feature_id: FEAT-GPS1
implementation_mode: manual
wave: 1
complexity: 1
---

# Task: Seed agentic-dataset-factory architecture artefacts to Graphiti

## Description

Manual step: Run from the `agentic-dataset-factory` directory to seed the 14 missing architecture artefacts identified in TASK-REV-5B3A.

## Commands to Execute

```bash
cd ~/Projects/appmilla_github/agentic-dataset-factory

# Seed all markdown architecture docs (ARCHITECTURE.md, 9 ADRs, domain-model, container, system-context)
guardkit graphiti add-context docs/architecture/ --pattern "**/*.md"

# Seed assumptions YAML
guardkit graphiti add-context docs/architecture/assumptions.yaml
```

## Acceptance Criteria

- [ ] All 14 artefacts seeded to Graphiti under project_id: agentic-dataset-factory
- [ ] Verify with: `guardkit graphiti search "architecture" --limit 5`
- [ ] Verify ADRs with: `guardkit graphiti search "ADR-ARCH" --limit 10`

## Expected Artefacts

1. docs/architecture/ARCHITECTURE.md
2. docs/architecture/decisions/ADR-ARCH-001.md through ADR-ARCH-009.md (9 files)
3. docs/architecture/assumptions.yaml
4. docs/architecture/domain-model.md
5. docs/architecture/container.md
6. docs/architecture/system-context.md
