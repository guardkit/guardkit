---
id: REV-SD-001
title: 'Review: /system-design defaults to Graphiti unavailable despite active configuration'
status: in_progress
created: '2026-03-18T00:00:00Z'
updated: '2026-03-18T00:00:00Z'
priority: high
complexity: 5
task_type: review
review_mode: architectural
review_depth: standard
tags: [graphiti, system-design, bug]
---

# Review: /system-design defaults to Graphiti unavailable despite active configuration

## Description

When running `/system-design` in a project with a fully configured and seeded Graphiti instance (`.guardkit/graphiti.yaml` present, `enabled: true`, `.graphiti_seeded.json` confirming seeded status), the command defaulted to "Graphiti unavailable" and skipped all Graphiti seeding of design artefacts.

The user had spent the day working with Graphiti. The project had:
- `.guardkit/graphiti.yaml` with `enabled: true`, FalkorDB on `whitestocks:6379`, vLLM endpoints configured
- `.guardkit/seeding/.graphiti_seeded.json` confirming seeded status (`v1.2.0`, 2026-03-17)
- `.guardkit/seeding/.system_seeded.json` confirming system seeded with `langchain-deepagents` template
- Active `group_ids`: `product_knowledge`, `command_workflows`, `architecture_decisions`

Despite all of this, `/system-design` treated Graphiti as unavailable and output: "Graphiti unavailable — continuing with markdown artefacts only".

## Root Cause Investigation Areas

1. **Command prompt template:** The `/system-design` command prompt includes Python pseudocode for Graphiti availability checks (`get_graphiti()`, `SystemPlanGraphiti`, `SystemDesignGraphiti`). These are illustrative — they don't correspond to actual importable modules. The LLM executing the command has no way to actually call these functions, so it defaults to the "unavailable" fallback path.

2. **Missing detection heuristic:** The command prompt should instruct the LLM to check for `.guardkit/graphiti.yaml` existence and `enabled: true` as the availability signal, rather than attempting Python imports that don't exist.

3. **Missing seeding instructions:** Even when Graphiti is detected as available, the command prompt doesn't provide concrete `guardkit graphiti add-context` commands for seeding design artefacts. The LLM needs actionable CLI commands, not Python pseudocode.

4. **Group ID gap:** The existing `group_ids` in `graphiti.yaml` are `product_knowledge`, `command_workflows`, `architecture_decisions`. The `/system-design` command references `project_design` and `api_contracts` groups — these may need to be added to the config, or the command should use existing groups.

## Acceptance Criteria

- [ ] `/system-design` correctly detects Graphiti availability by checking `.guardkit/graphiti.yaml` exists and `enabled: true`
- [ ] When available, `/system-design` generates `guardkit graphiti add-context` commands for all design artefacts
- [ ] The command prompt replaces Python pseudocode imports with file-existence checks the LLM can actually perform
- [ ] Group IDs for design artefacts are documented (new groups or mapping to existing ones)
- [ ] The "Graphiti unavailable" fallback path is only reached when `.guardkit/graphiti.yaml` is genuinely missing or `enabled: false`

## Impact

- Design artefacts are not seeded into the knowledge graph, breaking the downstream chain: `/feature-spec` and `/feature-plan` cannot query design context from Graphiti
- User trust is undermined when the system ignores configuration they've set up
- Same issue likely affects `/system-arch` and other commands that reference Graphiti

## Suggested Fix Approach

Replace the Python pseudocode prerequisite check with:

```python
# In the command prompt, instruct the LLM to:
# 1. Read .guardkit/graphiti.yaml
# 2. Check enabled: true
# 3. If available: generate guardkit CLI commands for seeding
# 4. If unavailable: warn and continue with markdown only
```

And add a Phase 5 output like:

```bash
# Seeding commands (run after review):
guardkit graphiti add-context docs/design/contracts/API-domain-config.md --group project_design
guardkit graphiti add-context docs/design/contracts/API-generation.md --group project_design
# ... etc
```

## Related

- `/system-arch` command — likely has same issue
- `.guardkit/graphiti.yaml` — source of truth for Graphiti availability
- `/system-design` command prompt — contains the pseudocode that causes the false negative
